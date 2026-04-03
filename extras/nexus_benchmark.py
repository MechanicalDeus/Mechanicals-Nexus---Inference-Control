#!/usr/bin/env python3
"""
Benchmark harness: run ``python -m nexus`` with ``--metrics-json`` over many repos × queries.

Parses ``[NEXUS_METRICS]`` lines from stderr; stdout is ignored for scoring (still captured).

Examples::

  python extras/nexus_benchmark.py --repo . --query mutation --query flow \\
    --out-json bench.json

  python extras/nexus_benchmark.py --repos-list repos.txt --queries-file queries.txt \\
    --out-csv bench.csv --max-symbols 12 --relevant-universe --slice-source

  NEXUS_TIKTOKEN_ENCODING=cl100k_base python extras/nexus_benchmark.py ...

  python extras/nexus_benchmark.py --repo ./src/mypkg --query flow \\
    --nexus-arg --agent-mode --out-json bench_agent.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _parse_metrics_stderr(stderr: str) -> dict[str, Any] | None:
    prefix = "[NEXUS_METRICS] "
    for line in stderr.splitlines():
        if line.startswith(prefix):
            try:
                return json.loads(line[len(prefix) :].strip())
            except json.JSONDecodeError:
                return None
    return None


def _read_lines(path: Path) -> list[str]:
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def run_one(
    *,
    repo: Path,
    query: str,
    max_symbols: int | None,
    extra_args: list[str],
    env_extra: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    repo = repo.resolve()
    cmd = [sys.executable, "-m", "nexus", str(repo), "-q", query, "--metrics-json"]
    if max_symbols is not None:
        cmd.extend(["--max-symbols", str(max_symbols)])
    cmd.extend(extra_args)
    env = {**os.environ, **env_extra}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "repo": str(repo),
            "query": query,
            "exit_code": -1,
            "error": "timeout",
            "metrics": None,
        }
    metrics = _parse_metrics_stderr(proc.stderr or "")
    err = None
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[:2000]
    return {
        "repo": str(repo),
        "query": query,
        "exit_code": proc.returncode,
        "error": err,
        "metrics": metrics,
    }


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {
        "repo": row["repo"],
        "query": row["query"],
        "exit_code": row["exit_code"],
    }
    if row.get("error") and row["exit_code"] != 0:
        flat["error_snippet"] = (row["error"] or "")[:500]
    m = row.get("metrics")
    if isinstance(m, dict):
        for k, v in sorted(m.items()):
            if isinstance(v, (dict, list)):
                flat[f"m_{k}"] = json.dumps(v, ensure_ascii=False)
            else:
                flat[f"m_{k}"] = v
    return flat


def main() -> int:
    p = argparse.ArgumentParser(description="Batch nexus --metrics-json benchmark runs.")
    p.add_argument("--repo", action="append", default=[], help="Repo root (repeatable).")
    p.add_argument(
        "--repos-list",
        type=Path,
        default=None,
        help="File with one repo path per line (# comments allowed).",
    )
    p.add_argument("--query", "-q", action="append", default=[], metavar="TEXT")
    p.add_argument(
        "--queries-file",
        type=Path,
        default=None,
        help="File with one -q string per line.",
    )
    p.add_argument("--max-symbols", type=int, default=None)
    p.add_argument(
        "--nexus-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra args after query (repeatable), e.g. --names-only",
    )
    p.add_argument("--out-json", type=Path, default=None)
    p.add_argument("--out-csv", type=Path, default=None)
    p.add_argument(
        "--relevant-universe",
        action="store_true",
        help="Set NEXUS_METRICS_RELEVANT_UNIVERSE=1 (extra scan cost).",
    )
    p.add_argument(
        "--slice-source",
        action="store_true",
        help="Set NEXUS_METRICS_SLICE_SOURCE_TOKENS=1 (needs tiktoken).",
    )
    p.add_argument(
        "--tiktoken-encoding",
        default=None,
        help="Set NEXUS_TIKTOKEN_ENCODING for the subprocess (e.g. cl100k_base).",
    )
    p.add_argument(
        "--tiktoken-model",
        default=None,
        help="Set NEXUS_TIKTOKEN_MODEL (overrides encoding if both set).",
    )
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args()

    repos: list[Path] = [Path(x) for x in args.repo]
    if args.repos_list is not None:
        repos.extend(Path(x) for x in _read_lines(args.repos_list))

    queries: list[str] = list(args.query)
    if args.queries_file is not None:
        queries.extend(_read_lines(args.queries_file))

    if not repos:
        p.error("Need at least one --repo or --repos-list")
    if not queries:
        p.error("Need at least one --query or --queries-file")

    env_extra: dict[str, str] = {}
    if args.relevant_universe:
        env_extra["NEXUS_METRICS_RELEVANT_UNIVERSE"] = "1"
    if args.slice_source:
        env_extra["NEXUS_METRICS_SLICE_SOURCE_TOKENS"] = "1"
    if args.tiktoken_model:
        env_extra["NEXUS_TIKTOKEN_MODEL"] = args.tiktoken_model
    elif args.tiktoken_encoding:
        env_extra["NEXUS_TIKTOKEN_ENCODING"] = args.tiktoken_encoding

    rows: list[dict[str, Any]] = []
    for repo in repos:
        if not repo.exists():
            rows.append(
                {
                    "repo": str(repo),
                    "query": "",
                    "exit_code": -2,
                    "error": "repo path does not exist",
                    "metrics": None,
                }
            )
            continue
        for query in queries:
            rows.append(
                run_one(
                    repo=repo,
                    query=query,
                    max_symbols=args.max_symbols,
                    extra_args=args.nexus_arg,
                    env_extra=env_extra,
                    timeout=args.timeout,
                )
            )

    if args.out_json:
        args.out_json.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.out_csv:
        flats = [_flatten_row(r) for r in rows]
        keys: list[str] = []
        seen: set[str] = set()
        for f in flats:
            for k in f:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        with args.out_csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(flats)

    if not args.out_json and not args.out_csv:
        sys.stdout.write(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")

    return 1 if any(r.get("exit_code", 0) != 0 for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
