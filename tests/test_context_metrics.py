from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.output.context_metrics import (
    build_context_metrics,
    count_output_tokens_tiktoken,
    estimate_tokens_chars_div_4,
    has_same_name_fold_marker,
    metrics_json_enabled,
    next_open_suggestion_count,
)
from nexus.output.perspective import PerspectivePayloadKind, PerspectiveResult
from nexus.scanner import attach


def test_estimate_tokens_chars_div_4() -> None:
    assert estimate_tokens_chars_div_4(0) == 0
    assert estimate_tokens_chars_div_4(1) == 1
    assert estimate_tokens_chars_div_4(4) == 1
    assert estimate_tokens_chars_div_4(5) == 2


def test_next_open_suggestion_count() -> None:
    text = """NEXT_OPEN (recommended file slices):
  - a.py:1-2  (x)
  - b.py:3-4  (y)

Other:
"""
    assert next_open_suggestion_count(text) == 2
    assert next_open_suggestion_count("no section") == 0


def test_has_same_name_fold_marker() -> None:
    assert has_same_name_fold_marker("SAME_NAME") is True
    assert has_same_name_fold_marker("same_name_also foo") is True
    assert has_same_name_fold_marker("plain") is False


def test_metrics_json_enabled_flag_and_env(monkeypatch) -> None:
    assert metrics_json_enabled(False) is False
    assert metrics_json_enabled(True) is True
    monkeypatch.setenv("NEXUS_METRICS_JSON", "1")
    assert metrics_json_enabled(False) is True
    monkeypatch.delenv("NEXUS_METRICS_JSON", raising=False)


