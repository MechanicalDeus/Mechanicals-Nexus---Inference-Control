"""
Invariante Projektionen auf ``InferenceGraph`` + Slice — dieselbe Semantik für CLI und UI.

Keine zusätzliche Heuristik: nur Felder/Kanten aus dem Graph, wie in der Inference Console
und den zugehörigen Tests beschrieben.
"""

from __future__ import annotations

from typing import Any

from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord

# Kanonischer Export: UI, CLI ``nexus focus``, LLM — eine Struktur.
FOCUS_PAYLOAD_SCHEMA = "nexus.focus_payload/v1"
_MAX_FOCUS_RELATION_ITEMS = 40


def _tags_short(symbol: SymbolRecord, *, max_tags: int = 3) -> str:
    tags = list(symbol.semantic_tags)
    if not tags:
        return ""
    head = tags[:max_tags]
    suf = "…" if len(tags) > max_tags else ""
    return ", ".join(head) + suf


def build_table_rows(slice_: list[SymbolRecord]) -> list[dict[str, Any]]:
    """Tabellenzeilen für die Slice-Ansicht (Qt-frei, nur Daten)."""
    rows: list[dict[str, Any]] = []
    for s in slice_:
        rows.append(
            {
                "kind": s.kind,
                "name": s.qualified_name,
                "confidence": s.confidence,
                "layer": s.layer,
                "file": s.file,
                "line_start": s.line_start,
                "tags_short": _tags_short(s),
                "tags_list": list(s.semantic_tags[:5]),
                "writes_count": len(s.writes),
                "reads_count": len(s.reads),
                "calls_count": len(s.calls),
                "influence_score": len(s.calls) + len(s.writes),
                "_symbol": s,
            }
        )
    return rows


def format_symbol_detail(symbol: SymbolRecord) -> str:
    """Trust Engine: nur Felder aus SymbolRecord, keine erfundene Begründung."""
    lines: list[str] = [
        f"qualified_name: {symbol.qualified_name}",
        f"id: {symbol.id}",
        f"kind: {symbol.kind}",
        f"file: {symbol.file}:{symbol.line_start}-{symbol.line_end}",
        f"signature: {symbol.signature}",
        f"confidence: {symbol.confidence}",
        f"layer: {symbol.layer}",
    ]
    if symbol.docstring:
        lines.append(
            f"docstring: {symbol.docstring[:500]}{'…' if len(symbol.docstring) > 500 else ''}"
        )
    if symbol.semantic_tags:
        lines.append(f"semantic_tags: {', '.join(symbol.semantic_tags)}")
    lines.append(f"has_dynamic_call: {symbol.has_dynamic_call}")
    lines.append(f"has_local_assign: {symbol.has_local_assign}")
    if symbol.reads:
        lines.append(f"reads: {', '.join(symbol.reads[:40])}")
    if symbol.writes:
        lines.append(f"writes: {', '.join(symbol.writes[:40])}")
    if symbol.indirect_writes:
        lines.append(f"indirect_writes: {', '.join(symbol.indirect_writes[:30])}")
    if symbol.transitive_writes:
        lines.append(f"transitive_writes: {', '.join(symbol.transitive_writes[:30])}")
    if symbol.calls:
        lines.append(f"calls: {', '.join(sorted(symbol.calls)[:40])}")
    if symbol.called_by:
        lines.append(f"called_by (ids): {', '.join(symbol.called_by[:20])}")
    if symbol.constructs:
        lines.append(f"constructs: {', '.join(symbol.constructs[:20])}")
    if symbol.inherits_from:
        lines.append(f"inherits_from: {', '.join(symbol.inherits_from)}")
    if symbol.mutation_paths:
        lines.append("mutation_paths:")
        for i, path in enumerate(symbol.mutation_paths[:12]):
            score = symbol.mutation_path_scores[i] if i < len(symbol.mutation_path_scores) else None
            conf = (
                symbol.mutation_path_confidence[i]
                if i < len(symbol.mutation_path_confidence)
                else None
            )
            extra = []
            if score is not None:
                extra.append(f"score={score}")
            if conf is not None:
                extra.append(f"path_confidence={conf}")
            suf = f" ({', '.join(extra)})" if extra else ""
            lines.append(f"  {' → '.join(path)}{suf}")
    return "\n".join(lines)


def build_json_slice(
    graph: InferenceGraph,
    slice_symbols: list[SymbolRecord],
) -> dict[str, Any]:
    """
    Begrenzter Export: nur Symbole im aktuellen Slice plus Kanten, deren Enden
    beide in dieser ID-Menge liegen (kein voller Repo-Graph).
    """
    ids = {s.id for s in slice_symbols}
    symbols_out = [s.to_dict() for s in slice_symbols]
    edges_out = [e.to_dict() for e in graph.edges if e.from_id in ids and e.to_id in ids]
    return {
        "repo": graph.repo_root,
        "symbols": symbols_out,
        "edges": edges_out,
    }


def _relation_pair_entries(graph: InferenceGraph, refs: list[str]) -> list[dict[str, str]]:
    return [
        {"raw": r, "display": graph.resolve_display_ref(r)}
        for r in refs[:_MAX_FOCUS_RELATION_ITEMS]
    ]


