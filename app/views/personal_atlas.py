"""Personal Atlas page entry point."""

from __future__ import annotations

from collections.abc import Callable


def render(page: Callable[[], None]) -> None:
    page()

