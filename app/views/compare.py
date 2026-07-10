"""Song comparison page entry point."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def render(data: pd.DataFrame, workspace: Callable[..., None]) -> None:
    workspace(
        data,
        page_title="Compare Songs & Themes",
        subtitle="Place two songs side by side and measure how their semantic neighborhoods overlap.",
        forced_mode="Compare",
    )

