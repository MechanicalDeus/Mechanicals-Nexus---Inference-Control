from __future__ import annotations

import pytest

from nexus import attach
from nexus.output.inference_projection import build_json_slice, format_symbol_detail
from nexus.output.llm_format import agent_symbol_lines, generic_query_symbol_slice
from nexus.output.perspective import (
    CenterKind,
    PerspectiveAdvice,
    PerspectiveKind,
    PerspectivePayloadKind,
    PerspectiveRequest,
    render_perspective,
)


def test_heuristic_slice_matches_generic_query(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def a():\n    b()\ndef b():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.HEURISTIC_SLICE,
            graph=g,
            query="flow",
            max_symbols=5,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.SYMBOL_LIST
    assert r.symbols is not None
    direct = generic_query_symbol_slice(g, "flow", max_symbols=5)
    assert [s.id for s in r.symbols] == [s.id for s in direct]


def test_query_slice_json_with_override_matches_build_json_slice(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    syms = generic_query_symbol_slice(g, "flow", max_symbols=10)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.QUERY_SLICE_JSON,
            graph=g,
            symbols_override=tuple(syms),
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.JSON
    assert r.payload_json == build_json_slice(g, syms)


def test_llm_brief_matches_to_llm_brief(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.LLM_BRIEF,
            graph=g,
            query="flow",
            max_symbols=3,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.TEXT
    assert r.payload_text == g.to_llm_brief(query="flow", max_symbols=3)


def test_trust_detail_matches_format_symbol_detail(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    sym = next(iter(g.symbols.values()))
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.TRUST_DETAIL,
            graph=g,
            center_kind=CenterKind.SYMBOL_ID,
            center_ref=sym.id,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.TEXT
    assert r.payload_text == format_symbol_detail(sym)


def test_focus_graph_payload_kind_graph_json(tmp_path) -> None:
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    sym = next(s for s in g.symbols.values() if s.name == "a")
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.FOCUS_GRAPH,
            graph=g,
            center_kind=CenterKind.SYMBOL_QUALIFIED_NAME,
            center_ref=sym.qualified_name,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.GRAPH_JSON
    assert "nodes" in (r.payload_json or {})


def test_mutation_trace_matches_trace_mutation(tmp_path) -> None:
    (tmp_path / "s.py").write_text("def set_hp(o):\n    o.hp = 10\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.MUTATION_TRACE,
            graph=g,
            mutation_key="hp",
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.JSON
    assert r.payload_json == g.trace_mutation("hp")


def test_agent_symbol_lines_fallback_advice(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.AGENT_SYMBOL_LINES,
            graph=g,
            query="impact x",
            annotate=False,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.NONE
    assert r.advice is PerspectiveAdvice.FALLBACK_TO_LLM_BRIEF
    assert r.provenance is not None
    assert r.provenance.backend == "agent_symbol_lines"
    assert agent_symbol_lines(g, query="impact x") is None


def test_agent_names_error_on_special_query(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.AGENT_NAMES,
            graph=g,
            query="impact x",
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.ERROR


def test_query_slice_json_requires_query_or_override(tmp_path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.QUERY_SLICE_JSON,
            graph=g,
            query="",
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.ERROR