def test_build_context_metrics_full_graph(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    payload = g.to_json()
    m = build_context_metrics(
        stdout_payload=payload if payload.endswith("\n") else payload + "\n",
        output_mode="full_graph_json",
        graph=g,
        query=None,
        max_symbols_arg=None,
        min_confidence=None,
        pr=None,
        is_full_json=True,
        include_query_slice_stats=False,
    )
    assert m["output_mode"] == "full_graph_json"
    assert m["graph_symbols"] >= 1
    assert "slice_cap_effective" not in m
    assert m["est_tokens_chars_div_4"] == estimate_tokens_chars_div_4(m["output_chars"])
    try:
        import tiktoken  # noqa: F401
    except ImportError:
        assert "output_tokens_tiktoken" not in m
    else:
        assert "output_tokens_tiktoken" in m
        assert isinstance(m["output_tokens_tiktoken"], int)
        assert m["output_tokens_tiktoken"] >= 1


def test_count_output_tokens_tiktoken_cl100k(monkeypatch) -> None:
    pytest.importorskip("tiktoken")
    monkeypatch.delenv("NEXUS_TIKTOKEN_MODEL", raising=False)
    monkeypatch.setenv("NEXUS_TIKTOKEN_ENCODING", "cl100k_base")
    n, meta = count_output_tokens_tiktoken("hello world")
    assert n is not None and meta is not None
    assert meta["backend"] == "tiktoken"
    assert n >= 2


def test_slice_source_tokens_when_env(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("tiktoken")
    monkeypatch.delenv("NEXUS_TIKTOKEN_MODEL", raising=False)
    monkeypatch.setenv("NEXUS_TIKTOKEN_ENCODING", "cl100k_base")
    monkeypatch.setenv("NEXUS_METRICS_SLICE_SOURCE_TOKENS", "1")
    monkeypatch.delenv("NEXUS_METRICS_SLICE_SOURCE_DETAIL", raising=False)
    (tmp_path / "m.py").write_text(
        "def foo():\n    return 42\n",
        encoding="utf-8",
    )
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    pr = PerspectiveResult(payload_kind=PerspectivePayloadKind.TEXT, payload_text="x\n")
    m = build_context_metrics(
        stdout_payload="x\n",
        output_mode="llm_brief",
        graph=g,
        query="foo",
        max_symbols_arg=5,
        min_confidence=None,
        pr=pr,
        is_full_json=False,
        include_query_slice_stats=True,
    )
    assert "slice_source_tokens_total" in m
    assert m["slice_source_tokens_total"] >= 1
    assert m.get("slice_symbols_total") >= 1
    assert "compression_ratio" in m
    assert "density_source_over_output" in m
    assert "avg_source_tokens_per_symbol" in m
    assert m["compression_ratio"] > 0


def test_relevant_universe_and_coverage_ratio(monkeypatch, tmp_path: Path) -> None:
    pytest.importorskip("tiktoken")
    monkeypatch.setenv("NEXUS_METRICS_RELEVANT_UNIVERSE", "1")
    monkeypatch.delenv("NEXUS_TIKTOKEN_MODEL", raising=False)
    monkeypatch.setenv("NEXUS_TIKTOKEN_ENCODING", "cl100k_base")
    (tmp_path / "m.py").write_text(
        "def mut_a():\n    self.x = 1\n\ndef mut_b():\n    self.y = 2\n",
        encoding="utf-8",
    )
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    pr = PerspectiveResult(payload_kind=PerspectivePayloadKind.TEXT, payload_text=".\n")
    m = build_context_metrics(
        stdout_payload=".\n",
        output_mode="llm_brief",
        graph=g,
        query="mutation",
        max_symbols_arg=1,
        min_confidence=None,
        pr=pr,
        is_full_json=False,
        include_query_slice_stats=True,
    )
    assert "relevant_symbols_total" in m
    assert m["relevant_symbols_total"] >= 2
    assert m.get("slice_symbols_total") == 1
    assert m.get("slice_relevant_coverage_ratio", 0) <= 1.0


def test_max_symbols_cli_explicit_when_passed(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def x():\n  pass\n", encoding="utf-8")
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    pr = PerspectiveResult(payload_kind=PerspectivePayloadKind.TEXT, payload_text=".\n")
    m = build_context_metrics(
        stdout_payload=".\n",
        output_mode="llm_brief",
        graph=g,
        query="x",
        max_symbols_arg=7,
        min_confidence=None,
        pr=pr,
        is_full_json=False,
        include_query_slice_stats=True,
    )
    assert m["max_symbols_cli_explicit"] == 7
    assert m["slice_cap_effective"] == 7


def test_build_context_metrics_brief_slice_stats(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def mutate_state():\n    x = 1\n", encoding="utf-8")
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    text = "brief\n"
    pr = PerspectiveResult(payload_kind=PerspectivePayloadKind.TEXT, payload_text=text)
    m = build_context_metrics(
        stdout_payload=text,
        output_mode="llm_brief",
        graph=g,
        query="mutation",
        max_symbols_arg=5,
        min_confidence=None,
        pr=pr,
        is_full_json=False,
        include_query_slice_stats=True,
    )
    assert m["slice_cap_effective"] == 5
    assert "symbols_in_heuristic_slice" in m
    assert m["symbols_in_heuristic_slice"] >= 0
    assert m.get("slice_symbols_total") == m["symbols_in_heuristic_slice"]


def test_build_context_metrics_includes_compact_fields(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    m = build_context_metrics(
        stdout_payload="x\n",
        output_mode="perspective:agent_compact",
        graph=g,
        query="f",
        max_symbols_arg=5,
        min_confidence=None,
        pr=None,
        is_full_json=False,
        include_query_slice_stats=True,
        compact_fields=["calls", "writes"],
    )
    assert m["compact_fields"] == ["calls", "writes"]


def test_build_context_metrics_agent_mode_flag(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path, mode="fresh", cache_dir=None)
    m = build_context_metrics(
        stdout_payload="x\n",
        output_mode="perspective:agent_compact",
        graph=g,
        query="f",
        max_symbols_arg=10,
        min_confidence=None,
        pr=None,
        is_full_json=False,
        include_query_slice_stats=True,
        agent_mode=True,
    )
    assert m.get("agent_mode") is True


def test_build_context_metrics_line_is_valid_json(capsys) -> None:
    from nexus.output.context_metrics import emit_context_metrics_line

    emit_context_metrics_line({"a": 1, "b": "x"})
    err = capsys.readouterr().err
    assert err.startswith("[NEXUS_METRICS] ")
    payload = err[len("[NEXUS_METRICS] ") :].strip()
    assert json.loads(payload) == {"a": 1, "b": "x"}
