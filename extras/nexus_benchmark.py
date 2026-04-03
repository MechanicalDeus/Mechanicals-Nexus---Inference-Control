#!/usr/bin/env python3
"""
Benchmark harness: run ``python -m nexus`` with ``--metrics-json`` over many repos × queries.

Parses ``[NEXUS_METRICS]`` lines from stderr; stdout is ignored for scoring (still captured).

Optional **ROI** reporting (quality / efficiency / Nexus-side cost) via ``--out-roi-json`` and/or
``--roi-enrich`` — see ``build_roi_report_for_row`` and CLI help under "ROI options" (C_hat = normalized token cost).

Examples::

  python extras/nexus_benchmark.py --repo . --query mutation --query flow \\
    --out-json bench.json

  python extras/nexus_benchmark.py --repos-list repos.txt --queries-file queries.txt \\
    --out-csv bench.csv --max-symbols 12 --relevant-universe --slice-source

  NEXUS_TIKTOKEN_ENCODING=cl100k_base python extras/nexus_benchmark.py ...

  python extras/nexus_benchmark.py --repo ./src/mypkg --query flow \\
    --nexus-arg --agent-mode --out-json bench_agent.json

  python extras/nexus_benchmark.py --repo . --query flow --out-json bench.json \\
    --out-roi-json roi.json --roi-ground-truth-result hit --roi-iterations 1

  python extras/nexus_benchmark.py --repo . -q flow -q mutation --out-roi-json roi.json \\
    --roi-ground-truth-file truth.json

  python extras/nexus_benchmark.py --roi-compare old_roi.json new_roi.json
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

# If Nexus metrics later emit slice_avg_confidence, flag low_confidence when below this threshold.
DEFAULT_ROI_LOW_CONFIDENCE_THRESHOLD = 0.4

# --- ROI model (Q / E / C_hat) ----------------------------------------------

GROUND_TRUTH_TO_Q: dict[str, float] = {
    "hit": 1.0,
    "partial": 0.5,
    "miss": 0.0,
}

DEFAULT_ROI_WQ = 0.6
DEFAULT_ROI_WE = 0.3
DEFAULT_ROI_WC = 0.1
DEFAULT_ROI_ALPHA = 0.7
DEFAULT_ROI_TOKEN_BUDGET = 100_000


def quality_from_ground_truth(result: str | None) -> float | None:
    if result is None:
        return None
    key = result.strip().lower()
    if key not in GROUND_TRUTH_TO_Q:
        raise ValueError(f"unknown ground-truth result: {result!r} (expected hit|partial|miss)")
    return GROUND_TRUTH_TO_Q[key]


def efficiency_score(iterations: int, *, alpha: float = DEFAULT_ROI_ALPHA) -> float:
    it = max(1, int(iterations))
    return 1.0 / (1.0 + alpha * (it - 1))


def cost_hat_nexus(nexus_tokens: int | None, *, token_budget: float) -> float:
    if nexus_tokens is None or nexus_tokens <= 0:
        return 0.0
    if token_budget <= 0:
        return 0.0
    return min(1.0, float(nexus_tokens) / float(token_budget))


def roi_composite_score(
    Q: float | None,
    E: float,
    C_hat: float,
    *,
    wq: float = DEFAULT_ROI_WQ,
    we: float = DEFAULT_ROI_WE,
    wc: float = DEFAULT_ROI_WC,
) -> float | None:
    if Q is None:
        return None
    return wq * Q + we * E - wc * C_hat


def _symbols_returned(metrics: dict[str, Any] | None) -> int | None:
    if not metrics:
        return None
    for k in ("symbols_in_result", "slice_symbols_total", "symbols_in_heuristic_slice"):
        v = metrics.get(k)
        if isinstance(v, int):
            return v
    return None


def _nexus_output_tokens(metrics: dict[str, Any] | None) -> int | None:
    if not metrics:
        return None
    v = metrics.get("output_tokens_tiktoken")
    return int(v) if isinstance(v, int) else None


def _slice_avg_confidence(metrics: dict[str, Any] | None) -> float | None:
    if not metrics:
        return None
    v = metrics.get("slice_avg_confidence")
    return float(v) if isinstance(v, (int, float)) else None


def _error_types_for_row(
    row: dict[str, Any],
    *,
    low_confidence_threshold: float | None = None,
) -> list[str]:
    types: list[str] = []
    if row.get("exit_code", 0) not in (0,):
        types.append("failed_run")
    m = row.get("metrics")
    if isinstance(m, dict) and row.get("exit_code", 0) == 0:
        sym = _symbols_returned(m)
        if sym == 0:
            types.append("empty_slice")
        sac = _slice_avg_confidence(m)
        if (
            low_confidence_threshold is not None
            and sac is not None
            and sac < low_confidence_threshold
        ):
            types.append("low_confidence")
    return types


def load_roi_ground_truth_file(path: Path) -> dict[str, Any]:
    """
    Load sidecar JSON. Expected shape::

        { \"queries\": { \"<query string>\": \"hit\"|\"partial\"|\"miss\", ... },
          \"kind\": \"golden\" }

    ``kind`` is optional; defaults to ``golden`` for rows matched from ``queries``.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("ground truth file must be a JSON object")
    queries = raw.get("queries")
    if queries is None:
        raise ValueError('ground truth file must contain a "queries" object')
    if not isinstance(queries, dict):
        raise ValueError('"queries" must be an object mapping query strings to results')
    out_queries: dict[str, str] = {}
    for k, v in queries.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError("queries map must use string keys and string values")
        key = k.strip()
        val = v.strip().lower()
        if val not in GROUND_TRUTH_TO_Q:
            raise ValueError(f"unknown result for query {key!r}: {v!r}")
        out_queries[key] = val
    kind = raw.get("kind")
    if kind is not None:
        if not isinstance(kind, str):
            raise ValueError('"kind" must be a string')
        kind = kind.strip().lower()
        if kind not in ("golden", "ci", "manual", "none"):
            raise ValueError(f"unknown file-level kind: {kind!r}")
    return {"queries": out_queries, "kind": kind}


def resolve_ground_truth_for_query(
    query: str,
    *,
    gt_file: dict[str, Any] | None,
    cli_result: str | None,
    cli_kind: str,
) -> tuple[str | None, str]:
    """
    Per row: file ``queries`` exact match (after strip) -> (result, file_kind or golden);
    else CLI ``--roi-ground-truth-result`` -> (result, cli_kind with none->manual);
    else (None, cli_kind).
    """
    cli_kind_l = (cli_kind or "none").strip().lower()
    q = query.strip()
    if gt_file is not None:
        qmap: dict[str, str] = gt_file["queries"]
        if q in qmap:
            fk = gt_file.get("kind")
            row_kind = (fk if isinstance(fk, str) else None) or "golden"
            return qmap[q], row_kind.strip().lower()
    if cli_result is not None:
        res = cli_result.strip().lower()
        row_kind = cli_kind_l
        if row_kind == "none":
            row_kind = "manual"
        return res, row_kind
    return None, cli_kind_l


def build_per_row_ground_truth(
    rows: list[dict[str, Any]],
    *,
    gt_file: dict[str, Any] | None,
    cli_result: str | None,
    cli_kind: str,
) -> list[tuple[str | None, str]]:
    return [
        resolve_ground_truth_for_query(
            str(row.get("query") or ""),
            gt_file=gt_file,
            cli_result=cli_result,
            cli_kind=cli_kind,
        )
        for row in rows
    ]


def build_roi_report_for_row(
    row: dict[str, Any],
    *,
    run_id: str,
    phases: int | None = None,
    iterations: int = 1,
    ground_truth_kind: str = "none",
    ground_truth_result: str | None = None,
    wq: float = DEFAULT_ROI_WQ,
    we: float = DEFAULT_ROI_WE,
    wc: float = DEFAULT_ROI_WC,
    alpha: float = DEFAULT_ROI_ALPHA,
    token_budget: float = DEFAULT_ROI_TOKEN_BUDGET,
    low_confidence_threshold: float | None = DEFAULT_ROI_LOW_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Build one ROI record (JSON-serializable) for a single benchmark row."""
    m = row.get("metrics") if isinstance(row.get("metrics"), dict) else None
    nexus_tokens = _nexus_output_tokens(m)
    symbols_ret = _symbols_returned(m)
    sac = _slice_avg_confidence(m)

    gt_kind = (ground_truth_kind or "none").strip().lower()
    gt_result = ground_truth_result.strip().lower() if ground_truth_result else None
    if gt_kind == "none" and gt_result is not None:
        gt_kind = "manual"

    Q = quality_from_ground_truth(gt_result)
    E = efficiency_score(iterations, alpha=alpha)
    C_hat = cost_hat_nexus(nexus_tokens, token_budget=token_budget)
    r_score = roi_composite_score(Q, E, C_hat, wq=wq, we=we, wc=wc)

    err_types = _error_types_for_row(
        row, low_confidence_threshold=low_confidence_threshold
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "repo": row.get("repo"),
        "query": row.get("query"),
        "iterations": max(1, int(iterations)),
        "ground_truth": {"kind": gt_kind, "result": gt_result},
        "metrics": {
            "nexus_output_tokens": nexus_tokens,
            "symbols_returned": symbols_ret,
            "avg_confidence": sac,
        },
        "errors": {
            "present": bool(err_types),
            "tokens": None,
            "types": err_types,
        },
        "scores": {
            "Q": Q,
            "E": round(E, 6),
            "C_hat": round(C_hat, 6),
            "roi_score": round(r_score, 6) if r_score is not None else None,
            "weights": {"wq": wq, "we": we, "wc": wc, "alpha": alpha},
        },
    }
    if phases is not None:
        payload["phases"] = int(phases)
    return payload


def build_roi_document(
    rows: list[dict[str, Any]],
    per_row_ground_truth: list[tuple[str | None, str]],
    *,
    run_id_prefix: str = "nx",
    phases: int | None = None,
    iterations: int = 1,
    wq: float = DEFAULT_ROI_WQ,
    we: float = DEFAULT_ROI_WE,
    wc: float = DEFAULT_ROI_WC,
    alpha: float = DEFAULT_ROI_ALPHA,
    token_budget: float = DEFAULT_ROI_TOKEN_BUDGET,
    session_error_tokens: int | None = None,
    session_total_tokens: int | None = None,
    low_confidence_threshold: float | None = DEFAULT_ROI_LOW_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Full ROI file payload with schema version and optional session-level Cursor-style totals."""
    if len(per_row_ground_truth) != len(rows):
        raise ValueError("per_row_ground_truth length must match rows")
    runs: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        rid = f"{run_id_prefix}-{i + 1:04d}"
        gt_result, gt_kind = per_row_ground_truth[i]
        runs.append(
            build_roi_report_for_row(
                row,
                run_id=rid,
                phases=phases,
                iterations=iterations,
                ground_truth_kind=gt_kind,
                ground_truth_result=gt_result,
                wq=wq,
                we=we,
                wc=wc,
                alpha=alpha,
                token_budget=token_budget,
                low_confidence_threshold=low_confidence_threshold,
            )
        )

    err_ratio: float | None = None
    if (
        session_error_tokens is not None
        and session_total_tokens is not None
        and session_total_tokens > 0
    ):
        err_ratio = session_error_tokens / session_total_tokens

    doc: dict[str, Any] = {
        "schema_version": 1,
        "roi_weights": {
            "wq": wq,
            "we": we,
            "wc": wc,
            "alpha": alpha,
            "token_budget": token_budget,
        },
        "session": {
            "error_tokens": session_error_tokens,
            "total_tokens": session_total_tokens,
            "error_cost_ratio": round(err_ratio, 6) if err_ratio is not None else None,
        },
        "runs": runs,
    }
    return doc


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


def load_roi_runs_from_file(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Load runs from ``--out-roi-json`` envelope ``{\"runs\": [...]}`` or from a benchmark
    JSON list where each row has an embedded ``roi`` object (``--roi-enrich``).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "runs" in raw and isinstance(raw["runs"], list):
        runs = [r for r in raw["runs"] if isinstance(r, dict)]
        return runs, raw
    if isinstance(raw, list):
        runs_out: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("roi"), dict):
                runs_out.append(item["roi"])
        if runs_out:
            return runs_out, None
    raise ValueError(
        f"{path}: expected ROI envelope with 'runs' array, or benchmark JSON list with per-row "
        "'roi' (from --out-roi-json or --roi-enrich)"
    )


def _run_key(run: dict[str, Any]) -> tuple[str, str]:
    return (str(run.get("repo") or ""), str(run.get("query") or ""))


def compare_roi_run_pair(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    def num_delta(a: Any, b: Any) -> float | None:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return float(b) - float(a)
        if a is None and isinstance(b, (int, float)):
            return float(b)
        if b is None and isinstance(a, (int, float)):
            return -float(a)
        return None

    o_scores = old.get("scores") if isinstance(old.get("scores"), dict) else {}
    n_scores = new.get("scores") if isinstance(new.get("scores"), dict) else {}
    o_m = old.get("metrics") if isinstance(old.get("metrics"), dict) else {}
    n_m = new.get("metrics") if isinstance(new.get("metrics"), dict) else {}

    return {
        "roi_score": num_delta(o_scores.get("roi_score"), n_scores.get("roi_score")),
        "Q": num_delta(o_scores.get("Q"), n_scores.get("Q")),
        "E": num_delta(o_scores.get("E"), n_scores.get("E")),
        "C_hat": num_delta(o_scores.get("C_hat"), n_scores.get("C_hat")),
        "nexus_output_tokens": num_delta(
            o_m.get("nexus_output_tokens"), n_m.get("nexus_output_tokens")
        ),
        "symbols_returned": num_delta(
            o_m.get("symbols_returned"), n_m.get("symbols_returned")
        ),
    }


def build_roi_compare_document(
    old_runs: list[dict[str, Any]],
    new_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    old_map = {_run_key(r): r for r in old_runs}
    new_map = {_run_key(r): r for r in new_runs}
    keys_old = set(old_map)
    keys_new = set(new_map)
    pairs: list[dict[str, Any]] = []
    for k in sorted(keys_old & keys_new):
        o, n = old_map[k], new_map[k]
        repo, query = k
        pairs.append(
            {
                "key": {"repo": repo, "query": query},
                "old": o,
                "new": n,
                "delta": compare_roi_run_pair(o, n),
            }
        )
    only_old = [
        {"key": {"repo": a, "query": b}, "old": old_map[(a, b)]}
        for (a, b) in sorted(keys_old - keys_new)
    ]
    only_new = [
        {"key": {"repo": a, "query": b}, "new": new_map[(a, b)]}
        for (a, b) in sorted(keys_new - keys_old)
    ]
    return {
        "schema_version": 1,
        "kind": "roi_compare",
        "pairs": pairs,
        "only_old": only_old,
        "only_new": only_new,
    }


def run_roi_compare(old_path: Path, new_path: Path, *, out: Path | None) -> int:
    old_runs, _ = load_roi_runs_from_file(old_path)
    new_runs, _ = load_roi_runs_from_file(new_path)
    doc = build_roi_compare_document(old_runs, new_runs)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if out is not None:
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


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
    p.add_argument(
        "--roi-compare",
        nargs=2,
        metavar=("OLD", "NEW"),
        default=None,
        help="Compare two ROI JSON files or roi-enriched benchmark lists; no Nexus run.",
    )
    p.add_argument(
        "--roi-compare-out",
        type=Path,
        default=None,
        help="Write roi-compare JSON (default: stdout).",
    )
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

    roi = p.add_argument_group("ROI options (Q/E/C_hat composite; optional ground truth)")
    roi.add_argument(
        "--out-roi-json",
        type=Path,
        default=None,
        help="Write ROI envelope (schema_version + runs + optional session totals).",
    )
    roi.add_argument(
        "--roi-enrich",
        action="store_true",
        help="Attach a per-row 'roi' object when writing --out-json or stdout JSON.",
    )
    roi.add_argument(
        "--roi-run-id-prefix",
        default="nx",
        help="Prefix for generated run_id values (default: nx -> nx-0001, ...).",
    )
    roi.add_argument(
        "--roi-phases",
        type=int,
        default=None,
        help="Optional phase count stored in each ROI run (same for all rows).",
    )
    roi.add_argument(
        "--roi-iterations",
        type=int,
        default=1,
        help="Iteration count for efficiency E (default: 1).",
    )
    roi.add_argument(
        "--roi-ground-truth-kind",
        choices=("golden", "ci", "manual", "none"),
        default="none",
        help="Ground-truth source label (default: none).",
    )
    roi.add_argument(
        "--roi-ground-truth-result",
        choices=("hit", "partial", "miss"),
        default=None,
        help="Maps to Q: hit=1, partial=0.5, miss=0. If set with kind=none, kind becomes manual.",
    )
    roi.add_argument("--roi-wq", type=float, default=DEFAULT_ROI_WQ, help="Weight for Q (default: 0.6).")
    roi.add_argument("--roi-we", type=float, default=DEFAULT_ROI_WE, help="Weight for E (default: 0.3).")
    roi.add_argument("--roi-wc", type=float, default=DEFAULT_ROI_WC, help="Weight for C_hat (default: 0.1).")
    roi.add_argument(
        "--roi-alpha",
        type=float,
        default=DEFAULT_ROI_ALPHA,
        help="Efficiency penalty alpha for E = 1/(1+alpha*(iter-1)) (default: 0.7).",
    )
    roi.add_argument(
        "--roi-token-budget",
        type=float,
        default=float(DEFAULT_ROI_TOKEN_BUDGET),
        help="Normalize Nexus output tokens: C_hat=min(1, tokens/budget) (default: 100000).",
    )
    roi.add_argument(
        "--roi-session-error-tokens",
        type=int,
        default=None,
        help="Optional external error-token total (e.g. Cursor) for session.error_cost_ratio.",
    )
    roi.add_argument(
        "--roi-session-total-tokens",
        type=int,
        default=None,
        help="Optional session total tokens; used with --roi-session-error-tokens for ratio.",
    )
    roi.add_argument(
        "--roi-ground-truth-file",
        type=Path,
        default=None,
        help='JSON sidecar: {"queries": {"<query text>": "hit"|"partial"|"miss", ...}, optional "kind".',
    )
    roi.add_argument(
        "--roi-skip-low-confidence",
        action="store_true",
        help="Do not emit low_confidence from metrics.slice_avg_confidence (when present).",
    )
    args = p.parse_args()

    if args.roi_compare:
        return run_roi_compare(
            Path(args.roi_compare[0]).resolve(),
            Path(args.roi_compare[1]).resolve(),
            out=args.roi_compare_out,
        )

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

    gt_file: dict[str, Any] | None = None
    if args.roi_ground_truth_file is not None:
        gt_file = load_roi_ground_truth_file(args.roi_ground_truth_file.resolve())
    low_thresh: float | None = (
        None if args.roi_skip_low_confidence else DEFAULT_ROI_LOW_CONFIDENCE_THRESHOLD
    )

    if args.roi_enrich or args.out_roi_json is not None:
        per_row_gt = build_per_row_ground_truth(
            rows,
            gt_file=gt_file,
            cli_result=args.roi_ground_truth_result,
            cli_kind=args.roi_ground_truth_kind,
        )
        roi_doc = build_roi_document(
            rows,
            per_row_gt,
            run_id_prefix=args.roi_run_id_prefix,
            phases=args.roi_phases,
            iterations=args.roi_iterations,
            wq=args.roi_wq,
            we=args.roi_we,
            wc=args.roi_wc,
            alpha=args.roi_alpha,
            token_budget=args.roi_token_budget,
            session_error_tokens=args.roi_session_error_tokens,
            session_total_tokens=args.roi_session_total_tokens,
            low_confidence_threshold=low_thresh,
        )
        if args.roi_enrich:
            for i, row in enumerate(rows):
                row["roi"] = roi_doc["runs"][i]
        if args.out_roi_json is not None:
            args.out_roi_json.write_text(
                json.dumps(roi_doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
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
