from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nexus import attach


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
        help="Cap number of symbols in brief (query mode default: 15).",
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
    args = parser.parse_args(argv)

    if args.json and args.names_only:
        parser.error("--json and --names-only cannot be used together")

    root = Path(args.path)
    g = attach(root)

    if args.json:
        out = g.to_json()
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
    elif args.names_only:
        if not (args.query and args.query.strip()):
            parser.error("--names-only requires a non-empty --query / -q")
        from nexus.output.llm_format import agent_qualified_names

        names = agent_qualified_names(
            g,
            query=args.query,
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
