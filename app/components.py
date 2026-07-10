"""Reusable Streamlit interface components for BTS Song Atlas."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import (
    format_duration,
    load_dashboard_data,
    load_personal_atlas_data,
    load_personal_history,
    pair_similarity,
    semantic_story,
    similar_songs,
)
from visualization import build_atlas_figure, build_home_preview, build_minimap, build_personal_atlas_figure
from views.router import render_page


ALL_SONGS = "__all_songs__"
NAV_ITEMS = [
    {
        "slug": "home",
        "label": "Home",
        "subtitle": "Choose your experience",
        "icon": "⌂",
        "badge": None,
    },
    {
        "slug": "atlas",
        "label": "Atlas",
        "subtitle": "2D semantic map",
        "icon": "◎",
        "badge": None,
    },
    {
        "slug": "explorer",
        "label": "Explorer",
        "subtitle": "3D semantic universe",
        "icon": "✦",
        "badge": "Soon",
    },
    {
        "slug": "compare",
        "label": "Compare",
        "subtitle": "Compare songs & themes",
        "icon": "≍",
        "badge": None,
    },
    {
        "slug": "insights",
        "label": "Insights",
        "subtitle": "Statistics & visualizations",
        "icon": "▥",
        "badge": None,
    },
    {
        "slug": "personal",
        "label": "Personal Atlas",
        "subtitle": "Your listening journey",
        "icon": "◌",
        "badge": None,
    },
    {
        "slug": "about",
        "label": "About",
        "subtitle": "About this project",
        "icon": "ⓘ",
        "badge": None,
    },
]
CLUSTER_COLORS = {
    -1: "#777b94",
    0: "#4f6cff",
    1: "#a855f7",
    2: "#1dd98f",
    3: "#ffd54f",
    4: "#ff8c42",
    5: "#ff4fa3",
    6: "#1ad6ff",
}
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


def _logo_data_uri() -> str:
    logo_path = Path(__file__).resolve().parents[1] / "docs" / "assets" / "BTS_logo.jpg"
    if not logo_path.exists():
        return FALLBACK_COVER
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _page_href(slug: str) -> str:
    return f"?page={slug}"


def _current_page() -> str:
    raw = st.query_params.get("page", "home")
    slug = raw[0] if isinstance(raw, list) else raw
    known = {item["slug"] for item in NAV_ITEMS}
    if slug == "journey":
        return "atlas"
    return slug if slug in known else "home"


def _navigate(slug: str) -> None:
    st.query_params["page"] = slug
    st.rerun()


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
    st.session_state.recent_searches = [track_id, *recent][:5]


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


def _stats_summary(data: pd.DataFrame) -> dict[str, int]:
    primary = data[data["is_primary_version"]]
    return {
        "songs": int(primary["canonical_title"].nunique()),
        "clusters": int(primary.loc[primary["cluster"] != -1, "cluster"].nunique()),
        "years": int(primary["release_year"].max() - primary["release_year"].min() + 1),
        "universe": 1,
    }


def _song_options(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    primary = data[data["is_primary_version"]].sort_values("track_name")
    song_options = primary["track_id"].tolist()
    labels = primary.set_index("track_id").apply(
        lambda row: f"{row['track_name']} · {row['album_name']}",
        axis=1,
    ).to_dict()
    labels[ALL_SONGS] = "All songs"
    return primary, [ALL_SONGS, *song_options], labels


def _selected_song_row(data: pd.DataFrame) -> pd.Series:
    selected_rows = data[data["track_id"] == st.session_state.selected_song_id]
    if selected_rows.empty:
        return data.iloc[0]
    return selected_rows.iloc[0]


def _recent_song_rows(data: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    ordered_ids: list[str] = []
    for track_id in reversed(st.session_state.get("journey_ids", [])):
        if track_id not in ordered_ids:
            ordered_ids.append(track_id)
    for track_id in st.session_state.get("recent_searches", []):
        if track_id not in ordered_ids:
            ordered_ids.append(track_id)
    if st.session_state.get("selected_song_id") and st.session_state.selected_song_id not in ordered_ids:
        ordered_ids.insert(0, st.session_state.selected_song_id)
    rows = data.set_index("track_id").reindex(ordered_ids).dropna(subset=["track_name"]).reset_index()
    return rows.head(limit)


def _cluster_color(value: object) -> str:
    try:
        cluster = int(value)
    except Exception:
        return "#777b94"
    return CLUSTER_COLORS.get(cluster, "#b26cff")


def _init_state(data: pd.DataFrame) -> None:
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
    st.session_state.setdefault("song_search", ALL_SONGS)


def render_app_sidebar(data: pd.DataFrame, current_page: str) -> None:
    selected = _selected_song_row(data)
    logo = _logo_data_uri()
    nav_html = []
    for item in NAV_ITEMS:
        active = " active" if item["slug"] == current_page else ""
        badge = f'<span class="nav-badge">{item["badge"]}</span>' if item["badge"] else ""
        nav_html.append(
            f'<a class="nav-link{active}" href="{_page_href(item["slug"])}" target="_self">'
            f'<div class="nav-icon">{item["icon"]}</div>'
            f'<div class="nav-copy"><div class="nav-label">{_safe(item["label"])}</div>'
            f'<div class="nav-subtitle">{_safe(item["subtitle"])}</div></div>{badge}</a>'
        )
    sidebar_html = f"""
    <div class="sidebar-shell">
      <div class="sidebar-brand">
        <img class="sidebar-logo" src="{logo}" alt="BTS Song Atlas logo">
        <div>
          <div class="sidebar-title">BTS SONG ATLAS</div>
          <div class="sidebar-subtitle">Explore the Universe of BTS Lyrics</div>
        </div>
      </div>
      <div class="sidebar-nav">{''.join(nav_html)}</div>
      <div class="now-playing-card">
        <div class="now-playing-kicker">Now playing</div>
        <div class="now-playing-row">
          <img class="now-playing-cover" src="{_safe(_image_source(selected.image_url))}" alt="">
          <div>
            <div class="now-playing-name">{_safe(selected.track_name)}</div>
            <div class="now-playing-album">{_safe(selected.album_name)}</div>
          </div>
        </div>
        <div class="now-playing-note">The atlas remembers your current song while you move through experiences.</div>
      </div>
    </div>
    """
    with st.sidebar:
        st.markdown(sidebar_html, unsafe_allow_html=True)


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
        f'<div class="value">{len(first_titles - shared)} violet · {len(second_titles - shared)} amber</div></div>',
        unsafe_allow_html=True,
    )
    if shared:
        names = data[data.canonical_title.isin(shared)].drop_duplicates("canonical_title").track_name
        st.markdown(
            f'<div class="semantic-story"><b>Shared neighborhood</b><br>{_safe(", ".join(names.head(8)))}</div>',
            unsafe_allow_html=True,
        )


def render_overview_panel(data: pd.DataFrame, title: str = "Atlas overview") -> None:
    st.markdown(f'<div class="section-label panel-section">{_safe(title)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="overview-welcome"><div class="overview-orbit">✦</div>'
        '<h3>The complete semantic universe</h3>'
        '<p>No song is selected. Every point represents a canonical BTS song positioned by '
        'lyrical similarity.</p><p><b>Select any point</b> or use search to begin exploration.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="compare-metrics"><div><b>{data.canonical_title.nunique()}</b>'
        f'<span>canonical songs</span></div><div><b>{data.album_name.nunique()}</b>'
        f'<span>albums</span></div><div><b>{data.release_year.min()}–{data.release_year.max()}</b>'
        f'<span>timeline</span></div></div>',
        unsafe_allow_html=True,
    )


def render_placeholder_page(title: str, subtitle: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="placeholder-shell">
          <div class="hero-kicker">COMING SOON</div>
          <h1 class="hero-title">{_safe(title)}</h1>
          <p class="hero-subtitle">{_safe(subtitle)}</p>
          <div class="placeholder-copy">{_safe(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_personal_metric(label: str, value: str, note: str, icon: str) -> None:
    st.markdown(
        f'<div class="personal-metric"><div class="personal-metric-icon">{_safe(icon)}</div>'
        f'<div><div class="personal-metric-label">{_safe(label)}</div>'
        f'<div class="personal-metric-value">{_safe(value)}</div>'
        f'<div class="personal-metric-note">{_safe(note)}</div></div></div>',
        unsafe_allow_html=True,
    )


def _render_ranked_list(data: pd.DataFrame, title_column: str, subtitle_column: str) -> None:
    rows = []
    for rank, row in enumerate(data.head(7).itertuples(index=False), 1):
        values = row._asdict()
        rows.append(
            f'<div class="personal-rank-row"><span class="personal-rank-number">{rank}</span>'
            f'<div class="personal-rank-copy"><b>{_safe(values[title_column])}</b>'
            f'<span>{_safe(values[subtitle_column])}</span></div>'
            f'<strong>{float(values["hours_played"]):.2f}h</strong></div>'
        )
    st.markdown(f'<div class="personal-ranked-list">{"".join(rows)}</div>', unsafe_allow_html=True)


def _render_mastery_section(personal_map: pd.DataFrame) -> None:
    mastery_counts = personal_map["mastery_level"].value_counts().sort_index()
    mastery_colors = ["#34205f", "#6630c8", "#a13bc2", "#dc4c91", "#ff9f32"]
    figure = go.Figure()
    for level, count in mastery_counts.items():
        figure.add_trace(
            go.Bar(
                x=[int(count)],
                y=["Songs"],
                orientation="h",
                name=f"Level {int(level)}",
                marker_color=mastery_colors[int(level) % len(mastery_colors)],
                hovertemplate=f"Level {int(level)}: %{{x}} songs<extra></extra>",
            )
        )
    figure.update_layout(
        barmode="stack",
        height=175,
        margin={"l": 8, "r": 8, "t": 10, "b": 34},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dcd7e9", "size": 11},
        legend={"orientation": "h", "x": 0, "y": -.2},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False, "displaylogo": False},
        key="personal_mastery_plot",
    )


def render_personal_atlas_page() -> None:
    st.markdown(
        """
        <div class="personal-hero">
          <div class="personal-hero-icon">♙</div>
          <div><h1>Personal <span>Atlas</span></h1>
          <p>Your listening journey across the BTS universe.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        personal_map, song_league, album_league = load_personal_atlas_data()
    except (FileNotFoundError, OSError, ValueError):
        st.markdown(
            '<div class="personal-empty"><b>Your Personal Atlas data is not available yet.</b>'
            '<span>Add a Spotify Extended Streaming History export and run the Personal Atlas pipeline.</span></div>',
            unsafe_allow_html=True,
        )
        return

    if personal_map.empty:
        st.markdown(
            '<div class="personal-empty"><b>Your Personal Atlas is empty.</b>'
            '<span>Run the Personal Atlas pipeline after adding listening history.</span></div>',
            unsafe_allow_html=True,
        )
        return

    personal_map = personal_map.copy()
    personal_map["has_listening_history"] = personal_map["has_listening_history"].fillna(False).astype(bool)
    explored = int(personal_map["has_listening_history"].sum())
    highest_level = int(personal_map["mastery_level"].max())
    total_hours = float(song_league["hours_played"].sum()) if not song_league.empty else 0.0
    explored_albums = int(album_league.loc[album_league["hours_played"] > 0, "master_metadata_album_album_name"].nunique())
    total_albums = int(album_league["master_metadata_album_album_name"].nunique())

    metric_columns = st.columns(4, gap="small")
    metrics = [
        ("Total listening hours", f"{total_hours:.1f}h", "Across matched BTS history", "◉"),
        ("Songs explored", f"{explored} / {len(personal_map)}", f"{explored / len(personal_map):.1%} of releases", "♫"),
        ("Albums explored", f"{explored_albums} / {total_albums}", "Listening-history albums", "◌"),
        ("Highest mastery", f"Level {highest_level}", "Based on listening hours", "✦"),
    ]
    for column, metric in zip(metric_columns, metrics, strict=True):
        with column:
            _render_personal_metric(*metric)

    map_column, side_column = st.columns([2.15, 1], gap="small")
    with map_column:
        with st.container(border=True, key="personal_map_card"):
            title_column, controls_column = st.columns([1.25, 1], gap="small")
            with title_column:
                st.markdown(
                    '<div class="personal-section-title">Your listening intensity</div>'
                    '<div class="personal-section-copy">Each point is a BTS song release in the semantic atlas.</div>',
                    unsafe_allow_html=True,
                )
            with controls_column:
                color_mode = st.segmented_control(
                    "Color mode",
                    ["Listening intensity", "Semantic clusters"],
                    default="Listening intensity",
                    label_visibility="collapsed",
                    key="personal_color_mode",
                )
            control_columns = st.columns([1.4, 1, 1.25, 1], gap="small")
            with control_columns[0]:
                personal_options = personal_map.sort_values(["track_name", "album_name"])
                personal_labels = personal_options.set_index("track_id").apply(
                    lambda row: f"{row['track_name']} · {row['album_name']}",
                    axis=1,
                ).to_dict()
                personal_labels[ALL_SONGS] = "All songs"
                selected_personal_song = st.selectbox(
                    "Find a song or album",
                    [ALL_SONGS, *personal_options["track_id"].tolist()],
                    format_func=lambda track_id: personal_labels[track_id],
                    label_visibility="collapsed",
                    key="personal_song_select",
                )
            with control_columns[1]:
                listened_only = st.toggle("Listened only", key="personal_listened_only")
            with control_columns[2]:
                show_duplicates = st.toggle(
                    "Show duplicate releases",
                    value=False,
                    key="personal_show_duplicates",
                )
            with control_columns[3]:
                size_by_plays = st.toggle("Size by plays", value=True, key="personal_size_by_plays")

            visible_map = personal_map
            if listened_only:
                visible_map = visible_map[visible_map["has_listening_history"]]
            if selected_personal_song != ALL_SONGS:
                visible_map = visible_map[visible_map["track_id"] == selected_personal_song]
            if not show_duplicates:
                visible_map = (
                    visible_map.sort_values("is_primary_version", ascending=False)
                    .drop_duplicates("canonical_title")
                )
            if visible_map.empty:
                st.info("No songs match the current Personal Atlas filters.")
            else:
                st.plotly_chart(
                    build_personal_atlas_figure(visible_map, color_mode, size_by_plays),
                    width="stretch",
                    config={"displaylogo": False, "scrollZoom": True, "responsive": True},
                    key="personal_atlas_plot",
                )
            st.caption("Brighter points represent more listening. Unexplored songs remain as quiet landmarks.")

    with side_column:
        with st.container(border=True, key="personal_top_songs"):
            st.markdown('<div class="personal-section-title">Top songs</div>', unsafe_allow_html=True)
            _render_ranked_list(
                song_league.sort_values("hours_played", ascending=False),
                "master_metadata_track_name",
                "master_metadata_album_album_name",
            )
        with st.container(border=True, key="personal_top_albums"):
            st.markdown('<div class="personal-section-title">Top albums</div>', unsafe_allow_html=True)
            _render_ranked_list(
                album_league.sort_values("hours_played", ascending=False),
                "master_metadata_album_album_name",
                "master_metadata_album_artist_name",
            )

    mastery_column, timeline_column, unexplored_column = st.columns([1.25, 1.25, 1], gap="small")
    with mastery_column:
        with st.container(border=True, key="personal_mastery_card"):
            st.markdown(
                '<div class="personal-section-title">Listening by mastery level</div>'
                '<div class="personal-section-copy">Level 0 is unexplored; higher levels reflect more listening time.</div>',
                unsafe_allow_html=True,
            )
            _render_mastery_section(personal_map)

    try:
        history = load_personal_history().copy()
        history["ts"] = pd.to_datetime(history["ts"], utc=True, errors="coerce")
        history = history.dropna(subset=["ts"])
    except (FileNotFoundError, OSError, ValueError):
        history = pd.DataFrame()

    with timeline_column:
        with st.container(border=True, key="personal_timeline_card"):
            st.markdown('<div class="personal-section-title">Listening timeline</div>', unsafe_allow_html=True)
            if history.empty:
                st.caption("Event-level listening history is unavailable.")
            else:
                monthly = history.set_index("ts")["hours_played"].resample("MS").sum()
                timeline = go.Figure(
                    go.Scatter(
                        x=monthly.index,
                        y=monthly.values,
                        mode="lines+markers",
                        line={"color": "#a95cff", "width": 2.5},
                        marker={"size": 5, "color": "#d780ff"},
                        fill="tozeroy",
                        fillcolor="rgba(139,65,235,.14)",
                        hovertemplate="%{x|%b %Y}<br>%{y:.2f} hours<extra></extra>",
                    )
                )
                timeline.update_layout(
                    height=220,
                    margin={"l": 6, "r": 6, "t": 14, "b": 8},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#9fa4be", "size": 10},
                    xaxis={"showgrid": False},
                    yaxis={"gridcolor": "rgba(255,255,255,.05)", "title": "Hours"},
                )
                st.plotly_chart(timeline, width="stretch", config={"displayModeBar": False}, key="personal_timeline")

    with unexplored_column:
        with st.container(border=True, key="personal_unexplored_card"):
            st.markdown('<div class="personal-section-title">Unexplored songs</div>', unsafe_allow_html=True)
            listened_titles = set(personal_map.loc[personal_map["has_listening_history"], "canonical_title"])
            unexplored_releases = personal_map[~personal_map["has_listening_history"]].copy()
            unexplored_releases["listened_elsewhere"] = unexplored_releases["canonical_title"].isin(listened_titles)
            alternate_releases = int(unexplored_releases["listened_elsewhere"].sum())
            unexplored_songs = (
                unexplored_releases[~unexplored_releases["listened_elsewhere"]]
                .sort_values(["is_primary_version", "track_name"], ascending=[False, True])
                .drop_duplicates("canonical_title")
            )
            if unexplored_songs.empty:
                st.caption("Every canonical song in the current atlas has listening history.")
            else:
                items = []
                for row in unexplored_songs.itertuples():
                    items.append(
                        f'<div class="personal-recent-row"><div><b>{_safe(row.track_name)}</b>'
                        f'<span>{_safe(row.album_name)}</span></div></div>'
                    )
                st.markdown(f'<div class="personal-recent-list personal-unexplored-list">{"".join(items)}</div>', unsafe_allow_html=True)
                st.caption(
                    f"{len(unexplored_songs)} canonical songs are unexplored. "
                    f"Another {alternate_releases} unplayed releases are alternate versions of songs you have heard."
                )


