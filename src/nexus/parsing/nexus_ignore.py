"""In-tree plaintext policy: `.nexusignore` under the scan root (no source read, stubs only)."""

from __future__ import annotations

from pathlib import Path

from nexus.parsing.path_pattern_rules import Matcher, parse_pattern_file

NEXUS_IGNORE_NAME = ".nexusignore"


class NexusIgnore:
    """
    Rules from ``<scan_root>/.nexusignore`` only.

    Matched Python files are still *listed* in the graph but **not** parsed: no AST,
    no symbols, no plaintext from disk — suitable for credentials or secret modules
    you want excluded from inference content while keeping a boundary marker.
    """

    def __init__(self, scan_root: Path) -> None:
        self.scan_root = scan_root.resolve()
        p = self.scan_root / NEXUS_IGNORE_NAME
        self._matchers: list[Matcher] = parse_pattern_file(p) if p.is_file() else []

    def matches(self, rel_posix: str, *, is_dir: bool) -> bool:
        rel = rel_posix.strip().lstrip("/")
        return any(m.matches(rel, is_dir=is_dir) for m in self._matchers)

    def covers_file(self, rel_posix: str) -> bool:
        """True if this relative file path (or a denied parent directory) is ignored."""
        rel = rel_posix.strip().lstrip("/")
        if self.matches(rel, is_dir=False):
            return True
        parts = rel.split("/")
        if len(parts) <= 1:
            return False
        for i in range(len(parts) - 1):
            prefix = "/".join(parts[: i + 1])
            if self.matches(prefix, is_dir=True):
                return True
        return False
