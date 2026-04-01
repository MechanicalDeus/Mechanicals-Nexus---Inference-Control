"""Hard exclusion: `.nexusdeny` outside the mapped tree (never scanned)."""

from __future__ import annotations

import os
from pathlib import Path

from nexus.parsing.path_pattern_rules import Matcher, parse_pattern_file

NEXUS_DENY_NAME = ".nexusdeny"
NEXUS_SKIP_NAME = ".nexus-skip"
_ENV_DENY_PATH = "NEXUS_DENY_PATH"


def _deny_file_paths(scan_root: Path) -> list[Path]:
    """
    Deny rule files live **outside** the mapped directory:

    - Every ``.nexusdeny`` found while walking **parents** of the scan root
      (not inside ``scan_root`` itself).
    - Optional ``NEXUS_DENY_PATH`` pointing at another file (merged).
    """
    root = scan_root.resolve()
    out: list[Path] = []
    seen: set[Path] = set()
    cur = root.parent
    while True:
        cand = (cur / NEXUS_DENY_NAME).resolve()
        if cand.is_file() and cand not in seen:
            out.append(cand)
            seen.add(cand)
        if cur == cur.parent:
            break
        cur = cur.parent

    env = os.environ.get(_ENV_DENY_PATH, "").strip()
    if env:
        ep = Path(os.path.expandvars(os.path.expanduser(env))).resolve()
        if ep.is_file() and ep not in seen:
            out.append(ep)
    return out


class NexusDeny:
    """Compiled deny rules: matched paths are omitted from discovery entirely."""

    def __init__(self, scan_root: Path) -> None:
        self.scan_root = scan_root.resolve()
        self._matchers: list[Matcher] = []
        for p in _deny_file_paths(self.scan_root):
            self._matchers.extend(parse_pattern_file(p))

    def matches(self, rel_posix: str, *, is_dir: bool) -> bool:
        rel = rel_posix.strip().lstrip("/")
        return any(m.matches(rel, is_dir=is_dir) for m in self._matchers)


def dir_has_nexus_skip(dirpath: Path) -> bool:
    return (dirpath / NEXUS_SKIP_NAME).is_file()
