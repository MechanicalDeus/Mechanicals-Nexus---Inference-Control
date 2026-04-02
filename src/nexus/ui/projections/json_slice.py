from __future__ import annotations

from typing import Any

from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord


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
    edges_out = [
        e.to_dict()
        for e in graph.edges
        if e.from_id in ids and e.to_id in ids
    ]
    return {
        "repo": graph.repo_root,
        "symbols": symbols_out,
        "edges": edges_out,
    }