def render_about_page(data: pd.DataFrame) -> None:
    stats = _stats_summary(data)
    st.markdown(
        """
        <div class="hero-kicker">ABOUT THE PROJECT</div>
        <h1 class="hero-title">BTS Song Atlas</h1>
        <p class="hero-subtitle">An interactive semantic explorer built from multilingual BTS lyrics.</p>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4, gap="small")
    for column, (label, value) in zip(
        (c1, c2, c3, c4),
        [("Songs", stats["songs"]), ("Clusters", stats["clusters"]), ("Years", stats["years"]), ("Universe", stats["universe"])],
        strict=True,
    ):
        column.markdown(
            f'<div class="metric-card"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="content-card">
              <div class="section-label">Why it exists</div>
              <p class="body-copy">BTS Song Atlas is designed as a map-first product. Instead of organizing songs only by album or year, it lets listeners move through lyrical meaning as if they were navigating a universe.</p>
              <p class="body-copy">Every point is a song. Nearby points share semantic similarity in the multilingual lyric embedding space. The 2D atlas remains the primary analytical surface.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div class="content-card">
              <div class="section-label">Technical core</div>
              <ul class="about-list">
                <li>Spotify metadata + Genius lyric matching</li>
                <li>SentenceTransformers multilingual embeddings</li>
                <li>Cosine similarity for neighborhoods and comparisons</li>
                <li>Canonical-song UMAP projection for the atlas geometry</li>
                <li>Streamlit + Plotly for interactive exploration</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_insights_page(data: pd.DataFrame) -> None:
    primary = data[data["is_primary_version"]].copy()
    cluster_counts = (
        primary.assign(cluster_label=primary["cluster"].map(lambda v: "Noise" if v == -1 else f"Cluster {int(v)}"))
        .groupby("cluster_label")
        .size()
        .sort_values(ascending=False)
    )
    year_counts = primary.groupby("release_year").size()

    st.markdown(
        """
        <div class="hero-kicker">INSIGHTS</div>
        <h1 class="hero-title">Atlas Statistics</h1>
        <p class="hero-subtitle">A compact analytical view of the semantic universe behind the atlas.</p>
        """,
        unsafe_allow_html=True,
    )

    stats = _stats_summary(data)
    cols = st.columns(4, gap="small")
    for column, (label, value) in zip(
        cols,
        [
            ("Canonical songs", stats["songs"]),
            ("Semantic clusters", stats["clusters"]),
            ("Albums", int(primary["album_name"].nunique())),
            ("Years covered", f"{primary['release_year'].min()}–{primary['release_year'].max()}"),
        ],
        strict=True,
    ):
        column.markdown(
            f'<div class="metric-card"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns(2, gap="large")
    with left:
        cluster_fig = go.Figure(
            go.Bar(
                x=cluster_counts.index,
                y=cluster_counts.values,
                marker_color="#9d5cff",
                opacity=0.9,
            )
        )
        cluster_fig.update_layout(
            title="Songs by cluster",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(12,14,31,.78)",
            font={"color": "#ebe7f7"},
            margin={"l": 10, "r": 10, "t": 45, "b": 10},
            height=340,
        )
        st.plotly_chart(cluster_fig, width="stretch", config={"displayModeBar": False, "displaylogo": False})
    with right:
        year_fig = go.Figure(
            go.Scatter(
                x=year_counts.index,
                y=year_counts.values,
                mode="lines+markers",
                line={"color": "#54c8ff", "width": 3},
                marker={"size": 8, "color": "#9d5cff"},
                fill="tozeroy",
                fillcolor="rgba(84,200,255,.12)",
            )
        )
        year_fig.update_layout(
            title="Songs by release year",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(12,14,31,.78)",
            font={"color": "#ebe7f7"},
            margin={"l": 10, "r": 10, "t": 45, "b": 10},
            height=340,
        )
        st.plotly_chart(year_fig, width="stretch", config={"displayModeBar": False, "displaylogo": False})


def _render_recently_explored(data: pd.DataFrame) -> None:
    recent = _recent_song_rows(data)
    st.markdown('<div class="section-label">Recently explored</div>', unsafe_allow_html=True)
    if recent.empty:
        st.markdown(
            """
            <div class="empty-state-card">
              <div class="empty-state-title">Your atlas is waiting</div>
              <div class="empty-state-copy">Choose Atlas or Compare to start exploring the semantic universe and building a listening path.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    columns = st.columns(len(recent), gap="small")
    for column, row in zip(columns, recent.itertuples(), strict=True):
        with column:
            st.markdown(
                f"""
                <div class="recent-card">
                  <div class="recent-head"><span class="recent-dot" style="background:{_cluster_color(row.cluster)}"></span>{_safe(row.track_name)}</div>
                  <div class="recent-album">{_safe(row.album_name)}</div>
                  <div class="recent-cluster">{_safe('Reflection' if row.cluster == 0 else f'Cluster {int(row.cluster)}' if row.cluster != -1 else 'Noise')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_home_page(data: pd.DataFrame) -> None:
    primary, _, _ = _song_options(data)
    stats = _stats_summary(data)
    _, about_col = st.columns([5, 1.2], gap="small")
    with about_col:
        st.button("About the Atlas", key="about_cta", width="stretch", on_click=_navigate, args=("about",))

    hero, preview = st.columns([1.2, 1.25], gap="large")
    with hero:
        st.markdown(
            """
            <div class="hero-kicker">WELCOME TO</div>
            <h1 class="hero-title">BTS Song <span>Atlas</span></h1>
            <p class="hero-subtitle">Explore the semantic universe of BTS lyrics</p>
            <p class="hero-description">Every point is a song. Every color is a theme. Every connection tells a story.</p>
            """,
            unsafe_allow_html=True,
        )
        metrics = st.columns(4, gap="small")
        for column, (label, value, icon) in zip(
            metrics,
            [
                ("Songs", stats["songs"], "♫"),
                ("Clusters", stats["clusters"], "✺"),
                ("Years", stats["years"], "◷"),
                ("Universe", stats["universe"], "◌"),
            ],
            strict=True,
        ):
            column.markdown(
                f'<div class="metric-card"><div class="metric-icon">{icon}</div>'
                f'<div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )
    with preview:
        st.plotly_chart(
            build_home_preview(primary),
            width="stretch",
            config={"displayModeBar": False, "displaylogo": False, "responsive": True},
            key="home_preview_plot",
        )

    st.markdown('<div class="section-label home-section">Choose your experience</div>', unsafe_allow_html=True)
    cards = [
        {
            "title": "Atlas",
            "subtitle": "2D Semantic Map",
            "description": "Analyze the lyrical landscape in 2D. Discover themes, clusters, and relationships.",
            "icon": "◎",
            "action": "Open Atlas",
            "slug": "atlas",
            "soon": False,
        },
        {
            "title": "Explorer",
            "subtitle": "3D Semantic Universe",
            "description": "Fly through the semantic universe in 3D. Rotate, zoom, and explore freely.",
            "icon": "✦",
            "action": "Coming soon",
            "slug": "explorer",
            "soon": True,
        },
        {
            "title": "Compare",
            "subtitle": "Compare Songs",
            "description": "Compare songs, themes, and eras. See how they relate in semantic space.",
            "icon": "≍",
            "action": "Compare Now",
            "slug": "compare",
            "soon": False,
        },
        {
            "title": "Insights",
            "subtitle": "Statistics & Visuals",
            "description": "Dive into insights about themes, eras, vocabulary, and atlas structure.",
            "icon": "▥",
            "action": "View Insights",
            "slug": "insights",
            "soon": False,
        },
        {
            "title": "Personal Atlas",
            "subtitle": "Your Listening Journey",
            "description": "See your Spotify listening history glow across the semantic atlas.",
            "icon": "◌",
            "action": "Open Personal Atlas",
            "slug": "personal",
            "soon": False,
        },
    ]
    rows = [cards[:3], cards[3:]]
    for row_cards in rows:
        columns = st.columns(len(row_cards), gap="small")
        for column, card in zip(columns, row_cards, strict=True):
            with column:
                badge = '<span class="card-badge">Soon</span>' if card["soon"] else ""
                st.markdown(
                    f"""
                    <div class="experience-card">
                      <div class="experience-icon">{card['icon']}</div>
                      <div class="experience-title">{_safe(card['title'])}{badge}</div>
                      <div class="experience-subtitle">{_safe(card['subtitle'])}</div>
                      <div class="experience-copy">{_safe(card['description'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.button(
                    card["action"],
                    key=f"card_{card['slug']}",
                    width="stretch",
                    on_click=_navigate if not card["soon"] else None,
                    args=(card["slug"],) if not card["soon"] else (),
                    disabled=card["soon"],
                )

    _render_recently_explored(data)


def render_atlas_search_bar(data: pd.DataFrame) -> None:
    _, search_options, labels = _song_options(data)
    if "song_search" not in st.session_state:
        st.session_state.song_search = ALL_SONGS
    st.selectbox(
        "Search for a song",
        search_options,
        format_func=lambda track_id: labels[track_id],
        key="song_search",
        on_change=_search_changed,
        filter_mode="fuzzy",
        placeholder="Search for a song, theme, or lyric…",
        label_visibility="collapsed",
    )


def render_atlas_controls_panel(data: pd.DataFrame, forced_mode: str) -> tuple[pd.DataFrame, str, dict[str, object]]:
    min_year, max_year = int(data.release_year.min()), int(data.release_year.max())
    primary, _, labels = _song_options(data)
    selected_id = st.session_state.selected_song_id

    st.session_state.experience_mode = forced_mode

    st.markdown('<div class="section-label">Search</div>', unsafe_allow_html=True)
    render_atlas_search_bar(data)

    st.markdown('<div class="section-label">Atlas controls</div>', unsafe_allow_html=True)
    neighborhood_size = st.select_slider(
        "Top similar songs",
        options=[5, 10, 20, 50],
        value=st.session_state.get("neighborhood_size", 10),
        key="neighborhood_size",
    )
    if forced_mode == "Compare":
        compare_options = [track_id for track_id in primary["track_id"].tolist() if track_id != selected_id]
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
        back, clear = st.columns(2, gap="small")
        back.button("← Back", width="stretch", disabled=len(journey) < 2, on_click=_journey_back)
        clear.button("Clear path", width="stretch", on_click=_journey_clear)

    st.markdown('<div class="section-label">Visual controls</div>', unsafe_allow_html=True)
    color_by = st.selectbox(
        "Color points by",
        ["Album", "Release Year", "Language", "Word Count", "Semantic Cluster"],
        key="color_mode",
        label_visibility="collapsed",
    )
    time_cutoff = st.slider(
        "Universe through",
        min_year,
        max_year,
        st.session_state.get("time_cutoff", max_year),
        key="time_cutoff",
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

    controls = {
        "labels": st.toggle("Label semantic neighbors", value=st.session_state.get("label_neighbors", True), key="label_neighbors"),
        "fade": st.toggle("Fade distant songs", value=st.session_state.get("fade_distant", True), key="fade_distant"),
        "density": st.toggle("Scale dots by word count", value=st.session_state.get("lyrics_density", False), key="lyrics_density"),
        "duplicates": st.toggle("Show duplicate releases", value=st.session_state.get("show_duplicates", False), key="show_duplicates"),
        "mode": forced_mode,
        "neighborhood_size": neighborhood_size,
    }

    filtered = data[data["release_year"].le(time_cutoff)]
    if album_filter:
        filtered = filtered[filtered["album_name"].isin(album_filter)]
    if type_filter:
        filtered = filtered[filtered["album_type"].isin(type_filter)]
    selected_row = data[data["track_id"].eq(selected_id)]
    if (
        not st.session_state.atlas_overview
        and not selected_row.empty
        and selected_id not in set(filtered["track_id"])
    ):
        filtered = pd.concat([filtered, selected_row], ignore_index=True)
    compare_id = st.session_state.get("compare_song_id") if forced_mode == "Compare" else None
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

    return filtered, color_by, controls


@st.fragment
def render_atlas_workspace(
    data: pd.DataFrame,
    *,
    page_title: str,
    subtitle: str,
    forced_mode: str,
) -> None:
    show_sidecar = st.session_state.get("show_atlas_sidecar", True)

    selected_song = _selected_song_row(data)
    compare_id = st.session_state.get("compare_song_id")
    compare_rows = data[data["track_id"].eq(compare_id)] if compare_id else data.iloc[0:0]

    header, status = st.columns([4, 1], gap="small")
    header.markdown(
        f'<div class="hero-kicker">{_safe(forced_mode)} MODE</div>'
        f'<div class="atlas-heading">{_safe(page_title)}</div>'
        f'<div class="panel-subtitle">{_safe(subtitle)}</div>',
        unsafe_allow_html=True,
    )
    status.markdown(
        f'<div class="map-status">{data[data["is_primary_version"]]["canonical_title"].nunique()} songs in view<br>'
        f'<span>{forced_mode} · UMAP 2D</span></div>',
        unsafe_allow_html=True,
    )
    toggle_label = "Hide panel" if show_sidecar else "Show panel"
    status.button(
        toggle_label,
        key=f"toggle_sidecar_{forced_mode.lower()}",
        width="stretch",
        on_click=lambda: st.session_state.update(show_atlas_sidecar=not st.session_state.get("show_atlas_sidecar", True)),
    )

    st.markdown(
        """
        <style>
        section.main > div.block-container {
          height: calc(100vh - 1.3rem);
          overflow: hidden;
          padding-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key=f"atlas_workspace_{forced_mode.lower()}"):
        if show_sidecar:
            controls_col, plot_col, rail_column = st.columns([1.25, 4.95, 1.55], gap="small")
        else:
            controls_col, plot_col = st.columns([1.3, 5.9], gap="small")
            rail_column = None

        with controls_col:
            with st.container(height=680, border=False, key=f"atlas_controls_{forced_mode.lower()}"):
                filtered, color_by, controls = render_atlas_controls_panel(data, forced_mode)
                st.markdown(
                    f'<div class="rail-caption">{data.canonical_title.nunique()} canonical songs · '
                    f'{len(data)} releases · {int(data.release_year.min())}–{int(data.release_year.max())}</div>',
                    unsafe_allow_html=True,
                )

        with plot_col:
            with st.container(key=f"atlas_plot_shell_{forced_mode.lower()}"):
                if filtered.empty:
                    st.warning("No songs match the current filters.")
                else:
                    focus_id = st.session_state.get("focus_song_id")
                    active_selected_id = None if st.session_state.atlas_overview else st.session_state.selected_song_id
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
                        key=f"atlas_plot_{forced_mode.lower()}",
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

        if show_sidecar and rail_column is not None:
            with rail_column:
                with st.container(height=680, border=False, key=f"atlas_sidecar_{forced_mode.lower()}"):
                    st.markdown('<div class="section-label">Current view</div>', unsafe_allow_html=True)
                    if st.session_state.atlas_overview:
                        render_overview_panel(data, "Atlas overview")
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
                        if len(journey) > 1 and controls["mode"] == "Explore":
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
                        key=f"atlas_minimap_{forced_mode.lower()}",
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
    _init_state(data)
    current_page = _current_page()
    render_app_sidebar(data, current_page)

    render_page(
        current_page,
        data,
        home_page=render_home_page,
        atlas_workspace=render_atlas_workspace,
        insights_page=render_insights_page,
        about_page=render_about_page,
        personal_page=render_personal_atlas_page,
        placeholder_page=render_placeholder_page,
    )
