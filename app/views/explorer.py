"""Future 3D Explorer page entry point."""

from __future__ import annotations

from collections.abc import Callable


def render(placeholder: Callable[[str, str, str], None]) -> None:
    placeholder(
        "3D Semantic Explorer",
        "The 2D atlas remains the default analytical view.",
        (
            "This future mode will let users fly through the semantic universe while keeping "
            "the current 2D atlas as the primary map for reading patterns and relationships."
        ),
    )

