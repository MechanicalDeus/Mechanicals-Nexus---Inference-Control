from __future__ import annotations

from typing import Any

from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord


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
