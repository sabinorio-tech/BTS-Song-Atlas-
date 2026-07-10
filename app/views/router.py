"""Custom page router that preserves the existing application shell."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from views import about, atlas, compare, explorer, home, insights, personal_atlas


def render_page(
    current_page: str,
    data: pd.DataFrame,
    *,
    home_page: Callable[[pd.DataFrame], None],
    atlas_workspace: Callable[..., None],
    insights_page: Callable[[pd.DataFrame], None],
    about_page: Callable[[pd.DataFrame], None],
    personal_page: Callable[[], None],
    placeholder_page: Callable[[str, str, str], None],
) -> None:
    """Dispatch one route without introducing Streamlit's automatic navigation."""
    if current_page == "home":
        home.render(data, home_page)
    elif current_page == "atlas":
        atlas.render(data, atlas_workspace)
    elif current_page == "compare":
        compare.render(data, atlas_workspace)
    elif current_page == "insights":
        insights.render(data, insights_page)
    elif current_page == "about":
        about.render(data, about_page)
    elif current_page == "explorer":
        explorer.render(placeholder_page)
    elif current_page == "personal":
        personal_atlas.render(personal_page)

