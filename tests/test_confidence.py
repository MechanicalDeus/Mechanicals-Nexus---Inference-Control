from __future__ import annotations

from pathlib import Path

from nexus import attach


def test_confidence_default_high_for_simple_symbol(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert f.confidence == 1.0


def test_confidence_ambiguous_call_penalty(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "c.py").write_text(
        "from a import foo\nfrom b import foo\n\ndef bar():\n    foo()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    bar = next(s for s in g.symbols.values() if s.name == "bar")
    assert "ambiguous-call" in bar.semantic_tags
    assert bar.confidence == 0.1


def test_confidence_dynamic_call_penalty(tmp_path: Path) -> None:
    (tmp_path / "d.py").write_text(
        "def f():\n    (lambda: None)()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert f.confidence == 0.0


def test_confidence_unknown_import_penalty(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text(
        "from missing_mod_xyz import *\n\ndef g():\n    pass\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    gsym = next(s for s in g.symbols.values() if s.name == "g")
    assert gsym.confidence == 0.2


def test_confidence_direct_write_bonus_clamped(tmp_path: Path) -> None:
    (tmp_path / "s.py").write_text(
        "def set_x(o):\n    o.x = 1\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    s = next(s for s in g.symbols.values() if s.name == "set_x")
    assert s.writes
    assert s.confidence == 1.0


def test_llm_brief_includes_confidence(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def f():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path)
    brief = g.to_llm_brief()
    assert "confidence:" in brief
    assert "(high," in brief


def test_llm_brief_min_confidence_filter(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "c.py").write_text(
        "from a import foo\nfrom b import foo\n\ndef bar():\n    foo()\n",
        encoding="utf-8",
    )
    (tmp_path / "clean.py").write_text("def ok():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path)
    brief = g.to_llm_brief(min_confidence=0.95)
    assert "MIN_CONFIDENCE: 0.95" in brief
    assert "### c.bar" not in brief
    assert "### clean.ok" in brief


def test_confidence_band_and_rationale_unit() -> None:
    from nexus.core.models import SymbolRecord
    from nexus.output.confidence_brief import confidence_band, format_confidence_line

    assert confidence_band(0.9) == "high"
    assert confidence_band(0.7) == "medium"
    assert confidence_band(0.5) == "low"
    s = SymbolRecord(
        id="symbol:t.f",
        name="f",
        kind="function",
        file="t.py",
        line_start=1,
        line_end=1,
        qualified_name="t.f",
        signature="def f()",
        docstring=None,
        writes=["x.y"],
        semantic_tags=["direct-mutation"],
        confidence=1.0,
    )
    line = format_confidence_line(s)
    assert "1.00" in line
    assert "high" in line
    assert "direct mutation" in line
