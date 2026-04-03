from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.cli import main


def test_query_slice_json_requires_query() -> None:
    with pytest.raises(SystemExit) as e:
        main([".", "--query-slice-json"])
    assert e.value.code == 2


def test_output_modes_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as e:
        main([".", "--json", "--query-slice-json", "-q", "flow"])
    assert e.value.code == 2


def test_query_slice_json_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    code = main(
        [
            str(tmp_path),
            "-q",
            "flow",
            "--max-symbols",
            "5",
            "--query-slice-json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "repo" in data and "symbols" in data and "edges" in data
    assert isinstance(data["symbols"], list)


def test_trace_mutation_json_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "s.py").write_text(
        "def set_hp(o):\n    o.hp = 10\n",
        encoding="utf-8",
    )
    code = main([str(tmp_path), "--trace-mutation", "hp"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data.keys()) == {"direct_writes", "indirect_writes", "transitive_writes"}


def test_focus_graph_unknown_symbol(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    code = main([str(tmp_path), "--focus-graph", "nope.not_there"])
    assert code == 1
    assert "qualified_name" in capsys.readouterr().err


def test_focus_graph_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    code = main([str(tmp_path), "--focus-graph", "m.a"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "nodes" in data and "edges" in data
    roles = {n["id"]: n["role"] for n in data["nodes"]}
    assert any(r == "center" for r in roles.values())
