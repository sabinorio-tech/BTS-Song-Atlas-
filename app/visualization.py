"""Plotly visualization for the semantic song atlas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from utils import similar_songs


PALETTE = ["#5b8cff", "#a95cff", "#42dc78", "#f4df3f", "#ff8a3d", "#ff4fa3", "#22d3ee"]


def build_personal_atlas_figure(
    data: pd.DataFrame,
    color_mode: str,
    size_by_plays: bool,
) -> go.Figure:
    """Map personal listening intensity without changing semantic coordinates."""
    figure = go.Figure()
    listened = data[data["has_listening_history"]].copy()
    unexplored = data[~data["has_listening_history"]].copy()

    if not unexplored.empty:
        figure.add_trace(
            go.Scattergl(
                x=unexplored["x"],
                y=unexplored["y"],
                mode="markers",
                name="Unexplored",
                customdata=unexplored[
                    ["track_name", "album_name", "personal_hours", "personal_plays", "mastery_level"]
                ],
                marker={"size": 5, "color": "#33235f", "opacity": .32, "line": {"width": 0}},
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                    "Hours: %{customdata[2]:.2f}<br>Plays: %{customdata[3]}<br>"
                    "Mastery: Level %{customdata[4]}<extra></extra>"
                ),
            )
        )

    if not listened.empty:
        marker_size = (
            np.clip(7 + 1.6 * np.sqrt(listened["personal_plays"].to_numpy()), 8, 32)
            if size_by_plays
            else np.full(len(listened), 8)
        )
        if color_mode == "Listening intensity":
            listened["listening_intensity"] = np.log1p(listened["personal_hours"])
            marker = {
                "size": marker_size,
                "color": listened["listening_intensity"],
                "colorscale": "Plasma",
                "opacity": .88,
                "line": {"color": "rgba(255,255,255,.25)", "width": .35},
                "colorbar": {"title": "Intensity", "thickness": 10, "len": .65},
            }
            name = "Listening intensity"
        else:
            marker = {
                "size": marker_size,
                "color": listened["cluster"].map(
                    lambda value: PALETTE[int(value) % len(PALETTE)] if value != -1 else "#555b70"
                ),
                "opacity": .84,
                "line": {"color": "rgba(255,255,255,.25)", "width": .35},
            }
            name = "Semantic clusters"
        figure.add_trace(
            go.Scattergl(
                x=listened["x"],
                y=listened["y"],
                mode="markers",
                name=name,
                customdata=listened[
                    ["track_name", "album_name", "personal_hours", "personal_plays", "mastery_level"]
                ],
                marker=marker,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                    "Hours: %{customdata[2]:.2f}<br>Plays: %{customdata[3]}<br>"
                    "Mastery: Level %{customdata[4]}<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=610,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,7,24,.5)",
        font={"color": "#ebe7f7"},
        hoverlabel={"bgcolor": "#141124", "bordercolor": "#9d5cff"},
        legend={"orientation": "h", "x": 0, "y": 1.02},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
        dragmode="pan",
    )
    return figure


def _add_weighted_edges(
    figure: go.Figure,
    center: pd.Series,
    neighbors: pd.DataFrame,
    rgb: str,
) -> None:
    """Render three strength buckets instead of one trace per connection."""
    buckets = [
        (neighbors["strength"] < .34, .7, .10),
        (neighbors["strength"].between(.34, .67, inclusive="left"), 1.2, .20),
        (neighbors["strength"] >= .67, 2.0, .36),
    ]
    for mask, width, opacity in buckets:
        subset = neighbors[mask]
        if subset.empty:
            continue
        edge_x: list[float | None] = []
        edge_y: list[float | None] = []
        for neighbor in subset.itertuples():
            edge_x.extend([center.x, neighbor.x, None])
            edge_y.extend([center.y, neighbor.y, None])
        figure.add_trace(
            go.Scattergl(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line={"color": f"rgba({rgb},{opacity})", "width": width},
                hoverinfo="skip",
                showlegend=False,
            )
        )


def _color_groups(data: pd.DataFrame, color_by: str) -> tuple[pd.Series, dict[str, str]]:
    if color_by == "Semantic Cluster":
        groups = data["cluster"].map(lambda value: "Noise" if value == -1 else f"Cluster {value}")
    elif color_by == "Release Year":
        groups = pd.cut(
            data["release_year"],
            bins=[2012, 2015, 2018, 2021, 2024, 2100],
            labels=["2013–15", "2016–18", "2019–21", "2022–24", "2025+"],
        ).astype(str)
    elif color_by == "Language":
        groups = data["language"]
    elif color_by == "Word Count":
        groups = data["word_count_group"]
    else:
        leaders = data["album_name"].value_counts().head(6).index
        groups = data["album_name"].where(data["album_name"].isin(leaders), "Other albums")

    unique = list(dict.fromkeys(groups.tolist()))
    colors = {group: PALETTE[index % len(PALETTE)] for index, group in enumerate(unique)}
    colors.update({"Noise": "#555b70", "Other albums": "#686c80"})
    return groups, colors


def _selected_row(
    data: pd.DataFrame, all_data: pd.DataFrame, selected_id: str | None
) -> pd.Series | None:
    if not selected_id:
        return None
    direct = data[data["track_id"] == selected_id]
    if not direct.empty:
        return direct.iloc[0]
    selected = all_data[all_data["track_id"] == selected_id]
    if selected.empty:
        return None
    canonical = selected.iloc[0].canonical_title
    representative = data[data["canonical_title"] == canonical]
    return representative.iloc[0] if not representative.empty else None


def build_home_preview(data: pd.DataFrame) -> go.Figure:
    """Return a decorative but truthful atlas preview for the landing page."""
    figure = go.Figure()
    primary = data[data["is_primary_version"]].copy()
    groups, colors = _color_groups(primary, "Semantic Cluster")
    preview = primary.assign(_group=groups)
    for group, subset in preview.groupby("_group", sort=False):
        figure.add_trace(
            go.Scattergl(
                x=subset["x"],
                y=subset["y"],
                mode="markers",
                marker={
                    "size": np.where(subset["cluster"].eq(-1), 3.6, 5.2),
                    "color": colors[str(group)],
                    "opacity": np.where(subset["cluster"].eq(-1), 0.24, 0.86),
                    "line": {"width": 0},
                },
                hoverinfo="skip",
                showlegend=False,
            )
        )

    x_span = float(primary["x"].max() - primary["x"].min())
    y_span = float(primary["y"].max() - primary["y"].min())
    x_pad = max(x_span * 0.09, 0.4)
    y_pad = max(y_span * 0.09, 0.4)
    x_mid = float(primary["x"].mean())
    y_mid = float(primary["y"].mean())
    for scale, opacity in ((1.18, 0.10), (1.42, 0.06), (1.72, 0.04)):
        figure.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=x_mid - x_span * scale / 2,
            x1=x_mid + x_span * scale / 2,
            y0=y_mid - y_span * scale / 3,
            y1=y_mid + y_span * scale / 3,
            line={"color": f"rgba(183,110,255,{opacity})", "width": 1},
        )

    figure.add_annotation(
        x=x_mid,
        y=y_mid,
        text="✦",
        showarrow=False,
        font={"size": 32, "color": "#d2b2ff"},
        bgcolor="rgba(128,76,255,.14)",
        bordercolor="rgba(191,153,255,.25)",
        borderwidth=1,
        borderpad=12,
    )
    figure.update_layout(
        height=330,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={
            "visible": False,
            "range": [float(primary["x"].min()) - x_pad, float(primary["x"].max()) + x_pad],
        },
        yaxis={
            "visible": False,
            "range": [float(primary["y"].min()) - y_pad, float(primary["y"].max()) + y_pad],
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        dragmode=False,
    )
    return figure


def build_atlas_figure(
    data: pd.DataFrame,
    all_data: pd.DataFrame,
    selected_id: str | None,
    color_by: str,
    controls: dict[str, bool],
    focus_id: str | None = None,
    viewport_revision: str = "atlas-v2",
    neighborhood_size: int = 10,
    compare_id: str | None = None,
    journey_ids: list[str] | None = None,
) -> go.Figure:
    """Build a stable map that makes the selected semantic neighborhood legible."""
    figure = go.Figure()
    groups, colors = _color_groups(data, color_by)
    plot_data = data.assign(_group=groups)
    selected = _selected_row(data, all_data, selected_id)

    # Native Plotly density contours add quiet depth without decorative
    # particles or any change to the semantic coordinates.
    if len(data) >= 20:
        figure.add_trace(
            go.Histogram2dContour(
                x=data["x"],
                y=data["y"],
                nbinsx=24,
                nbinsy=18,
                colorscale=[
                    [0, "rgba(20,24,58,0)"],
                    [.45, "rgba(71,45,130,.10)"],
                    [1, "rgba(165,72,205,.22)"],
                ],
                contours={"coloring": "heatmap", "showlabels": False},
                line={"width": 0},
                opacity=.55,
                hoverinfo="skip",
                showscale=False,
                showlegend=False,
            )
        )

    neighbors = (
        similar_songs(selected_id, all_data, neighborhood_size)
        if selected_id
        else pd.DataFrame(columns=["canonical_title", "similarity"])
    )
    neighbor_scores = dict(zip(neighbors["canonical_title"], neighbors["similarity"], strict=True))
    visible_neighbors = data[data["canonical_title"].isin(neighbor_scores)].copy()
    visible_neighbors["similarity"] = visible_neighbors["canonical_title"].map(neighbor_scores)
    visible_neighbors = visible_neighbors.sort_values("similarity", ascending=False)

    if not visible_neighbors.empty:
        low = float(visible_neighbors["similarity"].min())
        high = float(visible_neighbors["similarity"].max())
        scale = max(high - low, 1e-6)
        visible_neighbors["strength"] = (visible_neighbors["similarity"] - low) / scale
    else:
        visible_neighbors["strength"] = pd.Series(dtype=float)

    compare = _selected_row(data, all_data, compare_id) if compare_id else None
    compare_neighbors = (
        similar_songs(compare_id, all_data, neighborhood_size)
        if compare_id
        else pd.DataFrame(columns=["canonical_title", "similarity"])
    )
    compare_scores = dict(
        zip(compare_neighbors["canonical_title"], compare_neighbors["similarity"], strict=True)
    )
    visible_compare = data[data["canonical_title"].isin(compare_scores)].copy()
    visible_compare["similarity"] = visible_compare["canonical_title"].map(compare_scores)
    visible_compare = visible_compare.sort_values("similarity", ascending=False)
    if not visible_compare.empty:
        low = float(visible_compare["similarity"].min())
        high = float(visible_compare["similarity"].max())
        visible_compare["strength"] = (visible_compare["similarity"] - low) / max(high - low, 1e-6)
    else:
        visible_compare["strength"] = pd.Series(dtype=float)

    if journey_ids:
        journey_rows = []
        for track_id in journey_ids:
            row = _selected_row(data, all_data, track_id)
            if row is not None:
                journey_rows.append(row)
        if len(journey_rows) > 1:
            figure.add_trace(
                go.Scattergl(
                    x=[row.x for row in journey_rows],
                    y=[row.y for row in journey_rows],
                    mode="lines+markers",
                    line={"color": "rgba(84,200,255,.58)", "width": 2},
                    marker={"size": 5, "color": "#54c8ff"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    if selected is not None and not visible_neighbors.empty:
        _add_weighted_edges(figure, selected, visible_neighbors, "183,105,255")

    if compare is not None and not visible_compare.empty:
        _add_weighted_edges(figure, compare, visible_compare, "255,170,66")

    neighbor_titles = set(neighbor_scores) | set(compare_scores)
    for group, subset in plot_data.groupby("_group", sort=False):
        is_neighbor = subset["canonical_title"].isin(neighbor_titles).to_numpy()
        strength = subset["canonical_title"].map(neighbor_scores).fillna(0).to_numpy()
        if neighbor_scores:
            values = np.array(list(neighbor_scores.values()))
            strength = np.clip((strength - values.min()) / max(np.ptp(values), 1e-6), 0, 1)

        if controls["fade"] and neighbor_titles:
            opacity = np.where(is_neighbor, .52 + .40 * strength, .055)
        else:
            opacity = np.where(is_neighbor, .92, .78)

        base_sizes = (
            np.clip(4.5 + np.sqrt(subset["word_count"].to_numpy().clip(min=1)) / 3.2, 5, 12)
            if controls["density"]
            else np.full(len(subset), 5.5)
        )
        figure.add_trace(
            go.Scattergl(
                x=subset["x"],
                y=subset["y"],
                mode="markers",
                name=str(group),
                customdata=subset[["track_id", "track_name", "album_name", "release_year"]],
                marker={
                    "size": base_sizes,
                    "color": colors[str(group)],
                    "opacity": np.clip(opacity, 0, 1),
                    "line": {"color": "rgba(255,255,255,.35)", "width": .35},
                },
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "<span style='color:#aaa'>%{customdata[2]} · %{customdata[3]}</span>"
                    "<extra></extra>"
                ),
            )
        )

    # Semantic neighbors get their own vivid layer so the relationship is
    # immediately clear, regardless of the active color mode.
    if not visible_neighbors.empty:
        mode = "markers+text" if controls["labels"] else "markers"
        labels = (
            [name if index < 10 else "" for index, name in enumerate(visible_neighbors["track_name"])]
            if controls["labels"]
            else None
        )
        figure.add_trace(
            go.Scattergl(
                x=visible_neighbors["x"],
                y=visible_neighbors["y"],
                mode=mode,
                text=labels,
                textposition="top center",
                textfont={"size": 10, "color": "#f3ddff"},
                customdata=visible_neighbors[
                    ["track_id", "track_name", "album_name", "release_year", "similarity"]
                ],
                marker={
                    "size": 9 + visible_neighbors["strength"] * 10,
                    "color": visible_neighbors["similarity"],
                    "colorscale": [[0, "#7c3aed"], [1, "#f0abfc"]],
                    "opacity": .96,
                    "line": {"color": "rgba(255,255,255,.92)", "width": 1},
                },
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>%{customdata[2]}<br>"
                    "Semantic similarity · %{customdata[4]:.3f}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    if not visible_compare.empty:
        shared = visible_compare["canonical_title"].isin(set(neighbor_scores))
        compare_colors = np.where(shared, "#f9e27d", "#ff9f43")
        compare_labels = (
            [name if index < 10 else "" for index, name in enumerate(visible_compare["track_name"])]
            if controls["labels"]
            else None
        )
        figure.add_trace(
            go.Scattergl(
                x=visible_compare["x"],
                y=visible_compare["y"],
                mode="markers+text" if controls["labels"] else "markers",
                text=compare_labels,
                textposition="bottom center",
                textfont={"size": 10, "color": "#ffe5bc"},
                customdata=visible_compare[
                    ["track_id", "track_name", "album_name", "release_year", "similarity"]
                ],
                marker={
                    "size": 9 + visible_compare["strength"] * 7 + shared.astype(int) * 3,
                    "color": compare_colors,
                    "opacity": .92,
                    "line": {"color": "rgba(255,255,255,.88)", "width": 1},
                },
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>%{customdata[2]}<br>"
                    "Comparison similarity · %{customdata[4]:.3f}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    if selected is not None:
        custom = [[selected.track_id, selected.track_name, selected.album_name, selected.release_year]]
        figure.add_trace(
            go.Scattergl(
                x=[selected.x],
                y=[selected.y],
                mode="markers",
                marker={"size": 54, "color": "rgba(103,57,255,.08)", "line": {"width": 0}},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scattergl(
                x=[selected.x],
                y=[selected.y],
                mode="markers",
                marker={"size": 38, "color": "rgba(103,57,255,.22)", "line": {"width": 0}},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[selected.x],
                y=[selected.y],
                mode="markers+text",
                text=[selected.track_name],
                textposition="middle right",
                customdata=custom,
                marker={
                    "size": 24,
                    "color": "#54c8ff",
                    "line": {"color": "#ffffff", "width": 2.2},
                },
                textfont={"size": 14, "color": "white"},
                hovertemplate="<b>%{customdata[1]}</b><br>Selected song<extra></extra>",
                showlegend=False,
            )
        )

    if compare is not None:
        custom = [[compare.track_id, compare.track_name, compare.album_name, compare.release_year]]
        figure.add_trace(
            go.Scattergl(
                x=[compare.x],
                y=[compare.y],
                mode="markers",
                marker={"size": 36, "color": "rgba(255,159,67,.20)", "line": {"width": 0}},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[compare.x],
                y=[compare.y],
                mode="markers+text",
                text=[compare.track_name],
                textposition="middle right",
                customdata=custom,
                marker={"size": 19, "color": "#ff9f43", "line": {"color": "#fff", "width": 2}},
                textfont={"size": 13, "color": "#ffe5c2"},
                hovertemplate="<b>%{customdata[1]}</b><br>Compared song<extra></extra>",
                showlegend=False,
            )
        )

    x_span = float(data["x"].max() - data["x"].min())
    y_span = float(data["y"].max() - data["y"].min())
    x_padding = max(x_span * .035, .25)
    y_padding = max(y_span * .035, .25)
    xaxis: dict[str, object] = {
        "visible": False,
        "fixedrange": False,
        "range": [float(data["x"].min()) - x_padding, float(data["x"].max()) + x_padding],
        "constrain": "range",
    }
    yaxis: dict[str, object] = {
        "visible": False,
        "fixedrange": False,
        "range": [float(data["y"].min()) - y_padding, float(data["y"].max()) + y_padding],
        "scaleanchor": "x",
        "scaleratio": 1,
        "constrain": "range",
    }
    focus = _selected_row(data, all_data, focus_id) if focus_id else None
    if focus is not None:
        x_window = max(x_span * .16, 2.2)
        y_window = x_window / 1.38
        xaxis["range"] = [focus.x - x_window, focus.x + x_window]
        yaxis["range"] = [focus.y - y_window, focus.y + y_window]

    figure.update_layout(
        height=680,
        margin={"l": 5, "r": 5, "t": 5, "b": 5},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,7,21,.90)",
        font={"color": "#d9d6e6", "family": "Inter, Arial, sans-serif"},
        legend={
            "orientation": "h",
            "y": 1.018,
            "x": 0,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 9},
        },
        xaxis=xaxis,
        yaxis=yaxis,
        dragmode="pan",
        hovermode="closest",
        hoverdistance=18,
        hoverlabel={
            "bgcolor": "rgba(11,12,30,.96)",
            "bordercolor": "rgba(195,145,255,.55)",
            "font": {"color": "#f7f2ff", "size": 12, "family": "Inter, Arial, sans-serif"},
            "namelength": -1,
        },
        transition={"duration": 180, "easing": "cubic-in-out"},
        uirevision=viewport_revision,
        annotations=[
            {
                "text": (
                    "Violet = selected neighborhood · Amber = compared neighborhood · Gold = shared"
                    if compare_id and selected_id
                    else (
                        "Bright violet points are the closest semantic neighbors"
                        if selected_id
                        else "Select any point to reveal its semantic neighborhood"
                    )
                ),
                "x": .012,
                "y": .015,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 10, "color": "rgba(220,206,240,.66)"},
                "bgcolor": "rgba(8,9,25,.66)",
                "borderpad": 5,
            }
        ],
    )
    return figure


def build_minimap(
    data: pd.DataFrame, selected_id: str | None, journey_ids: list[str] | None = None
) -> go.Figure:
    """Return a lightweight overview; point selection can refocus the main atlas."""
    figure = go.Figure()
    figure.add_trace(
        go.Scattergl(
            x=data["x"],
            y=data["y"],
            mode="markers",
            customdata=data[["track_id", "track_name"]],
            marker={"size": 3, "color": "rgba(139,145,178,.40)"},
            hovertemplate="%{customdata[1]}<extra></extra>",
            showlegend=False,
        )
    )
    journey = data[data["track_id"].isin(journey_ids or [])]
    if not journey.empty:
        figure.add_trace(
            go.Scattergl(
                x=journey["x"],
                y=journey["y"],
                mode="lines+markers",
                marker={"size": 5, "color": "#54c8ff"},
                line={"width": 1, "color": "rgba(84,200,255,.6)"},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    selected = data[data["track_id"].eq(selected_id)] if selected_id else data.iloc[0:0]
    if not selected.empty:
        figure.add_trace(
            go.Scattergl(
                x=selected["x"],
                y=selected["y"],
                mode="markers",
                marker={"size": 10, "color": "#54c8ff", "line": {"color": "white", "width": 1}},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.update_layout(
        height=155,
        margin={"l": 2, "r": 2, "t": 2, "b": 2},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#080b1b",
        xaxis={"visible": False},
        yaxis={"visible": False},
        dragmode="select",
    )
    return figure
