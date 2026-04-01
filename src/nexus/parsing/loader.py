from __future__ import annotations

import os
from pathlib import Path

from nexus.parsing.nexus_deny import NexusDeny, dir_has_nexus_skip

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
    nexus_deny = NexusDeny(root_p)
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_p):
        current = Path(dirpath)
        if dir_has_nexus_skip(current):
            dirnames[:] = []
            continue

        rel = current.relative_to(root_p)
        rel_dir = "" if rel == Path(".") else rel.as_posix()

        pruned: list[str] = []
        for d in dirnames:
            if d in SKIP_DIR_NAMES or d.endswith(".egg-info"):
                continue
            child_rel = f"{rel_dir}/{d}" if rel_dir else d
            if nexus_deny.matches(child_rel, is_dir=True):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        parts_lower = {p.lower() for p in rel.parts if p != "."}
        if not include_tests and (
            "tests" in parts_lower or "test" in parts_lower
        ):
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            rel_file = f"{rel_dir}/{fn}" if rel_dir else fn
            if nexus_deny.matches(rel_file, is_dir=False):
                continue
            out.append(current / fn)
    return sorted(out)


def path_to_module_hint(repo_root: Path, file_path: Path) -> str:
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = file_path.name
    stem = rel.with_suffix("")
    return ".".join(stem.parts)
