"""Bundled Cursor rules (.mdc) shipped with nexus-inference."""

from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable


def rules_root() -> Traversable:
    """Traversable root of ``nexus.cursor_rules`` (wheel / source tree)."""
    return resources.files("nexus.cursor_rules")


def iter_mdc_rules() -> list[tuple[str, Traversable]]:
    """Return ``(filename, traversable)`` for each ``*.mdc`` in the package."""
    root = rules_root()
    out: list[tuple[str, Traversable]] = []
    for child in root.iterdir():
        if child.is_file() and child.name.endswith(".mdc"):
            out.append((child.name, child))
    out.sort(key=lambda x: x[0])
    return out
