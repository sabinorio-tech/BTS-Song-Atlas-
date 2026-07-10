"""Semantic Atlas page entry point."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def render(data: pd.DataFrame, workspace: Callable[..., None]) -> None:
    workspace(
        data,
        page_title="The Semantic Atlas",
        subtitle=(
            "The default analytical map for exploring lyrical meaning and building journeys "
            "across the BTS universe."
        ),
        forced_mode="Explore",
    )

