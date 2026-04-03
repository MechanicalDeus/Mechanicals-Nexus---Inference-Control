from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord
from nexus.scanner import attach
from nexus.output.inference_projection import build_table_rows
from nexus.output.perspective import (
    CenterKind,
    PerspectiveKind,
    PerspectiveRequest,
    render_perspective,
)


class ConsoleSession(QObject):
    """
    Single Source of Interaction: eine InferenceGraph-Instanz, gecachter Slice,
    Delegation zu Nexus — keine eigene Inferenz.
    """

    repoChanged = pyqtSignal(str)
    sliceUpdated = pyqtSignal(list)
    symbolSelected = pyqtSignal(object)
    statusMessage = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.graph: InferenceGraph | None = None
        self.current_slice: list[SymbolRecord] | None = None
        self.last_query: str | None = None
        self._last_max_symbols: int | None = None
        self._last_min_confidence: float | None = None
        self._last_error: str | None = None

    def last_error(self) -> str | None:
        return self._last_error

    def attach_repo(self, repo_path: str | Path) -> bool:
        self._last_error = None
        root = Path(repo_path).resolve()
        try:
            self.graph = attach(root)
        except Exception as e:  # noqa: BLE001 — UI-Feedback
            self.graph = None
            self.current_slice = None
            self._last_error = str(e)
            self.statusMessage.emit(self._last_error)
            return False
        self.current_slice = None
        self.last_query = None
        self.repoChanged.emit(str(root))
        self.sliceUpdated.emit([])
        self.statusMessage.emit(f"Attached: {root}")
        return True

    def query_slice(
        self,
        query: str,
        *,
        max_symbols: int | None = None,
        min_confidence: float | None = None,
    ) -> list[SymbolRecord]:
        self._last_error = None
        if not self.graph:
            self.statusMessage.emit("No repository attached.")
            self.sliceUpdated.emit([])
            return []
        self.last_query = query
        self._last_max_symbols = max_symbols
        self._last_min_confidence = min_confidence
        r = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.HEURISTIC_SLICE,
                graph=self.graph,
                query=query,
                max_symbols=max_symbols,
                min_confidence=min_confidence,
            )
        )
        if r.error:
            self.statusMessage.emit(r.error)
            self.current_slice = []
            self.sliceUpdated.emit([])
            return []
        syms = r.symbols or []
        self.current_slice = syms
        rows = build_table_rows(syms)
        self.sliceUpdated.emit(rows)
        self.statusMessage.emit(f"Slice: {len(syms)} symbol(s)")
        return syms

    def get_brief(self) -> str:
        if not self.graph:
            return ""
        q = self.last_query
        if not q or not q.strip():
            return ""
        r = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.LLM_BRIEF,
                graph=self.graph,
                query=q,
                max_symbols=self._last_max_symbols,
                min_confidence=self._last_min_confidence,
            )
        )
        return r.payload_text or ""

    def get_minimal_names(self) -> list[str] | None:
        if not self.graph:
            return None
        q = self.last_query
        if not q or not q.strip():
            return None
        r = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.AGENT_NAMES,
                graph=self.graph,
                query=q,
                max_symbols=self._last_max_symbols,
                min_confidence=self._last_min_confidence,
            )
        )
        if r.error or r.payload_text is None:
            return None
        lines = r.payload_text.splitlines()
        return lines

    def get_json_slice(self) -> dict[str, Any]:
        if not self.graph or not self.current_slice:
            return {"repo": "", "symbols": [], "edges": []}
        r = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.QUERY_SLICE_JSON,
                graph=self.graph,
                symbols_override=tuple(self.current_slice),
            )
        )
        return r.payload_json or {"repo": "", "symbols": [], "edges": []}

    def trace_mutation(self, key: str) -> dict[str, Any]:
        if not self.graph:
            return {
                "direct_writes": [],
                "indirect_writes": [],
                "transitive_writes": [],
            }
        r = render_perspective(
            PerspectiveRequest(
                kind=PerspectiveKind.MUTATION_TRACE,
                graph=self.graph,
                mutation_key=key,
            )
        )
        return r.payload_json or {
            "direct_writes": [],
            "indirect_writes": [],
            "transitive_writes": [],
        }
