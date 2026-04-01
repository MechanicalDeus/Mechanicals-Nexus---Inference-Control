from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nexus.core.graph import InferenceGraph


def graph_to_json_dict(graph: InferenceGraph) -> dict[str, Any]:
    return {
        "repo": graph.repo_root,
        "files": [f.to_dict() for f in graph.files],
        "symbols": [s.to_dict() for s in graph.symbols.values()],
        "edges": [e.to_dict() for e in graph.edges],
    }
