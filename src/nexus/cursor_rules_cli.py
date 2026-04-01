from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nexus.cursor_rules import iter_mdc_rules, rules_root


def _install(destination: Path, *, force: bool) -> int:
    destination = destination.resolve()
    rules_dest = destination / ".cursor" / "rules"
    rules_dest.mkdir(parents=True, exist_ok=True)

    bundled = iter_mdc_rules()
    if not bundled:
        print("error: no .mdc rules bundled in nexus.cursor_rules", file=sys.stderr)
        return 1

    exit_code = 0
    for name, traversable in bundled:
        target = rules_dest / name
        if target.exists() and not force:
            print(f"skip (exists): {target}", file=sys.stderr)
            exit_code = 1
            continue
        target.write_bytes(traversable.read_bytes())
        print(f"installed {target}")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nexus-cursor-rules",
        description=(
            "Install Nexus Cursor rules from the nexus-inference package into "
            "<project>/.cursor/rules/ (Cursor loads .mdc files from there)."
        ),
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default=Path("."),
        type=Path,
        help="Project root (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing rule files in .cursor/rules/",
    )
    parser.add_argument(
        "--path",
        action="store_true",
        help="Print filesystem path to bundled rules and exit",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_rules",
        help="List bundled .mdc filenames and exit",
    )
    args = parser.parse_args(argv)

    if args.path:
        print(str(rules_root()))
        return 0

    if args.list_rules:
        items = iter_mdc_rules()
        if not items:
            print("error: no .mdc rules bundled", file=sys.stderr)
            return 1
        for name, _ in items:
            print(name)
        return 0

    return _install(args.destination, force=args.force)
