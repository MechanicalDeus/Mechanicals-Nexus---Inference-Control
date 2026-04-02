from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nexus import attach
from nexus.control_header import (
    collect_control_config,
    control_header_enabled,
    emit_control_header,
)
from nexus import __version__ as nexus_version


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="Structural inference map for Python (symbols, calls, mutations, confidence).",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root or single .py file (default: .)",
    )
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        metavar="TEXT",
        help=(
            "Filter/sort brief. Heuristics: mutation, flow. Special: "
            "'full mutation chain', 'impact SymbolName', 'core system flow', "
            "'core mutation', 'why runtime changed'."
        ),
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Only include symbols with confidence >= FLOAT in text brief.",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        metavar="N",
        help="Cap number of symbols in brief (query mode default: 12).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full graph as JSON (ignores --query / --min-confidence).",
    )
    parser.add_argument(
        "--names-only",
        action="store_true",
        help=(
            "With -q: one qualified_name per line (minimal tokens). "
            "Falls back to full brief for special queries (impact / why / …)."
        ),
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help=(
            "When used with --names-only: emit a compact one-liner per symbol with "
            "confidence/tags/layer/file:line (slightly more tokens, fewer follow-up turns)."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("fresh", "persistent", "hybrid"),
        default="fresh",
        help=(
            "Inference strategy. fresh rebuilds the map each call (no cache). "
            "persistent/hybrid require --cache-dir and may store sensitive structure."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        metavar="PATH",
        help="Cache directory for persistent/hybrid modes (explicit opt-in).",
    )
    parser.add_argument(
        "--control-header",
        action="store_true",
        help="Emit a small [NEXUS_CONFIG] header to stderr before the answer.",
    )
    args = parser.parse_args(argv)

    if args.json and args.names_only:
        parser.error("--json and --names-only cannot be used together")
    if args.annotate and not args.names_only:
        parser.error("--annotate requires --names-only")
    if args.mode != "fresh" and not args.cache_dir:
        parser.error("--mode persistent/hybrid requires --cache-dir")

    root = Path(args.path)
    if control_header_enabled(args.control_header):
        cfg = collect_control_config(
            repo_root=(root if root.is_dir() else root.parent),
            mode=args.mode,
            include_tests=True,
            transitive_depth=12,
            cache_dir=args.cache_dir,
        )
        cfg["version"] = nexus_version
        emit_control_header(cfg)
    g = attach(root, mode=args.mode, cache_dir=args.cache_dir)

    if args.json:
        out = g.to_json()
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
    elif args.names_only:
        if not (args.query and args.query.strip()):
            parser.error("--names-only requires a non-empty --query / -q")
        from nexus.output.llm_format import agent_symbol_lines

        names = agent_symbol_lines(
            g,
            query=args.query,
            annotate=args.annotate,
            max_symbols=args.max_symbols,
            min_confidence=args.min_confidence,
        )
        if names is None:
            sys.stdout.write(
                g.to_llm_brief(
                    max_symbols=args.max_symbols,
                    query=args.query,
                    min_confidence=args.min_confidence,
                )
            )
        else:
            sys.stdout.write("\n".join(names))
            if names:
                sys.stdout.write("\n")
    else:
        sys.stdout.write(
            g.to_llm_brief(
                max_symbols=args.max_symbols,
                query=args.query,
                min_confidence=args.min_confidence,
            )
        )
    return 0
