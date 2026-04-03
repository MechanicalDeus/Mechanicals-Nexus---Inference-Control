"""
Messbare Größen für Prompt-/Kontext-Budgets (stderr, nicht stdout).

Ziel: reproduzierbare Kennzahlen zum Diffen gegen Zielbudgets — ohne LLM-API.

- ``est_tokens_chars_div_4``: grobe Heuristik (chars÷4), immer verfügbar.
- ``output_tokens_tiktoken``: wenn ``tiktoken`` installiert ist (Extra ``[metrics]``) und
  die Umgebung einen Encoder wählt — näher an GPT-4/4o/o-Serien als die Heuristik.
  Steuerung: ``NEXUS_TIKTOKEN_MODEL=gpt-4o`` oder ``NEXUS_TIKTOKEN_ENCODING=cl100k_base``.
- ``relevant_symbols_total`` / ``slice_relevant_coverage_ratio``: optional via
  ``NEXUS_METRICS_RELEVANT_UNIVERSE=1`` (zweiter Slice-Lauf mit großem Cap).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from nexus import __version__ as nexus_version
from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord
from nexus.output.llm_format import DEFAULT_QUERY_MAX_SYMBOLS, generic_query_symbol_slice
from nexus.output.perspective import PerspectiveResult


def _truthy_env(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def metrics_json_enabled(cli_flag: bool) -> bool:
    return cli_flag or _truthy_env("NEXUS_METRICS_JSON")


def estimate_tokens_chars_div_4(char_count: int) -> int:
    """Grobe untere Schätzung; kein Ersatz für einen echten Tokenizer."""
    if char_count <= 0:
        return 0
    return max(1, (char_count + 3) // 4)


def _tiktoken_encoder_bundle() -> tuple[object, str, str] | None:
    """
    Returns (encoder, label_key, label_value) or None if tiktoken missing / misconfigured.

    label_key is ``model`` or ``encoding`` for the metrics JSON ``tokenizer`` object.
    """
    try:
        import tiktoken  # type: ignore[import-untyped]
    except ImportError:
        return None
    model = os.environ.get("NEXUS_TIKTOKEN_MODEL", "").strip()
    try:
        if model:
            enc = tiktoken.encoding_for_model(model)
            return enc, "model", model
        name = os.environ.get("NEXUS_TIKTOKEN_ENCODING", "").strip() or "cl100k_base"
        enc = tiktoken.get_encoding(name)
        return enc, "encoding", name
    except Exception:
        return None


def count_output_tokens_tiktoken(text: str) -> tuple[int | None, dict[str, str] | None]:
    bundle = _tiktoken_encoder_bundle()
    if bundle is None:
        return None, None
    enc, lk, lv = bundle
    n = len(enc.encode(text))
    return n, {"backend": "tiktoken", lk: lv}


def _read_symbol_source_lines(repo_root: str, sym: SymbolRecord) -> str:
    root = Path(repo_root)
    path = root / sym.file
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if sym.line_start < 1:
        return ""
    chunk = raw[sym.line_start - 1 : sym.line_end]
    return "\n".join(chunk)


def next_open_suggestion_count(text: str) -> int:
    """Zählt Bullet-Zeilen unter der NEXT_OPEN-Sektion (wie in ``_next_open_lines``)."""
    if "NEXT_OPEN" not in text:
        return 0
    lines = text.splitlines()
    in_section = False
    count = 0
    for line in lines:
        if line.startswith("NEXT_OPEN"):
            in_section = True
            continue
        if in_section:
            stripped = line.strip()
            if stripped == "":
                break
            if stripped.startswith("- "):
                count += 1
    return count


def has_same_name_fold_marker(text: str) -> bool:
    return "SAME_NAME" in text or "same_name_also" in text


def _slice_source_max_symbols() -> int:
    raw = os.environ.get("NEXUS_METRICS_SLICE_SOURCE_MAX_SYMBOLS", "40").strip()
    try:
        n = int(raw)
        return max(1, min(n, 500))
    except ValueError:
        return 40


def _output_token_count_for_ratios(metrics: dict[str, Any]) -> int | None:
    if "output_tokens_tiktoken" in metrics:
        return int(metrics["output_tokens_tiktoken"])
    est = metrics.get("est_tokens_chars_div_4")
    if est is not None:
        return int(est)
    return None


def _append_derived_ratios(out: dict[str, Any]) -> None:
    """Kompression / Dichte / Mittelwerte — nur wenn die Basisgrößen vorhanden sind."""
    src_total = out.get("slice_source_tokens_total")
    if isinstance(src_total, int) and src_total > 0:
        out_n = _output_token_count_for_ratios(out)
        if out_n is not None and out_n > 0:
            out["compression_ratio"] = round(out_n / src_total, 6)
            out["density_source_over_output"] = round(src_total / out_n, 6)
        tok_sym = out.get("slice_source_symbols_tokenized")
        if isinstance(tok_sym, int) and tok_sym > 0:
            out["avg_source_tokens_per_symbol"] = round(src_total / tok_sym, 6)


def effective_max_symbols_for_query(
    *,
    max_symbols_arg: int | None,
    query: str | None,
    is_full_json: bool,
) -> int | None:
    if is_full_json:
        return None
    q = (query or "").strip()
    if not q:
        return None
    if max_symbols_arg is not None:
        return max_symbols_arg
    return DEFAULT_QUERY_MAX_SYMBOLS


def build_context_metrics(
    *,
    stdout_payload: str,
    output_mode: str,
    graph: InferenceGraph,
    query: str | None,
    max_symbols_arg: int | None,
    min_confidence: float | None,
    pr: PerspectiveResult | None,
    is_full_json: bool,
    include_query_slice_stats: bool,
    compact_fields: list[str] | None = None,
    agent_mode: bool = False,
) -> dict[str, Any]:
    chars = len(stdout_payload)
    lines = (
        0
        if not stdout_payload
        else stdout_payload.count("\n") + (1 if not stdout_payload.endswith("\n") else 0)
    )
    out: dict[str, Any] = {
        "version": nexus_version,
        "instrument": "nexus_context_metrics",
        "output_mode": output_mode,
        "output_chars": chars,
        "output_lines": lines,
        "est_tokens_chars_div_4": estimate_tokens_chars_div_4(chars),
        "graph_files": len(graph.files),
        "graph_symbols": len(graph.symbols),
        "graph_edges": len(graph.edges),
    }
    q = (query or "").strip()
    if q:
        out["query"] = q
    if compact_fields is not None:
        out["compact_fields"] = list(compact_fields)
    if agent_mode:
        out["agent_mode"] = True
    cap = effective_max_symbols_for_query(
        max_symbols_arg=max_symbols_arg,
        query=query,
        is_full_json=is_full_json,
    )
    if cap is not None:
        out["slice_cap_effective"] = cap
        if max_symbols_arg is not None:
            out["max_symbols_cli_explicit"] = max_symbols_arg

    symbols_in_pr = None
    heuristic_syms: list[SymbolRecord] | None = None
    slice_symbol_list: list[SymbolRecord] | None = None
    if pr is not None and pr.symbols is not None:
        symbols_in_pr = len(pr.symbols)
        out["symbols_in_result"] = symbols_in_pr
        slice_symbol_list = list(pr.symbols)

    if (
        include_query_slice_stats
        and symbols_in_pr is None
        and cap is not None
        and q
        and not is_full_json
    ):
        heuristic_syms = generic_query_symbol_slice(
            graph,
            q,
            max_symbols=max_symbols_arg,
            min_confidence=min_confidence,
        )
        out["symbols_in_heuristic_slice"] = len(heuristic_syms)
        if cap:
            out["slice_fill_ratio"] = round(len(heuristic_syms) / cap, 4) if cap > 0 else None
        slice_symbol_list = heuristic_syms

    if slice_symbol_list is not None:
        out["slice_symbols_total"] = len(slice_symbol_list)

    if (
        _truthy_env("NEXUS_METRICS_RELEVANT_UNIVERSE")
        and q
        and not is_full_json
        and cap is not None
    ):
        big = max(len(graph.symbols), 1) * 50
        rel = generic_query_symbol_slice(
            graph,
            q,
            max_symbols=big,
            min_confidence=min_confidence,
        )
        out["relevant_symbols_total"] = len(rel)
        sst = out.get("slice_symbols_total")
        if isinstance(sst, int) and len(rel) > 0:
            out["slice_relevant_coverage_ratio"] = round(sst / len(rel), 6)

    if stdout_payload:
        no = next_open_suggestion_count(stdout_payload)
        sm = has_same_name_fold_marker(stdout_payload)
        if no or sm:
            out["context_handoff"] = {
                "next_open_suggestions": no,
                "same_name_fold": sm,
            }

    tok_n, tok_meta = count_output_tokens_tiktoken(stdout_payload)
    if tok_n is not None and tok_meta is not None:
        out["output_tokens_tiktoken"] = tok_n
        out["tokenizer"] = tok_meta

    if _truthy_env("NEXUS_METRICS_SLICE_SOURCE_TOKENS"):
        slice_syms = slice_symbol_list
        bundle = _tiktoken_encoder_bundle()
        if bundle is not None and slice_syms:
            enc, lk, lv = bundle
            if "tokenizer" not in out:
                out["tokenizer"] = {"backend": "tiktoken", lk: lv}
            total_src = 0
            details: list[dict[str, Any]] = []
            cap_n = _slice_source_max_symbols()
            for s in slice_syms[:cap_n]:
                src = _read_symbol_source_lines(graph.repo_root, s)
                t = len(enc.encode(src)) if src else 0
                total_src += t
                if _truthy_env("NEXUS_METRICS_SLICE_SOURCE_DETAIL"):
                    details.append({"qualified_name": s.qualified_name, "tokens": t})
            out["slice_source_tokens_total"] = total_src
            out["slice_source_symbols_tokenized"] = min(len(slice_syms), cap_n)
            if len(slice_syms) > cap_n:
                out["slice_source_tokenization_capped"] = True
                out["slice_source_tokenization_cap"] = cap_n
            if details:
                out["slice_source_tokens_by_symbol"] = details

    _append_derived_ratios(out)

    return out


def emit_context_metrics_line(
    metrics: dict[str, Any],
    *,
    stream: TextIO | None = None,
) -> None:
    s = stream or sys.stderr
    s.write("[NEXUS_METRICS] " + json.dumps(metrics, ensure_ascii=False) + "\n")