def build_focus_reason_entries(
    graph: InferenceGraph,
    symbol: SymbolRecord,
) -> list[dict[str, str]]:
    """Eine Zeile pro Kategorie (Reihenfolge: Eintritt → Wirkung → Weiterleitung → passiv)."""
    out: list[dict[str, str]] = []
    if symbol.called_by:
        r0 = symbol.called_by[0]
        out.append(
            {"type": "called_by", "raw": r0, "target": graph.resolve_display_ref(r0)}
        )
    if symbol.writes:
        w0 = symbol.writes[0]
        out.append({"type": "writes", "raw": w0, "target": graph.resolve_display_ref(w0)})
    if symbol.calls:
        c0 = symbol.calls[0]
        out.append({"type": "calls", "raw": c0, "target": graph.resolve_display_ref(c0)})
    if symbol.reads:
        r0 = symbol.reads[0]
        out.append({"type": "reads", "raw": r0, "target": graph.resolve_display_ref(r0)})
    return out


def build_inference_chain(
    graph: InferenceGraph,
    symbol: SymbolRecord,
    *,
    max_up: int = 4,
    include_first_call: bool = True,
) -> list[str]:
    """
    Minimaler Bedeutungspfad: ``called_by[0]`` nach oben (ältester zuerst), dann Zentrum,
    optional erster ``calls``-Slot als ein Schritt „vorwärts“ (nur ``resolve_display_ref``).

    Keine neue Inferenz: nur vorhandene Graph-Felder, begrenzte Tiefe.
    """
    ancestors: list[str] = []
    cur: SymbolRecord | None = symbol
    for _ in range(max(0, max_up)):
        if cur is None or not cur.called_by:
            break
        pid = cur.called_by[0]
        parent = graph.symbols.get(pid)
        if parent is not None:
            ancestors.append(parent.qualified_name)
            cur = parent
        else:
            ancestors.append(graph.resolve_display_ref(pid))
            break
    chain = list(reversed(ancestors))
    chain.append(symbol.qualified_name)
    if include_first_call and symbol.calls:
        chain.append(graph.resolve_display_ref(symbol.calls[0]))
    return chain


def build_focus_payload(graph: InferenceGraph, symbol: SymbolRecord) -> dict[str, Any]:
    """
    Kanonische „Focus“-Struktur für UI, CLI und LLM (keine neue Inferenz, nur Projektion).

    Schema ``nexus.focus_payload/v1``: bestehende Schlüssel bleiben stabil; neue Felder
    (``primary_reason``, ``influence_breakdown``, ``inference_chain``) sind rein additiv.
    """
    reason_entries = build_focus_reason_entries(graph, symbol)
    n_calls = len(symbol.calls)
    n_writes = len(symbol.writes)
    inf_total = n_calls + n_writes
    primary = reason_entries[0] if reason_entries else None
    return {
        "schema": FOCUS_PAYLOAD_SCHEMA,
        "repo_root": graph.repo_root,
        "symbol": symbol.qualified_name,
        "symbol_id": symbol.id,
        "kind": symbol.kind,
        "layer": symbol.layer,
        "confidence": round(symbol.confidence, 4),
        "file": symbol.file,
        "line_start": symbol.line_start,
        "line_end": symbol.line_end,
        "influence": inf_total,
        "influence_breakdown": {
            "total": inf_total,
            "calls": n_calls,
            "writes": n_writes,
        },
        "tags": list(symbol.semantic_tags),
        "primary_reason": primary,
        "reason": reason_entries,
        "inference_chain": build_inference_chain(graph, symbol),
        "relations": {
            "called_by": _relation_pair_entries(graph, list(symbol.called_by)),
            "writes": _relation_pair_entries(graph, list(symbol.writes)),
            "calls": _relation_pair_entries(graph, list(symbol.calls)),
            "reads": _relation_pair_entries(graph, list(symbol.reads)),
        },
        "focus_graph": build_focus_graph(graph, symbol),
    }


def build_focus_graph(
    graph: InferenceGraph,
    center: SymbolRecord,
) -> dict[str, Any]:
    """
    Ein Hop: nur direkte caller (called_by) und direkte callees (Kanten type calls).
    Keine zusätzliche Traversierung — keine neue Semantik.
    """
    caller_ids = list(center.called_by)
    callee_ids = [e.to_id for e in graph.edges if e.type == "calls" and e.from_id == center.id]

    seen: set[str] = {center.id}
    nodes: list[dict[str, str]] = [
        {"id": center.id, "label": center.qualified_name, "role": "center"},
    ]

    def add_node(sym_id: str, role: str) -> None:
        if sym_id in seen:
            return
        s = graph.symbols.get(sym_id)
        if not s:
            return
        seen.add(sym_id)
        nodes.append({"id": s.id, "label": s.qualified_name, "role": role})

    for cid in caller_ids:
        add_node(cid, "caller")
    for tid in callee_ids:
        add_node(tid, "callee")

    edges: list[dict[str, str]] = []
    for cid in caller_ids:
        if cid in seen:
            edges.append({"from": cid, "to": center.id})
    for tid in callee_ids:
        if tid in seen:
            edges.append({"from": center.id, "to": tid})

    return {"nodes": nodes, "edges": edges}
