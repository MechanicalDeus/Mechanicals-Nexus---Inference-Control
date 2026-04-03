"""
Kanonischer Perspektiv-Vertrag: eine Anfrage, ein Ergebnis, Delegation an bestehende
Projektionen — keine zweite Inferenz.

Der Dispatcher :func:`render_perspective` bleibt dünn; die eigentliche Logik steckt in
``_perspective_*``-Hilfen unten.

Öffentliche Semantik (stabil wie API-Namen)
------------------------------------------
Die String-Werte von :class:`PerspectiveKind`, :class:`PerspectivePayloadKind`,
:class:`PerspectiveAdvice`, :class:`PerspectiveDriver` und :class:`CenterKind` sind
Teil des Vertrags (CLI, UI, künftige Agenten-Tools). Änderungen nur bewusst und
mit Migrationshinweis.

Epistemische Differenz (wichtig)
-------------------------------

* ``heuristic_slice``: **query-match-basierte** Symbolauswahl (Heuristik + Cap), wie die
  Slice-Tabelle der Console. Keine Spezialmodus-Verdichtung.
* ``llm_brief``: **LLM-orientierte** Ausgabe inkl. Spezialqueries (impact, why, …) über
  :meth:`~nexus.core.graph.InferenceGraph.to_llm_brief` — kann bei derselben ``query``
  **andere** Symbole und Struktur liefern als ``heuristic_slice``. Das sind zwei
  Erkenntnispfade, nicht zwei Darstellungen derselben Menge.

``focus_graph`` ist eine **zentrierte strukturelle** Perspektive (1 Hop Caller/Callee am
Symbol); sie ist **nicht** query-getrieben und verwendet keine Query-Heuristik.

Steuerfluss vs. Payload
----------------------
:class:`PerspectiveAdvice` trägt **keine** Ergebnisart, sondern Hinweise für Konsumenten
(z. B. CLI: stattdessen ``llm_brief`` ausgeben). :class:`PerspectivePayloadKind`
beschreibt nur die Art des **Primär-Payloads** (Text, JSON, Symbolliste, Fehler, oder
``none`` wenn nur ein Advice gilt).

Perspektive              | Payload-Art   | Zugrundeliegende API
------------------------|---------------|------------------------------------------
``heuristic_slice``     | symbol_list   | ``generic_query_symbol_slice``
``query_slice_json``    | json          | Slice oder ``symbols_override`` + ``build_json_slice``
``llm_brief``           | text          | ``InferenceGraph.to_llm_brief``
``agent_names``         | text          | ``InferenceGraph.agent_qualified_names``
``agent_symbol_lines``  | text / none+advice | ``agent_symbol_lines``; Spezialquery → ``advice``
``agent_compact``       | text / none+advice | :func:`~nexus.output.llm_format.agent_compact_lines`; Spezialquery → ``advice``
``trust_detail``        | text          | ``format_symbol_detail``
``focus_graph``         | graph_json    | ``build_focus_graph``
``mutation_trace``      | json          | ``InferenceGraph.trace_mutation``

**Zentrum:** :class:`CenterKind` + ``center_ref`` (Phase 1 nur Symbole; später File/Key).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from nexus.core.graph import InferenceGraph
from nexus.core.models import SymbolRecord
from nexus.output.inference_projection import (
    build_focus_graph,
    build_json_slice,
    format_symbol_detail,
)
from nexus.output.llm_format import (
    agent_compact_lines,
    agent_symbol_lines,
    generic_query_symbol_slice,
)

__all__ = [
    "CenterKind",
    "PerspectiveAdvice",
    "PerspectiveDriver",
    "PerspectiveKind",
    "PerspectivePayloadKind",
    "PerspectiveProvenance",
    "PerspectiveRequest",
    "PerspectiveResult",
    "render_perspective",
]


class PerspectiveKind(str, Enum):
    HEURISTIC_SLICE = "heuristic_slice"
    QUERY_SLICE_JSON = "query_slice_json"
    LLM_BRIEF = "llm_brief"
    AGENT_NAMES = "agent_names"
    AGENT_SYMBOL_LINES = "agent_symbol_lines"
    AGENT_COMPACT = "agent_compact"
    TRUST_DETAIL = "trust_detail"
    FOCUS_GRAPH = "focus_graph"
    MUTATION_TRACE = "mutation_trace"


class PerspectivePayloadKind(str, Enum):
    """Art des Primär-Payloads (nicht mit Steuerhinweisen vermischen)."""

    ERROR = "error"
    TEXT = "text"
    JSON = "json"
    GRAPH_JSON = "graph_json"
    SYMBOL_LIST = "symbol_list"
    NONE = "none"


class PerspectiveAdvice(str, Enum):
    """Steuerhinweis für Konsumenten, kein Ersatz für payload_kind."""

    NONE = "none"
    FALLBACK_TO_LLM_BRIEF = "fallback_to_llm_brief"


class PerspectiveDriver(str, Enum):
    """Was die Perspektive primär antreibt (für Provenance / Debugging)."""

    NONE = "none"
    QUERY = "query"
    CENTER = "center"
    MUTATION_KEY = "mutation_key"
    SYMBOLS_OVERRIDE = "symbols_override"


@dataclass(frozen=True)
class PerspectiveProvenance:
    """Knappe Herkunftsinformation — nicht zum LLM spammen, nur für Debug/Transparenz."""

    backend: str
    driver: PerspectiveDriver
    center_qualified_name: str | None = None


class CenterKind(str, Enum):
    NONE = "none"
    SYMBOL_ID = "symbol_id"
    SYMBOL_QUALIFIED_NAME = "symbol_qualified_name"


@dataclass(frozen=True)
class PerspectiveRequest:
    kind: PerspectiveKind
    graph: InferenceGraph
    query: str | None = None
    max_symbols: int | None = None
    min_confidence: float | None = None
    center_kind: CenterKind = CenterKind.NONE
    center_ref: str | None = None
    mutation_key: str | None = None
    annotate: bool = False
    #: Console „Copy JSON“: gebundener Slice ohne erneutes ``generic_query_symbol_slice``.
    symbols_override: tuple[SymbolRecord, ...] | None = None
    #: Nur ``agent_compact``: ausgewählte Ausgabefelder (``None`` = volles Set).
    agent_compact_fields: frozenset[str] | None = None


@dataclass
class PerspectiveResult:
    payload_kind: PerspectivePayloadKind
    payload_text: str | None = None
    payload_json: dict | None = None
    symbols: list[SymbolRecord] | None = None
    error: str | None = None
    advice: PerspectiveAdvice = PerspectiveAdvice.NONE
    provenance: PerspectiveProvenance | None = None


def _prov(
    backend: str,
    driver: PerspectiveDriver,
    center: SymbolRecord | None = None,
) -> PerspectiveProvenance:
    return PerspectiveProvenance(
        backend=backend,
        driver=driver,
        center_qualified_name=center.qualified_name if center else None,
    )


def _resolve_center(graph: InferenceGraph, req: PerspectiveRequest) -> SymbolRecord | None:
    if req.center_kind is CenterKind.NONE:
        return None
    ref = (req.center_ref or "").strip()
    if not ref:
        return None
    if req.center_kind is CenterKind.SYMBOL_ID:
        return graph.symbols.get(ref)
    if req.center_kind is CenterKind.SYMBOL_QUALIFIED_NAME:
        return next(
            (s for s in graph.symbols.values() if s.qualified_name == ref),
            None,
        )
    return None


def _nonempty_query(req: PerspectiveRequest) -> str | None:
    q = (req.query or "").strip()
    return q if q else None


def _err(msg: str) -> PerspectiveResult:
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.ERROR,
        error=msg,
        provenance=_prov("error", PerspectiveDriver.NONE),
    )


def _perspective_heuristic_slice(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    q = _nonempty_query(req)
    if not q:
        return _err("heuristic_slice requires non-empty query")
    syms = generic_query_symbol_slice(
        g,
        q,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
    )
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.SYMBOL_LIST,
        symbols=syms,
        provenance=_prov("generic_query_symbol_slice", PerspectiveDriver.QUERY),
    )


def _perspective_query_slice_json(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    if req.symbols_override is not None:
        syms = list(req.symbols_override)
        return PerspectiveResult(
            payload_kind=PerspectivePayloadKind.JSON,
            symbols=syms,
            payload_json=build_json_slice(g, syms),
            provenance=_prov("build_json_slice", PerspectiveDriver.SYMBOLS_OVERRIDE),
        )
    q = _nonempty_query(req)
    if not q:
        return _err("query_slice_json requires non-empty query or symbols_override")
    syms = generic_query_symbol_slice(
        g,
        q,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
    )
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.JSON,
        symbols=syms,
        payload_json=build_json_slice(g, syms),
        provenance=_prov("build_json_slice+generic_query_symbol_slice", PerspectiveDriver.QUERY),
    )


def _perspective_llm_brief(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    text = g.to_llm_brief(
        query=req.query,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
    )
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.TEXT,
        payload_text=text,
        provenance=_prov("InferenceGraph.to_llm_brief", PerspectiveDriver.QUERY),
    )


def _perspective_agent_names(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    q = _nonempty_query(req)
    if not q:
        return _err("agent_names requires non-empty query")
    names = g.agent_qualified_names(
        query=q,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
    )
    if names is None:
        return PerspectiveResult(
            payload_kind=PerspectivePayloadKind.ERROR,
            error="agent_names unavailable for this query (special mode)",
            provenance=_prov("InferenceGraph.agent_qualified_names", PerspectiveDriver.QUERY),
        )
    body = "\n".join(names)
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.TEXT,
        payload_text=body + ("\n" if names else ""),
        provenance=_prov("InferenceGraph.agent_qualified_names", PerspectiveDriver.QUERY),
    )


def _perspective_agent_symbol_lines(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    q = _nonempty_query(req)
    if not q:
        return _err("agent_symbol_lines requires non-empty query")
    lines = agent_symbol_lines(
        g,
        query=q,
        annotate=req.annotate,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
    )
    if lines is None:
        return PerspectiveResult(
            payload_kind=PerspectivePayloadKind.NONE,
            advice=PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF,
            provenance=_prov("agent_symbol_lines", PerspectiveDriver.QUERY),
        )
    body = "\n".join(lines)
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.TEXT,
        payload_text=body + ("\n" if lines else ""),
        provenance=_prov("agent_symbol_lines", PerspectiveDriver.QUERY),
    )


def _perspective_agent_compact(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    q = _nonempty_query(req)
    if not q:
        return _err("agent_compact requires non-empty query")
    lines = agent_compact_lines(
        g,
        query=q,
        max_symbols=req.max_symbols,
        min_confidence=req.min_confidence,
        fields=req.agent_compact_fields,
    )
    if lines is None:
        return PerspectiveResult(
            payload_kind=PerspectivePayloadKind.NONE,
            advice=PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF,
            provenance=_prov("agent_compact_lines", PerspectiveDriver.QUERY),
        )
    body = "\n".join(lines)
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.TEXT,
        payload_text=body + ("\n" if lines else ""),
        provenance=_prov("agent_compact_lines", PerspectiveDriver.QUERY),
    )


def _perspective_trust_detail(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    center = _resolve_center(g, req)
    if center is None:
        return _err(
            "trust_detail requires center_kind=center_ref for symbol_id or symbol_qualified_name",
        )
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.TEXT,
        payload_text=format_symbol_detail(center),
        provenance=_prov("format_symbol_detail", PerspectiveDriver.CENTER, center),
    )


def _perspective_focus_graph(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    center = _resolve_center(g, req)
    if center is None:
        return _err(
            "focus_graph requires center_kind=center_ref for symbol_id or symbol_qualified_name",
        )
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.GRAPH_JSON,
        payload_json=build_focus_graph(g, center),
        provenance=_prov("build_focus_graph", PerspectiveDriver.CENTER, center),
    )


def _perspective_mutation_trace(g: InferenceGraph, req: PerspectiveRequest) -> PerspectiveResult:
    key = (req.mutation_key or "").strip()
    if not key:
        return _err("mutation_trace requires non-empty mutation_key")
    return PerspectiveResult(
        payload_kind=PerspectivePayloadKind.JSON,
        payload_json=g.trace_mutation(key),
        provenance=_prov("InferenceGraph.trace_mutation", PerspectiveDriver.MUTATION_KEY),
    )


_DISPATCH: dict[
    PerspectiveKind,
    Callable[[InferenceGraph, PerspectiveRequest], PerspectiveResult],
] = {
    PerspectiveKind.HEURISTIC_SLICE: _perspective_heuristic_slice,
    PerspectiveKind.QUERY_SLICE_JSON: _perspective_query_slice_json,
    PerspectiveKind.LLM_BRIEF: _perspective_llm_brief,
    PerspectiveKind.AGENT_NAMES: _perspective_agent_names,
    PerspectiveKind.AGENT_SYMBOL_LINES: _perspective_agent_symbol_lines,
    PerspectiveKind.AGENT_COMPACT: _perspective_agent_compact,
    PerspectiveKind.TRUST_DETAIL: _perspective_trust_detail,
    PerspectiveKind.FOCUS_GRAPH: _perspective_focus_graph,
    PerspectiveKind.MUTATION_TRACE: _perspective_mutation_trace,
}


def render_perspective(req: PerspectiveRequest) -> PerspectiveResult:
    fn = _DISPATCH.get(req.kind)
    if fn is None:
        return _err(f"unknown perspective kind: {req.kind!r}")
    return fn(req.graph, req)
