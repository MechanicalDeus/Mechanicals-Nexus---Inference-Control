from __future__ import annotations

import pytest

from nexus.core.graph import InferenceGraph
from nexus.core.models import Edge, SymbolRecord
from nexus.ui.projections.focus_graph import build_focus_graph
from nexus.ui.projections.json_slice import build_json_slice
from nexus.ui.projections.slice_table import build_table_rows
from nexus.ui.projections.symbol_detail import format_symbol_detail


def _sym(
    qn: str,
    *,
    calls: list[str] | None = None,
    called_by: list[str] | None = None,
    writes: list[str] | None = None,
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
        confidence=0.9,
        layer="core",
    )


def test_build_table_rows_counts() -> None:
    a = _sym("mod.a", calls=["b"], writes=["x"])
    rows = build_table_rows([a])
    assert len(rows) == 1
    assert rows[0]["name"] == "mod.a"
    assert rows[0]["writes_count"] == 1
    assert rows[0]["calls_count"] == 1
    assert rows[0]["_symbol"] is a


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


def test_build_focus_graph_one_hop() -> None:
    a = _sym("mod.a", calls=["b"])
    b = _sym("mod.b", called_by=[f"symbol:mod.a"])
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
