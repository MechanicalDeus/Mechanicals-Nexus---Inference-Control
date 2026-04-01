from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from nexus.core.models import SymbolRecord
from nexus.output.confidence_brief import format_confidence_line
from nexus.output.llm_query_modes import (
    build_callers_index,
    core_runtime_query_boost,
    detect_special_query_mode,
    format_core_flow_view,
    format_core_mutation_view,
    format_impact_view,
    format_mutation_chain_row,
    format_mutation_chain_view,
    format_why_view,
)

if TYPE_CHECKING:
    from nexus.core.graph import InferenceGraph


def entry_point_heuristic_score(s: SymbolRecord) -> float:
    """
    Heuristik: hoher Score = eher öffentlicher Einstieg / Orchestrierung (Service,
    commit_*/process_*/handle_*, viele Aufrufe oder Writes). Niedrig = eher
    Initialisierung, Getter, Utils — ohne ML, nur gewichtete Regeln.
    """
    score = 0.0
    fp = s.file.replace("\\", "/").lower()
    name = s.name.lower()

    path_bonus = 0.0
    if "application" in fp:
        path_bonus += 3.5
    if "/services/" in fp or "/service/" in fp:
        path_bonus += 2.5
    if "handler" in fp:
        path_bonus += 2.0
    score += min(path_bonus, 6.0)

    if name.startswith("commit_"):
        score += 4.0
    elif name.startswith("process_"):
        score += 3.0
    elif name.startswith("handle_"):
        score += 3.0

    if name in ("main", "run"):
        score += 2.5
    if name.endswith("_entry"):
        score += 2.0

    score += min(len(s.calls), 20) * 0.35
    w = len(s.writes) + len(s.indirect_writes)
    score += min(w, 15) * 0.22
    score += min(len(s.called_by), 12) * 0.18

    if s.kind in ("function", "method"):
        score += 1.0
    elif s.kind == "class":
        score -= 0.5

    if "entrypoint" in s.semantic_tags:
        score += 2.0

    if name == "__init__":
        score -= 8.0
    if name.startswith(("get_", "set_", "is_", "has_")):
        score -= 2.0

    util_markers = (
        "/util/",
        "/utils/",
        "/helpers/",
        "/helper/",
        "/mock",
        "/tests/",
        "/test/",
        "_test.py",
    )
    if any(m in fp for m in util_markers):
        score -= 3.0

    span = max(0, s.line_end - s.line_start)
    if span <= 2 and not s.calls and not s.writes and not s.indirect_writes:
        score -= 2.5

    return score


def top_entry_point_symbols(symbols: list[SymbolRecord], k: int = 3) -> list[SymbolRecord]:
    """Die k Symbole mit höchstem :func:`entry_point_heuristic_score` (stabile Tie-Breaker)."""
    ranked = sorted(
        symbols,
        key=lambda s: (-entry_point_heuristic_score(s), s.qualified_name),
    )
    return ranked[:k]


def _callees_by_caller(graph: InferenceGraph) -> dict[str, list[str]]:
    m: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        if e.type == "calls":
            m[e.from_id].append(e.to_id)
    return m


def generic_query_symbol_slice(
    graph: InferenceGraph,
    q_raw: str,
    *,
    max_symbols: int | None = None,
    min_confidence: float | None = None,
) -> list[SymbolRecord]:
    """
    Heuristische Symbol-Liste wie im normalen Query-Modus (ohne Spezialansichten).
    """
    callees_by_from = _callees_by_caller(graph)
    q = q_raw.lower().strip()
    default_cap = 15
    cap = max_symbols if max_symbols is not None else default_cap

    syms = list(graph.symbols.values())

    mutation_kw = any(
        k in q
        for k in (
            "mutat",
            "write",
            "change",
            "schreib",
            "ändert",
            "ändere",
            "state",
            "zustand",
            "commit",
            "resolver",
            "delta",
            "runtime",
            "chronicle",
        )
    )
    flow_kw = any(
        k in q
        for k in (
            "flow",
            "trace",
            "chain",
            "kette",
            "aufruf",
            "call graph",
            "hook",
            "pipeline",
        )
    )
    if mutation_kw:
        syms = [
            s
            for s in syms
            if s.writes or s.indirect_writes or s.transitive_writes
        ]
    elif flow_kw:
        syms = [s for s in syms if s.calls or callees_by_from.get(s.id)]

    runtime_q = any(k in q for k in ("runtime", "resolver", "commit"))
    if runtime_q:
        syms.sort(
            key=lambda s: (
                -core_runtime_query_boost(s, q),
                -entry_point_heuristic_score(s),
            )
            + _query_rank_key(s)
        )
    else:
        syms.sort(
            key=lambda s: (-entry_point_heuristic_score(s),) + _query_rank_key(s)
        )

    if min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]

    return syms[:cap]


def agent_qualified_names(
    graph: InferenceGraph,
    *,
    query: str,
    max_symbols: int | None = None,
    min_confidence: float | None = None,
) -> list[str] | None:
    """
    Eine qualified_name pro Zeile — spart Tokens. ``None`` bei Spezialqueries
    (impact / why / …), dann lieber :func:`format_graph_for_llm` nutzen.
    """
    q_raw = query.strip()
    if not q_raw:
        return None
    if detect_special_query_mode(q_raw):
        return None
    syms = generic_query_symbol_slice(
        graph,
        q_raw,
        max_symbols=max_symbols,
        min_confidence=min_confidence,
    )
    return [s.qualified_name for s in syms]


def _mutation_score(s: SymbolRecord) -> tuple[int, int, int, int]:
    return (
        len(s.writes),
        len(s.indirect_writes),
        len(s.transitive_writes),
        len(s.calls),
    )


