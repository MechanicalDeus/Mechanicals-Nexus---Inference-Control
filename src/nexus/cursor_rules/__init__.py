"""Bundled Cursor rules (.mdc) shipped with nexus-inference."""

from __future__ import annotations

from importlib import resources
from typing import Any

# ``importlib.resources.abc.Traversable`` exists from Python 3.11 on; we support 3.10+.


def rules_root() -> Any:
    """Root of ``nexus.cursor_rules`` (``importlib.resources`` traversable / path-like)."""
    return resources.files("nexus.cursor_rules")


def iter_mdc_rules() -> list[tuple[str, Any]]:
    """Return ``(filename, child)`` for each ``*.mdc`` in the package."""
    root = rules_root()
    out: list[tuple[str, Any]] = []
    for child in root.iterdir():
        if child.is_file() and child.name.endswith(".mdc"):
            out.append((child.name, child))
    out.sort(key=lambda x: x[0])
    return out
