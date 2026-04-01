from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileRecord:
    path: str
    module_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "module_hint": self.module_hint}


@dataclass
class SymbolRecord:
    id: str
    name: str
    kind: str
    file: str
    line_start: int
    line_end: int
    qualified_name: str
    signature: str
    docstring: str | None
    reads: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    indirect_writes: list[str] = field(default_factory=list)
    transitive_writes: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)
    constructs: list[str] = field(default_factory=list)
    inherits_from: list[str] = field(default_factory=list)
    semantic_tags: list[str] = field(default_factory=list)
    has_dynamic_call: bool = False
    has_local_assign: bool = False
    confidence: float = 1.0
    layer: str = "support"
    mutation_paths: list[list[str]] = field(default_factory=list)
    mutation_path_scores: list[float] = field(default_factory=list)
    mutation_path_confidence: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "qualified_name": self.qualified_name,
            "signature": self.signature,
            "docstring": self.docstring,
            "reads": list(self.reads),
            "writes": list(self.writes),
            "indirect_writes": list(self.indirect_writes),
            "transitive_writes": list(self.transitive_writes),
            "calls": list(self.calls),
            "called_by": list(self.called_by),
            "constructs": list(self.constructs),
            "inherits_from": list(self.inherits_from),
            "semantic_tags": list(self.semantic_tags),
            "has_dynamic_call": self.has_dynamic_call,
            "has_local_assign": self.has_local_assign,
            "confidence": round(self.confidence, 4),
            "layer": self.layer,
            "mutation_paths": [list(path) for path in self.mutation_paths],
            "mutation_path_scores": list(self.mutation_path_scores),
            "mutation_path_confidence": list(self.mutation_path_confidence),
        }


@dataclass
class Edge:
    from_id: str
    to_id: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_id, "to": self.to_id, "type": self.type}