def _query_rank_key(s: SymbolRecord) -> tuple[float, int, int, int, int]:
    return (
        -s.confidence,
        -len(s.writes),
        -len(s.indirect_writes),
        -len(s.transitive_writes),
        -len(s.calls),
    )


def _format_symbol_block(s: SymbolRecord, callees_by_from: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    lines.append(f"### {s.qualified_name} ({s.kind})")
    lines.append(format_confidence_line(s))
    lines.append(f"  layer: {s.layer}")
    lines.append(f"  file: {s.file}:{s.line_start}-{s.line_end}")
    if s.docstring:
        doc = s.docstring.strip().split("\n")[0][:200]
        lines.append(f"  doc: {doc}")
    if s.signature:
        lines.append(f"  sig: {s.signature}")
    if s.reads:
        lines.append(f"  reads: {', '.join(sorted(s.reads)[:20])}")
    if s.writes:
        lines.append(f"  writes: {', '.join(sorted(s.writes)[:20])}")
    if s.indirect_writes:
        lines.append(f"  indirect_writes: {', '.join(sorted(s.indirect_writes)[:15])}")
    if s.transitive_writes:
        lines.append(f"  transitive_writes: {', '.join(sorted(s.transitive_writes)[:15])}")
    if s.calls:
        lines.append(f"  calls: {', '.join(sorted(s.calls)[:25])}")
    kids = callees_by_from.get(s.id, [])
    if kids:
        lines.append(f"  call_targets_resolved: {', '.join(kids[:12])}")
    if s.called_by:
        lines.append(f"  called_by: {', '.join(s.called_by[:15])}")
    if s.inherits_from:
        lines.append(f"  inherits: {', '.join(s.inherits_from)}")
    if s.semantic_tags:
        lines.append(f"  tags: {', '.join(s.semantic_tags)}")
    if s.mutation_paths:
        for i, path in enumerate(s.mutation_paths[:5], 1):
            row = format_mutation_chain_row(i, path, s)
            lines.append(row.replace("  chain ", "  mutation_chain ", 1))
    lines.append("")
    return lines


def format_graph_for_llm(
    graph: InferenceGraph,
    *,
    max_symbols: int | None = None,
    query: str | None = None,
    min_confidence: float | None = None,
) -> str:
    callees_by_from = _callees_by_caller(graph)

    q_raw = query or ""
    q = q_raw.lower()
    query_mode = bool(q.strip())
    default_cap = 15
    cap = max_symbols if max_symbols is not None else (default_cap if query_mode else None)

    if query_mode:
        spec = detect_special_query_mode(q_raw)
        callers_ix = build_callers_index(graph.edges)
        eff_cap = cap if cap is not None else 25
        if spec == "impact":
            return format_impact_view(
                graph,
                q_raw,
                cap=eff_cap,
                min_confidence=min_confidence,
                callers_index=callers_ix,
            )
        if spec == "mutation_chain":
            mc_cap = cap if cap is not None else 40
            return format_mutation_chain_view(
                graph,
                q_raw,
                cap=mc_cap,
                min_confidence=min_confidence,
            )
        if spec == "core_flow":
            cf_cap = cap if cap is not None else 40
            return format_core_flow_view(
                graph,
                q_raw,
                cap=cf_cap,
                min_confidence=min_confidence,
            )
        if spec == "core_mutation":
            return format_core_mutation_view(
                graph,
                q_raw,
                cap=eff_cap,
                min_confidence=min_confidence,
            )
        if spec == "why":
            return format_why_view(
                graph,
                q_raw,
                cap=eff_cap,
                min_confidence=min_confidence,
            )

    syms = list(graph.symbols.values())

    if query_mode:
        syms = generic_query_symbol_slice(
            graph,
            q_raw,
            max_symbols=cap,
            min_confidence=min_confidence,
        )
    else:
        syms.sort(key=lambda s: s.qualified_name)

    if not query_mode and min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]

    if not query_mode and cap is not None:
        syms = syms[:cap]

    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    if query_mode:
        lines.append(f"QUERY (filtered): {query.strip()}")
    if min_confidence is not None:
        lines.append(f"MIN_CONFIDENCE: {min_confidence:.2f}")
    lines.append(
        f"Files: {len(graph.files)}  Symbols: {len(graph.symbols)}  Edges: {len(graph.edges)}"
    )
    redacted_paths = sorted(f.path for f in graph.files if f.redacted)
    if redacted_paths:
        lines.append(
            "NEXUS_IGNORE (plaintext not mapped): " + ", ".join(redacted_paths)
        )
    lines.append(f"Showing {len(syms)} symbol(s).")
    lines.append("")

    entry = [s for s in syms if "entrypoint" in s.semantic_tags]
    mutators = [
        s
        for s in syms
        if s not in entry
        and (s.writes or s.indirect_writes or s.transitive_writes)
    ]
    helpers = [s for s in syms if s not in entry and s not in mutators]

    if query_mode and (entry or mutators or helpers):
        if entry:
            lines.append("## Entry points")
            lines.append("")
            for s in entry:
                lines.extend(_format_symbol_block(s, callees_by_from))
        if mutators:
            lines.append("## Mutation / state-touching symbols")
            lines.append("")
            for s in mutators:
                lines.extend(_format_symbol_block(s, callees_by_from))
        if helpers:
            lines.append("## Other symbols (in this slice)")
            lines.append("")
            for s in helpers:
                lines.extend(_format_symbol_block(s, callees_by_from))
    else:
        for s in syms:
            lines.extend(_format_symbol_block(s, callees_by_from))

    return "\n".join(lines).rstrip() + "\n"
