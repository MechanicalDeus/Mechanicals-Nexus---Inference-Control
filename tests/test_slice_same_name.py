from __future__ import annotations

from pathlib import Path

from nexus import attach
from nexus.output.llm_format import agent_qualified_names


def test_llm_brief_query_folds_same_name_to_one_block(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "def dup():\n    self.x = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text(
        "def dup():\n    self.y = 2\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    brief = g.to_llm_brief(query="mutation", max_symbols=10)
    assert "SAME_NAME" in brief
    assert brief.count("### ") == 1
    assert "same_name_also:" in brief


def test_agent_qualified_names_primary_plus_same_name_footer(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "def dup():\n    self.x = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text(
        "def dup():\n    self.y = 2\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    lines = agent_qualified_names(g, query="mutation", max_symbols=10)
    assert lines is not None
    qn_lines = [L for L in lines if not L.startswith(" ") and "SAME_NAME" not in L]
    assert len(qn_lines) == 1
    assert any("SAME_NAME" in L for L in lines)
