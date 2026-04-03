from __future__ import annotations

import pytest

from nexus.core.graph import InferenceGraph
from nexus.core.models import Edge, SymbolRecord
from nexus.output.inference_projection import (
    FOCUS_PAYLOAD_SCHEMA,
    build_focus_graph,
    build_focus_payload,
    build_focus_reason_entries,
    build_inference_chain,
    build_json_slice,
    build_table_rows,
    format_symbol_detail,
)


def _sym(
    qn: str,
    *,
    calls: list[str] | None = None,
    called_by: list[str] | None = None,
    writes: list[str] | None = None,
    reads: list[str] | None = None,
) -> SymbolRecord:
    sid = f"symbol:{qn}"
    return SymbolRecord(
        id=sid,
        name=qn.split(".")[-1],
        kind="function",
        file="m.py",
        line_start=1,
        line_end=3,
        qualified_name=qn,
        signature=f"def {qn.split('.')[-1]}():",
        docstring=None,
        calls=list(calls or []),
        called_by=list(called_by or []),
        writes=list(writes or []),
        reads=list(reads or []),
        confidence=0.9,
        layer="core",
    )


def test_build_table_rows_counts() -> None:
    a = _sym("mod.a", calls=["b"], writes=["x"])
    rows = build_table_rows([a])
    assert len(rows) == 1
    assert rows[0]["kind"] == "function"
    assert rows[0]["name"] == "mod.a"
    assert rows[0]["file"] == "m.py"
    assert rows[0]["line_start"] == 1
    assert rows[0]["tags_short"] == ""
    assert rows[0]["writes_count"] == 1
    assert rows[0]["reads_count"] == 0
    assert rows[0]["calls_count"] == 1
    assert rows[0]["influence_score"] == 2
    assert rows[0]["tags_list"] == []
    assert rows[0]["_symbol"] is a


def test_build_table_rows_tags_truncated() -> None:
    a = _sym("mod.a")
    a.semantic_tags = ["a", "b", "c", "d"]
    rows = build_table_rows([a])
    assert rows[0]["tags_short"] == "a, b, c…"
    assert rows[0]["tags_list"] == ["a", "b", "c", "d"]


def test_format_symbol_detail_includes_confidence() -> None:
    a = _sym("mod.a", writes=["state"])
    text = format_symbol_detail(a)
    assert "mod.a" in text
    assert "confidence: 0.9" in text
    assert "writes: state" in text


def test_build_json_slice_only_internal_edges() -> None:
    a = _sym("mod.a")
    b = _sym("mod.b")
    e1 = Edge(from_id=a.id, to_id=b.id, type="calls")
    e2 = Edge(from_id=b.id, to_id=a.id, type="calls")
    g = InferenceGraph(
        repo_root="/repo",
        symbols={a.id: a, b.id: b},
        edges=[e1, e2],
    )
    out = build_json_slice(g, [a])
    assert len(out["symbols"]) == 1
    assert len(out["edges"]) == 0
    out2 = build_json_slice(g, [a, b])
    assert len(out2["edges"]) == 2


def test_inference_graph_resolve_display_ref() -> None:
    a = _sym("mod.a")
    g = InferenceGraph(repo_root="/r", symbols={a.id: a})
    assert g.resolve_display_ref(a.id) == "mod.a"
    assert g.resolve_display_ref("mod.a") == "mod.a"
    assert g.resolve_display_ref("not_a_symbol_id") == "not_a_symbol_id"
    assert g.resolve_display_ref("") == ""


def test_inference_graph_resolve_symbol_ref() -> None:
    a = _sym("mod.a")
    g = InferenceGraph(repo_root="/r", symbols={a.id: a})
    assert g.resolve_symbol_ref(a.id) is a
    assert g.resolve_symbol_ref("mod.a") is a
    assert g.resolve_symbol_ref("missing") is None


def test_build_focus_reason_entries_order() -> None:
    a = _sym(
        "mod.a",
        called_by=["symbol:mod.z"],
        writes=["w"],
        calls=["c"],
        reads=["r"],
    )
    z = _sym("mod.z")
    g = InferenceGraph(repo_root="/r", symbols={a.id: a, z.id: z})
    entries = build_focus_reason_entries(g, a)
    assert [e["type"] for e in entries] == ["called_by", "writes", "calls", "reads"]


def test_build_focus_payload_schema_and_focus_graph() -> None:
    a = _sym("mod.a", calls=["b"])
    b = _sym("mod.b", called_by=[a.id])
    e = Edge(from_id=a.id, to_id=b.id, type="calls")
    g = InferenceGraph(
        repo_root="/repo",
        symbols={a.id: a, b.id: b},
        edges=[e],
    )
    p = build_focus_payload(g, a)
    assert p["schema"] == FOCUS_PAYLOAD_SCHEMA
    assert p["symbol"] == "mod.a"
    assert p["influence"] == len(a.calls) + len(a.writes)
    assert p["influence_breakdown"] == {
        "total": len(a.calls) + len(a.writes),
        "calls": len(a.calls),
        "writes": len(a.writes),
    }
    assert p["primary_reason"] == p["reason"][0]
    assert p["inference_chain"][0] == "mod.a"
    assert p["focus_graph"] == build_focus_graph(g, a)
    assert isinstance(p["reason"], list)
    assert "relations" in p


def test_build_inference_chain_walks_callers() -> None:
    z = _sym("mod.z")
    a = _sym("mod.a", called_by=[z.id])
    b = _sym("mod.b", called_by=[a.id], calls=["x"])
    g = InferenceGraph(
        repo_root="/r",
        symbols={z.id: z, a.id: a, b.id: b},
        edges=[],
    )
    ch = build_inference_chain(g, b, include_first_call=True)
    assert ch == ["mod.z", "mod.a", "mod.b", "x"]
    ch2 = build_inference_chain(g, b, include_first_call=False)
    assert ch2 == ["mod.z", "mod.a", "mod.b"]


def test_build_focus_graph_one_hop() -> None:
    a = _sym("mod.a", calls=["b"])
    b = _sym("mod.b", called_by=["symbol:mod.a"])
    e = Edge(from_id=a.id, to_id=b.id, type="calls")
    g = InferenceGraph(
        repo_root="/r",
        symbols={a.id: a, b.id: b},
        edges=[e],
    )
    fg = build_focus_graph(g, a)
    roles = {n["id"]: n["role"] for n in fg["nodes"]}
    assert roles[a.id] == "center"
    assert roles[b.id] == "callee"
    assert any(e["from"] == a.id and e["to"] == b.id for e in fg["edges"])


def test_app_main_is_callable_when_pyqt_installed() -> None:
    pytest.importorskip("PyQt6")
    from nexus.ui.app import main

    assert callable(main)
