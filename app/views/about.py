"""About page entry point."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def render(data: pd.DataFrame, page: Callable[[pd.DataFrame], None]) -> None:
    page(data)

