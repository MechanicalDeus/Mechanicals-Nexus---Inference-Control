"""
Deterministic **opcode** CLI: run fixed Nexus (and optional benchmark) pipelines
without inventing flags in the LLM.

Each subcommand maps to a concrete ``python -m ...`` invocation. Use ``catalog --json``
for a machine-readable manifest (agents / Cursor skills).

Environment:
    NEXUS_BENCHMARK_SCRIPT — path to ``extras/nexus_benchmark.py`` when not discoverable
    (e.g. PyPI install without checkout).
    NEXUS_OPC_LOG_APPEND — if set, default path for JSONL run log (same as ``--opc-log-append``).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Any


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def _strip_remainder(rem: list[str]) -> list[str]:
    if rem and rem[0] == "--":
        return rem[1:]
    return list(rem)


def _resolve_opc_log_path(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    raw = os.environ.get("NEXUS_OPC_LOG_APPEND", "").strip()
    return Path(raw) if raw else None


def _append_opc_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _emit_opc_run_log(
    path: Path | None,
    *,
    dry_run: bool,
    opcode: str,
    exit_code: int,
    duration_ms: float,
    argv: list[str] | None,
    roi_score: float | None,
    run_id: str | None,
    query_hint: str | None,
) -> None:
    if path is None or dry_run:
        return
    rec: dict[str, Any] = {
        "schema_version": 1,
        "kind": "nexus_opc_run",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "opcode": opcode,
        "exit_code": exit_code,
        "duration_ms": round(duration_ms, 3),
    }
    if roi_score is not None:
        rec["roi"] = float(roi_score)
    if run_id:
        rec["run_id"] = str(run_id)
    if query_hint:
        rec["query"] = query_hint[:500]
    if argv is not None:
        rec["argv"] = argv
    _append_opc_jsonl(path, rec)


def _run_subprocess(
    cmd: list[str],
    *,
    dry_run: bool,
    opcode: str,
    log_path: Path | None,
    roi_score: float | None,
    run_id: str | None,
    query_hint: str | None,
) -> int:
    t0 = time.perf_counter()
    if dry_run:
        sys.stdout.write(json.dumps({"argv": cmd}, ensure_ascii=False) + "\n")
        code = 0
    else:
        proc = subprocess.run(cmd)
        code = int(proc.returncode)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    _emit_opc_run_log(
        log_path,
        dry_run=dry_run,
        opcode=opcode,
        exit_code=code,
        duration_ms=elapsed_ms,
        argv=cmd,
        roi_score=roi_score,
        run_id=run_id,
        query_hint=query_hint,
    )
    return code


def _find_benchmark_script() -> Path | None:
    import nexus as nx_pkg

    here = Path(nx_pkg.__file__).resolve().parent
    for anc in [here, *here.parents]:
        cand = anc / "extras" / "nexus_benchmark.py"
        if cand.is_file():
            return cand
    return None


def resolve_benchmark_script(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise SystemExit(f"--benchmark-script is not a file: {explicit}")
        return explicit
    env = os.environ.get("NEXUS_BENCHMARK_SCRIPT", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
        raise SystemExit(f"NEXUS_BENCHMARK_SCRIPT is not a file: {env!r}")
    found = _find_benchmark_script()
    if found is not None:
        return found
    raise SystemExit(
        "bench/compare: set NEXUS_BENCHMARK_SCRIPT to extras/nexus_benchmark.py "
        "or install from a Nexus checkout where extras/ is present."
    )


def catalog_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "program": "nexus-opc",
        "description": (
            "Stable opcodes -> fixed subprocess argv. LLM picks opcode + operands; "
            "shell does not invent nexus flags."
        ),
        "opcodes": [
            {
                "name": "map",
                "intent": "Heuristic structure slice (table path); no agent brief.",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus",
                    "{path}",
                    "--perspective",
                    "heuristic_slice",
                    "-q",
                    "{query}",
                ],
                "operands": {"path": "repo root", "query": "-q text"},
                "optional_flags": ["--max-symbols N", "--metrics-json", "+ remainder after --"],
            },
            {
                "name": "locate",
                "intent": "Agent structural entry (agent_compact + default caps).",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus",
                    "{path}",
                    "--agent-mode",
                    "-q",
                    "{query}",
                ],
                "operands": {"path": "repo root", "query": "-q text"},
                "optional_flags": ["--max-symbols N", "+ remainder after --"],
            },
            {
                "name": "explain",
                "intent": "Trust / detail for one symbol (trust_detail).",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus",
                    "{path}",
                    "--perspective",
                    "trust_detail",
                    "--center-kind",
                    "{center_kind}",
                    "--center-ref",
                    "{center_ref}",
                ],
                "operands": {
                    "path": "repo root",
                    "center_ref": "symbol id or qualified_name",
                    "center_kind": "symbol_id | symbol_qualified_name (default: symbol_qualified_name)",
                },
            },
            {
                "name": "focus",
                "intent": "Canonical focus JSON (nexus focus_payload / UI parity).",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus",
                    "focus",
                    "{path}",
                    "-s",
                    "{symbol}",
                ],
                "operands": {"path": "repo root", "symbol": "-s ref"},
            },
            {
                "name": "grep",
                "intent": "Nexus slice then ripgrep / regex (nexus-grep).",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus.cli_grep",
                    "{path}",
                    "-q",
                    "{query}",
                ],
                "operands": {"path": "repo root", "query": "-q text"},
            },
            {
                "name": "policy",
                "intent": "Policy-gated retrieval (caps + scope).",
                "argv": [
                    "{python}",
                    "-m",
                    "nexus.cli_policy",
                    "{path}",
                    "-q",
                    "{query}",
                ],
                "operands": {"path": "repo root", "query": "-q text"},
            },
            {
                "name": "bench",
                "intent": "extras/nexus_benchmark.py (batch --metrics-json runs).",
                "argv": ["{python}", "{benchmark_script}", "..."],
                "operands": {"passthrough": "all args after --"},
            },
            {
                "name": "compare",
                "intent": "ROI / run diff via nexus_benchmark --roi-compare.",
                "argv": [
                    "{python}",
                    "{benchmark_script}",
                    "--roi-compare",
                    "{old}",
                    "{new}",
                ],
                "operands": {"old": "json path", "new": "json path"},
                "optional_flags": ["--roi-compare-out PATH"],
            },
            {
                "name": "stats",
                "intent": "Aggregate --opc-log-append JSONL into per-opcode counts and avg_roi.",
                "argv": ["{python}", "-m", "nexus.cli_opc", "stats", "{logfile}"],
                "operands": {"logfile": "path to JSONL"},
            },
        ],
    }


def aggregate_opc_log_jsonl(path: Path) -> dict[str, Any]:
    """
    Read JSONL written by ``--opc-log-append``; return opcode aggregates for ROI learning.

    Output shape::

        {"schema_version": 1, "opcode_stats": {"locate": {"count", "roi_samples", "avg_roi"}, ...}}
    """
    stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "roi_sum": 0.0, "roi_n": 0.0}
    )
    if not path.is_file():
        return {"schema_version": 1, "opcode_stats": {}}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("kind") != "nexus_opc_run":
            continue
        op = str(rec.get("opcode") or "?")
        st = stats[op]
        st["count"] += 1.0
        if "roi" in rec and isinstance(rec["roi"], (int, float)):
            st["roi_sum"] += float(rec["roi"])
            st["roi_n"] += 1.0
    out_stats: dict[str, Any] = {}
    for op, st in sorted(stats.items()):
        n = int(st["count"])
        rn = int(st["roi_n"])
        avg = (st["roi_sum"] / rn) if rn else None
        out_stats[op] = {
            "count": n,
            "roi_samples": rn,
            "avg_roi": round(avg, 6) if avg is not None else None,
        }
    return {"schema_version": 1, "opcode_stats": out_stats}


def _cmd_catalog(args: argparse.Namespace) -> int:
    man = catalog_manifest()
    if args.json:
        sys.stdout.write(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
        return 0
    sys.stdout.write("nexus-opc opcodes (use: nexus-opc <opcode> -h)\n\n")
    for op in man["opcodes"]:
        sys.stdout.write(f"  {op['name']}\n    {op['intent']}\n")
    sys.stdout.write("\nMachine-readable: nexus-opc catalog --json\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)

    root = argparse.ArgumentParser(
        prog="nexus-opc",
        description=(
            "Opcode dispatcher: fixed Nexus CLI pipelines. "
            "Pass extra nexus flags after -- where supported."
        ),
    )
    root.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON {\"argv\": [...]} instead of executing.",
    )
    root.add_argument(
        "--benchmark-script",
        type=Path,
        default=None,
        help="Path to extras/nexus_benchmark.py (overrides env / discovery).",
    )
    root.add_argument(
        "--opc-log-append",
        type=Path,
        default=None,
        metavar="PATH",
        help="Append one JSON object per real run (JSONL). Or set NEXUS_OPC_LOG_APPEND.",
    )
    root.add_argument(
        "--opc-roi-score",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Optional ROI score for this run (e.g. from nexus_benchmark ROI); for analytics only.",
    )
    root.add_argument(
        "--opc-run-id",
        default=None,
        metavar="ID",
        help="Optional correlation id (session / Cursor job).",
    )
    sub = root.add_subparsers(dest="opcode", required=True)

    p_cat = sub.add_parser("catalog", help="List opcodes; --json for agents.")
    p_cat.add_argument("--json", action="store_true", help="Emit catalog_manifest JSON.")
    p_cat.set_defaults(_handler=_cmd_catalog)

    def add_remainder(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "remainder",
            nargs=argparse.REMAINDER,
            default=[],
            help="Extra args after -- forwarded to underlying nexus (optional).",
        )

    p_map = sub.add_parser("map", help="OP: heuristic_slice (structural slice).")
    p_map.add_argument("-q", "--query", required=True, metavar="TEXT")
    p_map.add_argument("path", nargs="?", default=".")
    p_map.add_argument("--max-symbols", type=int, default=None)
    p_map.add_argument("--metrics-json", action="store_true")
    add_remainder(p_map)

    p_loc = sub.add_parser("locate", help="OP: --agent-mode (agent_compact entry).")
    p_loc.add_argument("-q", "--query", required=True, metavar="TEXT")
    p_loc.add_argument("path", nargs="?", default=".")
    p_loc.add_argument("--max-symbols", type=int, default=None)
    add_remainder(p_loc)

    p_ex = sub.add_parser("explain", help="OP: trust_detail around one symbol.")
    p_ex.add_argument(
        "--center-kind",
        default="symbol_qualified_name",
        choices=("symbol_id", "symbol_qualified_name"),
    )
    p_ex.add_argument("--center-ref", required=True, metavar="REF")
    p_ex.add_argument("path", nargs="?", default=".")
    add_remainder(p_ex)

    p_fo = sub.add_parser("focus", help="OP: nexus focus (canonical JSON payload).")
    p_fo.add_argument("-s", "--symbol", required=True, metavar="REF")
    p_fo.add_argument("path", nargs="?", default=".")
    p_fo.set_defaults(remainder=[])

    p_gr = sub.add_parser("grep", help="OP: nexus.cli_grep.")
    p_gr.add_argument("-q", "--query", required=True, metavar="TEXT")
    p_gr.add_argument("path", nargs="?", default=".")
    p_gr.add_argument("--max-symbols", type=int, default=None)
    add_remainder(p_gr)

    p_po = sub.add_parser("policy", help="OP: nexus.cli_policy.")
    p_po.add_argument("-q", "--query", required=True, metavar="TEXT")
    p_po.add_argument("path", nargs="?", default=".")
    add_remainder(p_po)

    p_bn = sub.add_parser(
        "bench",
        help="OP: nexus_benchmark.py — pass through args after --.",
    )
    p_bn.add_argument(
        "bench_argv",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments for nexus_benchmark.py (typically after --).",
    )

    p_cp = sub.add_parser("compare", help="OP: --roi-compare OLD NEW.")
    p_cp.add_argument("old", type=Path)
    p_cp.add_argument("new", type=Path)
    p_cp.add_argument("--roi-compare-out", type=Path, default=None)

    p_stats = sub.add_parser(
        "stats",
        help="Aggregate JSONL from --opc-log-append (count + avg_roi per opcode).",
    )
    p_stats.add_argument("logfile", type=Path, help="JSONL path written by nexus-opc runs.")

    args = root.parse_args(argv)

    dry = args.dry_run
    py = sys.executable
    log_path = _resolve_opc_log_path(args.opc_log_append)
    roi_s = args.opc_roi_score
    run_id = args.opc_run_id

    if args.opcode == "map":
        extra = _strip_remainder(args.remainder)
        cmd = [py, "-m", "nexus", args.path, "--perspective", "heuristic_slice", "-q", args.query]
        if args.max_symbols is not None:
            cmd.extend(["--max-symbols", str(args.max_symbols)])
        if args.metrics_json:
            cmd.append("--metrics-json")
        cmd.extend(extra)
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="map",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.query,
        )

    if args.opcode == "locate":
        extra = _strip_remainder(args.remainder)
        cmd = [py, "-m", "nexus", args.path, "--agent-mode", "-q", args.query]
        if args.max_symbols is not None:
            cmd.extend(["--max-symbols", str(args.max_symbols)])
        cmd.extend(extra)
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="locate",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.query,
        )

    if args.opcode == "explain":
        extra = _strip_remainder(args.remainder)
        cmd = [
            py,
            "-m",
            "nexus",
            args.path,
            "--perspective",
            "trust_detail",
            "--center-kind",
            args.center_kind,
            "--center-ref",
            args.center_ref,
        ]
        cmd.extend(extra)
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="explain",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.center_ref,
        )

    if args.opcode == "focus":
        cmd = [py, "-m", "nexus", "focus", args.path, "-s", args.symbol]
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="focus",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.symbol,
        )

    if args.opcode == "grep":
        extra = _strip_remainder(args.remainder)
        cmd = [py, "-m", "nexus.cli_grep", args.path, "-q", args.query]
        if args.max_symbols is not None:
            cmd.extend(["--max-symbols", str(args.max_symbols)])
        cmd.extend(extra)
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="grep",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.query,
        )

    if args.opcode == "policy":
        extra = _strip_remainder(args.remainder)
        cmd = [py, "-m", "nexus.cli_policy", args.path, "-q", args.query]
        cmd.extend(extra)
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="policy",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=args.query,
        )

    if args.opcode == "bench":
        script = resolve_benchmark_script(args.benchmark_script)
        ba = list(args.bench_argv)
        if ba and ba[0] == "--":
            ba = ba[1:]
        cmd = [py, str(script), *ba]
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="bench",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=None,
        )

    if args.opcode == "compare":
        script = resolve_benchmark_script(args.benchmark_script)
        cmd = [py, str(script), "--roi-compare", str(args.old), str(args.new)]
        if args.roi_compare_out is not None:
            cmd.extend(["--roi-compare-out", str(args.roi_compare_out)])
        return _run_subprocess(
            cmd,
            dry_run=dry,
            opcode="compare",
            log_path=log_path,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=f"{args.old!s} :: {args.new!s}",
        )

    if args.opcode == "stats":
        doc = aggregate_opc_log_jsonl(args.logfile)
        sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        return 0

    if args.opcode == "catalog":
        t0 = time.perf_counter()
        code = int(args._handler(args))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        argv_syn = [py, "-m", "nexus.cli_opc", "catalog"]
        if getattr(args, "json", False):
            argv_syn.append("--json")
        _emit_opc_run_log(
            log_path,
            dry_run=dry,
            opcode="catalog",
            exit_code=code,
            duration_ms=elapsed_ms,
            argv=argv_syn,
            roi_score=roi_s,
            run_id=run_id,
            query_hint=None,
        )
        return code

    raise SystemExit(f"unknown opcode: {args.opcode!r}")


if __name__ == "__main__":
    raise SystemExit(main())
