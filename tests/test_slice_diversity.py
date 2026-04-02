from __future__ import annotations

from pathlib import Path

from nexus import attach
from nexus.output.llm_format import generic_query_symbol_slice


def test_generic_query_slice_diversifies_files(tmp_path: Path) -> None:
    """
    Token-efficiency: avoid spending the whole slice budget on one hot file when
    another file contains equally relevant orchestration.
    """
    (tmp_path / "hot.py").write_text(
        "\n".join(
            [
                "def a():\n    x.y = 1\n",
                "def b():\n    x.y = 2\n",
                "def c():\n    x.y = 3\n",
                "def d():\n    x.y = 4\n",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def orchestrate():\n    x.y = 9\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    syms = generic_query_symbol_slice(g, "mutation", max_symbols=4)
    files = {s.file for s in syms}
    assert "hot.py" in files
    assert "other.py" in files

