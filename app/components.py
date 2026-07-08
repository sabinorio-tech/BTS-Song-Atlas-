"""Reusable Streamlit interface components for BTS Song Atlas V2."""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from utils import (
    format_duration,
    load_dashboard_data,
    pair_similarity,
    semantic_story,
    similar_songs,
)
from visualization import build_atlas_figure, build_minimap


ALL_SONGS = "__all_songs__"
FALLBACK_COVER = "data:image/svg+xml;charset=UTF-8," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">'
    '<rect width="240" height="240" fill="#11132b"/>'
    '<circle cx="120" cy="120" r="62" fill="#6d35a5" opacity=".55"/>'
    '<text x="120" y="133" text-anchor="middle" font-size="42" fill="#f1e8ff">♪</text>'
    "</svg>"
)


def apply_styles() -> None:
    css = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _safe(value: object) -> str:
    return html.escape(str(value if pd.notna(value) else "—"))


def _image_source(value: object) -> str:
    if pd.notna(value) and str(value).startswith(("https://", "data:image/")):
        return str(value)
    return FALLBACK_COVER


def _valid_url(value: object) -> bool:
    return bool(pd.notna(value) and str(value).startswith("https://"))


def _select_song(track_id: str, *, focus: bool) -> None:
    """Update selection and optionally request a map camera move."""
    st.session_state.atlas_overview = False
    st.session_state.selected_song_id = track_id
    if focus:
        nonce = st.session_state.get("focus_nonce", 0) + 1
        st.session_state.focus_nonce = nonce
        st.session_state.focus_song_id = track_id
        st.session_state.viewport_revision = f"atlas-focus-{track_id}-{nonce}"
    else:
        st.session_state.focus_song_id = None
    if st.session_state.get("experience_mode", "Explore") == "Explore":
        journey = st.session_state.setdefault("journey_ids", [])
        if not journey or journey[-1] != track_id:
            journey.append(track_id)
            st.session_state.journey_ids = journey[-12:]


def _search_changed() -> None:
    track_id = st.session_state.get("song_search")
    if not track_id:
        return
    if track_id == ALL_SONGS:
        nonce = st.session_state.get("focus_nonce", 0) + 1
        st.session_state.focus_nonce = nonce
        st.session_state.focus_song_id = None
        st.session_state.viewport_revision = f"atlas-all-{nonce}"
        st.session_state.atlas_overview = True
        return
    _select_song(track_id, focus=True)
    recent = [item for item in st.session_state.get("recent_searches", []) if item != track_id]
    st.session_state.recent_searches = [track_id, *recent][:4]


def _popular_song(track_id: str) -> None:
    st.session_state.song_search = track_id
    _search_changed()


def _compare_changed() -> None:
    track_id = st.session_state.get("compare_search")
    if track_id and track_id != st.session_state.selected_song_id:
        st.session_state.atlas_overview = False
        st.session_state.compare_song_id = track_id


def _journey_back() -> None:
    journey = st.session_state.get("journey_ids", [])
    if len(journey) > 1:
        journey.pop()
        st.session_state.journey_ids = journey
        _select_song(journey[-1], focus=True)


def _journey_clear() -> None:
    st.session_state.journey_ids = [st.session_state.selected_song_id]


