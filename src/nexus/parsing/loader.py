from __future__ import annotations

import os
from pathlib import Path

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
    "site-packages",
}


def discover_py_files(
    root: str | Path,
    *,
    include_tests: bool = True,
) -> list[Path]:
    root_p = Path(root).resolve()
    if not root_p.is_dir():
        return []
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_p):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIR_NAMES and not d.endswith(".egg-info")
        ]
        rel = Path(dirpath).relative_to(root_p)
        parts_lower = {p.lower() for p in rel.parts}
        if not include_tests and (
            "tests" in parts_lower or "test" in parts_lower
        ):
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(Path(dirpath) / fn)
    return sorted(out)


def path_to_module_hint(repo_root: Path, file_path: Path) -> str:
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = file_path.name
    stem = rel.with_suffix("")
    return ".".join(stem.parts)
