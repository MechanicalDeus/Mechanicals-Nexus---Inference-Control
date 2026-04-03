from __future__ import annotations

import json
from typing import Any, Iterator

from nexus.core.models import Edge, FileRecord, SymbolRecord
from nexus.output.json_export import graph_to_json_dict
from nexus.output.llm_format import agent_qualified_names, format_graph_for_llm


class InferenceGraph:
    """In-memory inference map: symbols, files, edges."""

    def __init__(
        self,
        repo_root: str,
        files: list[FileRecord] | None = None,
        symbols: dict[str, SymbolRecord] | None = None,
        edges: list[Edge] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.files = files or []
        self.symbols: dict[str, SymbolRecord] = dict(symbols or {})
        self.edges: list[Edge] = list(edges or [])

    def get_symbol(self, symbol_id: str) -> SymbolRecord | None:
        return self.symbols.get(symbol_id)

    def symbol_by_qualified_name(self, qualified_name: str) -> SymbolRecord | None:
        qn = qualified_name.strip()
        if not qn:
            return None
        return next((s for s in self.symbols.values() if s.qualified_name == qn), None)

    def resolve_symbol_ref(self, ref: str) -> SymbolRecord | None:
        """Symbol-ID oder exakter ``qualified_name`` → Record; sonst ``None``."""
        r = ref.strip()
        if not r:
            return None
        if r in self.symbols:
            return self.symbols[r]
        return self.symbol_by_qualified_name(r)

    def resolve_display_ref(self, ref: str) -> str:
        """Kante/Slot-String: echte Symbol-ID oder ``qualified_name`` → Anzeige; sonst unverändert."""
        if not ref:
            return ref
        if ref in self.symbols:
            return self.symbols[ref].qualified_name
        if not ref.startswith("symbol:"):
            sid = f"symbol:{ref}"
            if sid in self.symbols:
                return self.symbols[sid].qualified_name
        return ref

    def find_by_name(self, name: str) -> list[SymbolRecord]:
        return [s for s in self.symbols.values() if s.name == name]

    def find_callers(self, name_or_id: str) -> list[SymbolRecord]:
        target_ids = self._resolve_name_or_id(name_or_id)
        out: list[SymbolRecord] = []
        for sid in target_ids:
            sym = self.symbols.get(sid)
            if sym:
                for caller_id in sym.called_by:
                    c = self.symbols.get(caller_id)
                    if c:
                        out.append(c)
        return out

    def find_writers(self, state_key_substring: str) -> list[SymbolRecord]:
        key = state_key_substring.lower()
        return [
            s
            for s in self.symbols.values()
            if any(key in w.lower() for w in s.writes)
            or any(key in w.lower() for w in s.indirect_writes)
            or any(key in w.lower() for w in s.transitive_writes)
        ]

    def trace_mutation(self, state_key_substring: str) -> dict[str, Any]:
        k = state_key_substring.lower()
        direct = [
            s.to_dict() for s in self.symbols.values() if any(k in w.lower() for w in s.writes)
        ]
        indirect = [
            s.to_dict()
            for s in self.symbols.values()
            if any(k in w.lower() for w in s.indirect_writes)
        ]
        transitive = [
            s.to_dict()
            for s in self.symbols.values()
            if any(k in w.lower() for w in s.transitive_writes)
        ]
        return {
            "direct_writes": direct,
            "indirect_writes": indirect,
            "transitive_writes": transitive,
        }

    def iter_edges(self, type_: str | None = None) -> Iterator[Edge]:
        for e in self.edges:
            if type_ is None or e.type == type_:
                yield e

    def to_json_dict(self) -> dict[str, Any]:
        return graph_to_json_dict(self)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_json_dict(), indent=indent, ensure_ascii=False)

    def to_llm_brief(
        self,
        max_symbols: int | None = None,
        *,
        query: str | None = None,
        min_confidence: float | None = None,
    ) -> str:
        return format_graph_for_llm(
            self,
            max_symbols=max_symbols,
            query=query,
            min_confidence=min_confidence,
        )

    def agent_qualified_names(
        self,
        *,
        query: str,
        max_symbols: int | None = None,
        min_confidence: float | None = None,
    ) -> list[str] | None:
        """Token-sparende Namensliste; siehe :func:`nexus.output.llm_format.agent_qualified_names`."""
        return agent_qualified_names(
            self,
            query=query,
            max_symbols=max_symbols,
            min_confidence=min_confidence,
        )

    def _resolve_name_or_id(self, name_or_id: str) -> list[str]:
        if name_or_id in self.symbols:
            return [name_or_id]
        matches = [s.id for s in self.symbols.values() if s.name == name_or_id]
        return matches