def render_sidebar(data: pd.DataFrame) -> tuple[pd.DataFrame, str, dict[str, object]]:
    min_year, max_year = int(data.release_year.min()), int(data.release_year.max())
    primary = data[data["is_primary_version"]].sort_values("track_name")
    song_options = primary["track_id"].tolist()
    search_options = [ALL_SONGS, *song_options]
    labels = primary.set_index("track_id").apply(
        lambda row: f"{row['track_name']} · {row['album_name']}", axis=1
    ).to_dict()
    labels[ALL_SONGS] = "All songs"

    selected_id = st.session_state.selected_song_id
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-card">
              <div class="brand-kicker">SEMANTIC EXPLORATION</div>
              <div class="brand-title">BTS SONG ATLAS <span>♥</span></div>
              <p>Move through a universe of songs shaped by lyrical meaning.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-label">Search</div>', unsafe_allow_html=True)
        if "song_search" not in st.session_state:
            st.session_state.song_search = ALL_SONGS
        st.selectbox(
            "Search for a song",
            search_options,
            format_func=lambda track_id: labels[track_id],
            key="song_search",
            on_change=_search_changed,
            filter_mode="fuzzy",
            placeholder="Search for a song…",
            label_visibility="collapsed",
        )
        st.caption("Type a title, album, or close spelling · ↑↓ to navigate · Enter to select")

        recent_ids = [track_id for track_id in st.session_state.recent_searches if track_id in labels]
        if recent_ids:
            st.caption("Recent searches")
            recent_columns = st.columns(2)
            for index, track_id in enumerate(recent_ids):
                recent_columns[index % 2].button(
                    labels[track_id].split(" · ")[0],
                    key=f"recent_{track_id}",
                    width="stretch",
                    on_click=_popular_song,
                    args=(track_id,),
                )

        popular = ["Black Swan", "Spring Day", "Dynamite", "Life Goes On"]
        columns = st.columns(2)
        for index, title in enumerate(popular):
            match = primary[primary["track_name"].str.casefold() == title.casefold()]
            if not match.empty:
                columns[index % 2].button(
                    title,
                    key=f"popular_{index}",
                    width="stretch",
                    on_click=_popular_song,
                    args=(match.iloc[0].track_id,),
                )

        st.markdown('<div class="section-label">Explore mode</div>', unsafe_allow_html=True)
        mode = st.segmented_control(
            "Experience mode",
            ["Explore", "Compare"],
            key="experience_mode",
            label_visibility="collapsed",
            width="stretch",
        )
        neighborhood_size = st.select_slider(
            "Top similar songs",
            options=[5, 10, 20, 50],
            value=10,
            key="neighborhood_size",
        )
        if mode == "Compare":
            compare_options = [track_id for track_id in song_options if track_id != selected_id]
            st.selectbox(
                "Compare with",
                compare_options,
                index=None,
                format_func=lambda track_id: labels[track_id],
                key="compare_search",
                on_change=_compare_changed,
                filter_mode="fuzzy",
                placeholder="Choose a second song…",
            )
        else:
            journey = st.session_state.journey_ids
            st.caption(f"Journey · {len(journey)} stop{'s' if len(journey) != 1 else ''}")
            back, clear = st.columns(2)
            back.button("← Back", width="stretch", disabled=len(journey) < 2, on_click=_journey_back)
            clear.button("Clear path", width="stretch", on_click=_journey_clear)

        st.markdown('<div class="section-label">Color by</div>', unsafe_allow_html=True)
        color_by = st.selectbox(
            "Color points by",
            ["Album", "Release Year", "Language", "Word Count", "Semantic Cluster"],
            key="color_mode",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
        time_cutoff = st.slider(
            "Universe through",
            min_year,
            max_year,
            max_year,
            key="time_cutoff",
            help="Move backward through release history and watch the atlas emerge.",
        )
        album_filter = st.multiselect(
            "Album",
            sorted(data["album_name"].dropna().unique()),
            placeholder="All albums",
            key="album_filter",
        )
        type_filter = st.multiselect(
            "Album type",
            sorted(data["album_type"].dropna().unique()),
            placeholder="All types",
            key="type_filter",
        )

        st.markdown('<div class="section-label">Advanced</div>', unsafe_allow_html=True)
        controls = {
            "labels": st.toggle("Label semantic neighbors", value=True, key="label_neighbors"),
            "fade": st.toggle("Fade distant songs", value=True, key="fade_distant"),
            "density": st.toggle("Scale dots by word count", value=False, key="lyrics_density"),
            "duplicates": st.toggle("Show duplicate releases", value=False, key="show_duplicates"),
            "mode": mode,
            "neighborhood_size": neighborhood_size,
        }

        filtered = data[data["release_year"].le(time_cutoff)]
        if album_filter:
            filtered = filtered[filtered["album_name"].isin(album_filter)]
        if type_filter:
            filtered = filtered[filtered["album_type"].isin(type_filter)]
        # Search is an explicit navigation action, so the selected song stays
        # visible even when it sits just outside the active filters.
        selected_row = data[data["track_id"].eq(selected_id)]
        if (
            not st.session_state.atlas_overview
            and not selected_row.empty
            and selected_id not in set(filtered["track_id"])
        ):
            filtered = pd.concat([filtered, selected_row], ignore_index=True)
        compare_id = st.session_state.get("compare_song_id") if mode == "Compare" else None
        compare_row = data[data["track_id"].eq(compare_id)] if compare_id else data.iloc[0:0]
        if not compare_row.empty and compare_id not in set(filtered["track_id"]):
            filtered = pd.concat([filtered, compare_row], ignore_index=True)
        if not controls["duplicates"]:
            filtered = (
                filtered.assign(_selected=filtered["track_id"].eq(selected_id))
                .sort_values(["_selected", "is_primary_version"], ascending=False)
                .drop_duplicates("canonical_title")
                .drop(columns="_selected")
            )

        st.markdown("---")
        st.caption(
            f"{data.canonical_title.nunique()} canonical songs · "
            f"{len(data)} releases · {min_year}–{max_year}"
        )
        st.markdown('<div class="source-line">● Spotify &nbsp; ● Genius &nbsp; ● Multilingual AI</div>', unsafe_allow_html=True)
    return filtered, color_by, controls


def render_song_panel(song: pd.Series, data: pd.DataFrame, neighborhood_size: int) -> None:
    st.markdown('<div class="section-label panel-section">Selected song</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="song-hero">
          <img class="song-cover" src="{_safe(_image_source(song.image_url))}" alt="Album cover">
          <div><div class="song-name">{_safe(song.track_name)}</div>
          <div class="song-album">{_safe(song.album_name)}</div>
          <div class="song-year">{_safe(song.release_year)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    spotify, genius = st.columns(2, gap="small")
    if _valid_url(song.spotify_url):
        spotify.link_button("▶ Spotify", str(song.spotify_url), width="stretch")
    else:
        spotify.caption("Spotify link unavailable")
    if _valid_url(song.genius_url):
        genius.link_button("Genius ↗", str(song.genius_url), width="stretch")
    else:
        genius.caption("Genius link unavailable")

    detail_pairs = [
        ("Album", song.album_name),
        ("Release year", song.release_year),
        ("Album type", song.album_type),
        ("Duration", format_duration(song.duration_ms)),
        ("Word count", f"{song.word_count:,}"),
        ("Characters", f"{song.character_count:,}"),
        ("Language", song.language),
    ]
    details = "".join(
        f'<div class="key">{_safe(key)}</div><div class="value">{_safe(value)}</div>'
        for key, value in detail_pairs
    )
    st.markdown(f'<div class="details-grid">{details}</div>', unsafe_allow_html=True)

    min_year, max_year = int(data.release_year.min()), int(data.release_year.max())
    timeline_position = (int(song.release_year) - min_year) / max(max_year - min_year, 1)
    st.markdown(
        f'<div class="timeline-label"><span>Catalog timeline</span><span>{song.release_year}</span></div>'
        f'<div class="timeline-track"><div style="width:{timeline_position * 100:.1f}%"></div></div>',
        unsafe_allow_html=True,
    )

    neighbors = similar_songs(song.track_id, data, neighborhood_size)
    st.markdown('<div class="section-label panel-section">Neighborhood story</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="semantic-story">{_safe(semantic_story(song, neighbors, data))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="section-label panel-section">{neighborhood_size} semantic neighbors</div>',
        unsafe_allow_html=True,
    )
    rows = []
    for rank, match in enumerate(neighbors.itertuples(), start=1):
        bar = max(4, min(100, float(match.similarity) * 100))
        rows.append(
            f'<div class="similar-row">'
            f'<div class="similar-rank">{rank}</div>'
            f'<img class="similar-cover" src="{_safe(_image_source(match.image_url))}" alt="">'
            f'<div><div class="similar-name">{_safe(match.track_name)}</div>'
            f'<div class="similar-album">{_safe(match.album_name)}</div>'
            f'<div class="similar-bar"><div style="width:{bar:.1f}%"></div></div></div>'
            f'<div class="similar-score">{match.similarity:.3f}</div>'
            f'</div>'
        )
    st.html(f'<div class="neighbor-scroll">{"".join(rows)}</div>')

    if not neighbors.empty:
        jump_key = f"neighbor_jump_{song.track_id}"
        neighbor_labels = neighbors.set_index("track_id")["track_name"].to_dict()

        def choose_neighbor() -> None:
            target = st.session_state.get(jump_key)
            if target:
                _select_song(target, focus=True)

        st.markdown(
            '<div class="continue-cue">Continue the journey <span>→</span></div>',
            unsafe_allow_html=True,
        )
        st.selectbox(
            "Explore a nearby song",
            neighbors["track_id"].tolist(),
            index=None,
            format_func=lambda track_id: neighbor_labels[track_id],
            key=jump_key,
            on_change=choose_neighbor,
            filter_mode="fuzzy",
            placeholder="Travel to a neighboring song…",
            label_visibility="collapsed",
        )

    st.markdown('<div class="section-label panel-section">Lyrics preview</div>', unsafe_allow_html=True)
    preview = "\n".join(str(song.lyrics_clean).splitlines()[:8])
    st.markdown(f'<div class="lyrics-preview">{_safe(preview)}</div>', unsafe_allow_html=True)


def render_compare_panel(first: pd.Series, second: pd.Series, data: pd.DataFrame, size: int) -> None:
    first_neighbors = similar_songs(first.track_id, data, size)
    second_neighbors = similar_songs(second.track_id, data, size)
    first_titles = set(first_neighbors.canonical_title)
    second_titles = set(second_neighbors.canonical_title)
    shared = first_titles & second_titles
    similarity = pair_similarity(first.track_id, second.track_id)
    distance = ((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** .5

    st.markdown('<div class="section-label panel-section">Compare songs</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="compare-title"><span>{_safe(first.track_name)}</span><b>↔</b>'
        f'<span>{_safe(second.track_name)}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="compare-metrics"><div><b>{similarity:.3f}</b><span>cosine similarity</span></div>'
        f'<div><b>{distance:.2f}</b><span>map distance</span></div>'
        f'<div><b>{len(shared)}</b><span>shared neighbors</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="details-grid"><div class="key">Albums</div>'
        f'<div class="value">{_safe(first.album_name)}<br>{_safe(second.album_name)}</div>'
        f'<div class="key">Release years</div>'
        f'<div class="value">{first.release_year} · {second.release_year}</div>'
        f'<div class="key">Unique neighbors</div>'
        f'<div class="value">{len(first_titles - shared)} blue · {len(second_titles - shared)} amber</div></div>',
        unsafe_allow_html=True,
    )
    if shared:
        names = data[data.canonical_title.isin(shared)].drop_duplicates("canonical_title").track_name
        st.markdown(
            f'<div class="semantic-story"><b>Shared neighborhood</b><br>{_safe(", ".join(names.head(8)))}</div>',
            unsafe_allow_html=True,
        )


def render_overview_panel(data: pd.DataFrame) -> None:
    st.markdown('<div class="section-label panel-section">Atlas overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="overview-welcome"><div class="overview-orbit">✦</div>'
        '<h3>The complete semantic universe</h3>'
        '<p>No song is selected. Every point represents a canonical BTS song positioned by '
        'lyrical similarity.</p><p><b>Select any point</b> or use fuzzy search to reveal its neighborhood.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="compare-metrics"><div><b>{data.canonical_title.nunique()}</b>'
        f'<span>canonical songs</span></div><div><b>{data.album_name.nunique()}</b>'
        f'<span>albums</span></div><div><b>{data.release_year.min()}–{data.release_year.max()}</b>'
        f'<span>timeline</span></div></div>',
        unsafe_allow_html=True,
    )


@st.fragment
def render_explorer(
    data: pd.DataFrame,
    filtered: pd.DataFrame,
    color_by: str,
    controls: dict[str, object],
) -> None:
    """Rerender only the atlas explorer when a point is selected."""
    map_column, detail_column = st.columns([4.8, 1.35], gap="small")
    with map_column:
        header, status = st.columns([4, 1])
        header.markdown(
            '<div class="atlas-heading">Explore the semantic universe</div>'
            f'<div class="panel-subtitle">{controls["mode"]} mode · Select a song to travel through lyrical space.</div>',
            unsafe_allow_html=True,
        )
        status.markdown(
            f'<div class="map-status">{len(filtered)} songs visible<br>'
            f'<span>{color_by} · UMAP 2D</span></div>',
            unsafe_allow_html=True,
        )
        if filtered.empty:
            st.warning("No songs match the current filters.")
        else:
            focus_id = st.session_state.get("focus_song_id")
            active_selected_id = (
                None if st.session_state.atlas_overview else st.session_state.selected_song_id
            )
            event = st.plotly_chart(
                build_atlas_figure(
                    filtered,
                    data,
                    active_selected_id,
                    color_by,
                    controls,
                    focus_id=focus_id,
                    viewport_revision=st.session_state.viewport_revision,
                    neighborhood_size=int(controls["neighborhood_size"]),
                    compare_id=(
                        st.session_state.get("compare_song_id")
                        if controls["mode"] == "Compare" and not st.session_state.atlas_overview
                        else None
                    ),
                    journey_ids=(
                        st.session_state.journey_ids if controls["mode"] == "Explore" else None
                    ),
                ),
                width="stretch",
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "responsive": True,
                    "doubleClick": "reset+autosize",
                    "displayModeBar": "hover",
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                },
                on_select="rerun",
                selection_mode="points",
                key="atlas_plot_v2",
            )
            st.session_state.focus_song_id = None
            if event and event.selection and event.selection.points:
                custom = event.selection.points[0].get("customdata")
                if custom and (
                    st.session_state.atlas_overview
                    or custom[0] != st.session_state.selected_song_id
                ):
                    if st.session_state.atlas_overview:
                        _select_song(custom[0], focus=False)
                    elif controls["mode"] == "Compare":
                        st.session_state.compare_song_id = custom[0]
                    else:
                        _select_song(custom[0], focus=False)
                    st.rerun(scope="fragment")

    selected_rows = data[data["track_id"] == st.session_state.selected_song_id]
    if selected_rows.empty:
        selected_rows = data.iloc[[0]]
    with detail_column:
        selected_song = selected_rows.iloc[0]
        compare_id = st.session_state.get("compare_song_id")
        compare_rows = data[data["track_id"].eq(compare_id)] if compare_id else data.iloc[0:0]
        if st.session_state.atlas_overview:
            render_overview_panel(data)
        elif controls["mode"] == "Compare" and not compare_rows.empty:
            render_compare_panel(
                selected_song,
                compare_rows.iloc[0],
                data,
                int(controls["neighborhood_size"]),
            )
        else:
            render_song_panel(selected_song, data, int(controls["neighborhood_size"]))
            journey = st.session_state.journey_ids
            if len(journey) > 1:
                journey_rows = data.set_index("track_id").reindex(journey).dropna(subset=["track_name"])
                st.markdown('<div class="section-label panel-section">Your journey</div>', unsafe_allow_html=True)
                st.markdown(
                    '<div class="journey-path">' + "<span>↓</span>".join(
                        f'<b>{_safe(name)}</b>' for name in journey_rows.track_name
                    ) + "</div>",
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="section-label panel-section">Atlas overview</div>', unsafe_allow_html=True)
        mini_data = data[data["is_primary_version"]]
        mini_event = st.plotly_chart(
            build_minimap(
                mini_data,
                None if st.session_state.atlas_overview else selected_song.track_id,
                st.session_state.journey_ids,
            ),
            width="stretch",
            config={"displayModeBar": False, "displaylogo": False},
            on_select="rerun",
            selection_mode="points",
            key="atlas_minimap",
        )
        st.caption("Select a point in the overview to move across the atlas.")
        if mini_event and mini_event.selection and mini_event.selection.points:
            custom = mini_event.selection.points[0].get("customdata")
            if custom and custom[0] != st.session_state.selected_song_id:
                _select_song(custom[0], focus=True)
                st.rerun(scope="fragment")


def render_dashboard() -> None:
    apply_styles()
    data = load_dashboard_data()
    if "selected_song_id" not in st.session_state:
        black_swan = data[
            data["track_name"].str.casefold().eq("black swan") & data["is_primary_version"]
        ]
        st.session_state.selected_song_id = (
            black_swan.iloc[0].track_id if not black_swan.empty else data.iloc[0].track_id
        )
    st.session_state.setdefault("focus_song_id", None)
    st.session_state.setdefault("viewport_revision", "atlas-v2")
    st.session_state.setdefault("experience_mode", "Explore")
    st.session_state.setdefault("atlas_overview", True)
    st.session_state.setdefault("journey_ids", [])
    st.session_state.setdefault("recent_searches", [])
    st.session_state.setdefault("compare_song_id", None)

    filtered, color_by, controls = render_sidebar(data)
    render_explorer(data, filtered, color_by, controls)
    st.markdown(
        '<div class="microcopy atlas-footer">Made with 💜 for ARMY &nbsp;·&nbsp; '
        'Every point is a song; distance represents lyrical similarity.</div>',
        unsafe_allow_html=True,
    )
