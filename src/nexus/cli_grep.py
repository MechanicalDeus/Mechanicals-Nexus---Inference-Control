from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from nexus import attach
from nexus.output.llm_format import (
    generic_query_symbol_slice,
    top_entry_point_symbols,
)
from nexus.output.llm_query_modes import detect_special_query_mode
from nexus.parsing.loader import discover_py_files
from nexus.parsing.nexus_ignore import NexusIgnore


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def _grep_pattern_for_name(name: str) -> str | None:
    name = name.strip()
    if len(name) < 1:
        return None
    if not (name[0].isalpha() or name[0] == "_"):
        return None
    return r"\b" + re.escape(name) + r"\b"


def _rel_or_abs(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run_rg(pattern: str, paths: list[Path], cwd: Path) -> int:
    if not paths:
        return 0
    rels = [_rel_or_abs(p, cwd) for p in paths]
    cmd = ["rg", "-n", "--color", "never", pattern, *rels]
    r = subprocess.run(cmd, cwd=str(cwd))
    return r.returncode


def _run_py_grep(pattern: str, paths: list[Path], cwd: Path) -> int:
    if not paths:
        return 0
    try:
        cre = re.compile(pattern)
    except re.error:
        return 2
    rc = 1
    for fp in paths:
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        display = _rel_or_abs(fp, cwd)
        for i, line in enumerate(text.splitlines(), 1):
            if cre.search(line):
                rc = 0
                sys.stdout.write(f"{display}:{i}:{line}\n")
    return rc


def _target_paths(
    scope: str,
    repo_root: Path,
    symbol_rel_files: set[str],
) -> list[Path]:
    if scope == "nexus-files":
        out: list[Path] = []
        for rel in sorted(symbol_rel_files):
            p = (repo_root / rel).resolve()
            if p.is_file():
                out.append(p)
        return out
    paths = discover_py_files(repo_root, include_tests=True)
    ig = NexusIgnore(repo_root)
    return [
        p
        for p in paths
        if not ig.covers_file(p.relative_to(repo_root).as_posix())
    ]


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    parser = argparse.ArgumentParser(
        prog="nexus-grep",
        description=(
            "Run a Nexus query slice, then ripgrep/Python-regex for each symbol name "
            "in the selected files (Nexus → Grep)."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root (default: .)",
    )
    parser.add_argument(
        "--query",
        "-q",
        required=True,
        metavar="TEXT",
        help="Same heuristic query as `nexus -q` (not special modes like impact / why).",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        metavar="N",
        help="Cap symbols from Nexus before grepping (default: same as nexus query mode, 15).",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Only symbols with confidence >= FLOAT.",
    )
    parser.add_argument(
        "--scope",
        choices=("nexus-files", "repo"),
        default="nexus-files",
        help=(
            "nexus-files: search only .py files that define the selected symbols; "
            "repo: all discovered .py under the root (same skips as Nexus)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print qualified names, patterns, and target paths; do not run grep.",
    )
    parser.add_argument(
        "--no-entry-candidates",
        action="store_true",
        help="Do not print the top 3 ENTRY CANDIDATE lines (heuristic entry points).",
    )
    args = parser.parse_args(argv)

    q_raw = args.query.strip()
    if not q_raw:
        parser.error("--query / -q must be non-empty")
    if detect_special_query_mode(q_raw):
        sys.stderr.write(
            "nexus-grep: special queries (impact / why / mutation chain / …) are not "
            "supported; use a plain heuristic -q string like 'runtime mutation'.\n"
        )
        return 2

    root = Path(args.path).resolve()
    g = attach(root)
    repo_root = Path(g.repo_root).resolve()

    syms = generic_query_symbol_slice(
        g,
        q_raw,
        max_symbols=args.max_symbols,
        min_confidence=args.min_confidence,
    )
    if not syms:
        sys.stderr.write("nexus-grep: no symbols in this slice.\n")
        return 1

    if not args.no_entry_candidates:
        for i, s in enumerate(top_entry_point_symbols(syms, k=3), 1):
            sys.stdout.write(f"[ENTRY CANDIDATE #{i}]\n")
            sys.stdout.write(f"{s.qualified_name}\n")
        sys.stdout.write("\n")

    symbol_files = {s.file for s in syms}
    paths = _target_paths(args.scope, repo_root, symbol_files)
    if not paths:
        sys.stderr.write("nexus-grep: no target .py files to search.\n")
        return 1

    names_ordered: list[str] = []
    seen: set[str] = set()
    for s in syms:
        if s.name not in seen:
            seen.add(s.name)
            names_ordered.append(s.name)

    if args.dry_run:
        sys.stdout.write(f"REPO: {repo_root}\n")
        sys.stdout.write(f"QUERY: {q_raw}\n")
        sys.stdout.write(f"SCOPE: {args.scope}\n")
        sys.stdout.write(f"Symbols ({len(syms)}):\n")
        for s in syms:
            sys.stdout.write(f"  {s.qualified_name}  ({s.file}:{s.line_start})\n")
        sys.stdout.write(f"Grep names ({len(names_ordered)}): {', '.join(names_ordered)}\n")
        sys.stdout.write(f"Target files ({len(paths)}).\n")
        return 0

    use_rg = shutil.which("rg") is not None
    overall_hits = False
    for name in names_ordered:
        pat = _grep_pattern_for_name(name)
        if pat is None:
            continue
        sys.stdout.write(f"\n=== {name} ===\n")
        if use_rg:
            rc = _run_rg(pat, paths, repo_root)
            if rc == 0:
                overall_hits = True
        else:
            rc = _run_py_grep(pat, paths, repo_root)
            if rc == 0:
                overall_hits = True
        if rc == 2:
            return 2

    if not overall_hits:
        sys.stderr.write("nexus-grep: no matches for any symbol name in the target set.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
