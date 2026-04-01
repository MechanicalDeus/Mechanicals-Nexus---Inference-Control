"""Shared gitignore-style path patterns for `.nexusdeny` / `.nexusignore`."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from fnmatch import fnmatchcase
from pathlib import Path


def strip_pattern_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def segment_glob_to_regex(segment: str) -> str:
    """Glob for one path segment: * and ? do not cross '/'."""
    out: list[str] = []
    i = 0
    n = len(segment)
    while i < n:
        c = segment[i]
        if c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


def compile_path_regex(pattern: str, *, dir_only: bool) -> re.Pattern[str]:
    """Path relative to scan root; pattern may contain / and **."""
    parts = [p for p in pattern.split("/") if p != ""]
    if not parts:
        return re.compile("$^")
    chunks: list[str] = ["^"]
    for i, p in enumerate(parts):
        if p == "**":
            if i == 0:
                chunks.append("(?:.*/)?")
            elif i == len(parts) - 1:
                chunks.append("(?:/.*)?")
            else:
                chunks.append("(?:/[^/]+)*/")
        else:
            if i > 0 and parts[i - 1] != "**":
                chunks.append("/")
            chunks.append(segment_glob_to_regex(p))
    body = "".join(chunks).replace("^/", "^")
    if dir_only:
        return re.compile(f"{body}(?:/|$)")
    return re.compile(f"{body}$")


class Matcher(ABC):
    @abstractmethod
    def matches(self, rel_posix: str, *, is_dir: bool) -> bool:
        raise NotImplementedError


class BasenameMatcher(Matcher):
    """Pattern without '/' matches that basename in any subdirectory."""

    def __init__(self, pattern: str, *, dir_only: bool) -> None:
        self.pattern = pattern
        self.dir_only = dir_only

    def matches(self, rel_posix: str, *, is_dir: bool) -> bool:
        rel = rel_posix.rstrip("/")
        base = rel.rsplit("/", 1)[-1]
        if self.dir_only and not is_dir:
            return False
        if any(c in self.pattern for c in "*?["):
            return fnmatchcase(base, self.pattern)
        return base == self.pattern


class PathMatcher(Matcher):
    """Anchored path or pattern containing '/' — relative to scan root."""

    def __init__(self, rx: re.Pattern[str], *, dir_only: bool) -> None:
        self.rx = rx
        self.dir_only = dir_only

    def matches(self, rel_posix: str, *, is_dir: bool) -> bool:
        rel = rel_posix.rstrip("/")
        if self.dir_only and not is_dir:
            return False
        return self.rx.fullmatch(rel) is not None


def parse_pattern_file(path: Path) -> list[Matcher]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[Matcher] = []
    for line in raw.splitlines():
        s = strip_pattern_comment(line)
        if not s:
            continue
        anchored = s.startswith("/")
        if anchored:
            s = s[1:]
        dir_only = s.endswith("/")
        if dir_only:
            s = s[:-1]
        if not s:
            continue
        if not anchored and "/" not in s:
            out.append(BasenameMatcher(s, dir_only=dir_only))
            continue
        try:
            rx = compile_path_regex(s, dir_only=dir_only)
        except re.error:
            continue
        out.append(PathMatcher(rx, dir_only=dir_only))
    return out
