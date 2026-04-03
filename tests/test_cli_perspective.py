from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus.cli import AGENT_MODE_DEFAULT_MAX_SYMBOLS, main


def test_agent_mode_sets_compact_perspective_and_minimal(tmp_path: Path, capsys) -> None:
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    code = main([str(tmp_path), "--agent-mode", "-q", "flow", "--metrics-json"])
    assert code == 0
    out = capsys.readouterr()
    assert "QUERY: flow" in out.out
    assert "  L=" not in out.out
    metrics = None
    for ln in out.err.splitlines():
        if ln.startswith("[NEXUS_METRICS] "):
            metrics = json.loads(ln[len("[NEXUS_METRICS] ") :].strip())
            break
    assert metrics is not None
    assert metrics.get("agent_mode") is True
    assert metrics.get("compact_fields") == ["calls", "writes"]
    assert metrics.get("max_symbols_cli_explicit") == AGENT_MODE_DEFAULT_MAX_SYMBOLS


def test_agent_mode_conflicts_with_other_perspective(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        main(
            [
                str(tmp_path),
                "--agent-mode",
                "--perspective",
                "llm_brief",
                "-q",
                "x",
            ]
        )
    assert e.value.code == 2


def test_agent_mode_max_symbols_override(tmp_path: Path, capsys) -> None:
    lines = "\n\n".join(f"def fn{i}():\n    pass" for i in range(12))
    (tmp_path / "m.py").write_text(lines + "\n", encoding="utf-8")
    code = main(
        [
            str(tmp_path),
            "--agent-mode",
            "-q",
            "fn",
            "--max-symbols",
            "3",
        ]
    )
    assert code == 0
    assert f"PRIMARY (n=3):" in capsys.readouterr().out


def test_perspective_heuristic_slice_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text("def a():\n    b()\ndef b():\n    pass\n", encoding="utf-8")
    code = main(
        [
            str(tmp_path),
            "--perspective",
            "heuristic_slice",
            "-q",
            "flow",
            "--max-symbols",
            "5",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out, "expected qualified_name lines"


def test_perspective_llm_brief_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    code = main(
        [str(tmp_path), "--perspective", "llm_brief", "-q", "flow", "--max-symbols", "2"]
    )
    assert code == 0
    assert "REPO:" in capsys.readouterr().out


def test_perspective_trust_detail_requires_center(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        main([str(tmp_path), "--perspective", "trust_detail", "-q", "flow"])
    assert e.value.code == 2


def test_perspective_trust_detail_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    code = main(
        [
            str(tmp_path),
            "--perspective",
            "trust_detail",
            "--center-kind",
            "symbol_qualified_name",
            "--center-ref",
            "m.x",
        ]
    )
    assert code == 0
    assert "qualified_name:" in capsys.readouterr().out


def test_perspective_mutation_trace_uses_mutation_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "s.py").write_text("def set_hp(o):\n    o.hp = 10\n", encoding="utf-8")
    code = main(
        [
            str(tmp_path),
            "--perspective",
            "mutation_trace",
            "--mutation-key",
            "hp",
        ]
    )
    assert code == 0
    import json

    data = json.loads(capsys.readouterr().out)
    assert "direct_writes" in data


def test_debug_perspective_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text("def x(): pass\n", encoding="utf-8")
    code = main(
        [
            str(tmp_path),
            "--perspective",
            "llm_brief",
            "-q",
            "flow",
            "--max-symbols",
            "2",
            "--debug-perspective",
        ]
    )
    assert code == 0
    err = capsys.readouterr().err
    assert "[NEXUS_PERSPECTIVE]" in err
    assert "payload_kind" in err
    assert "provenance" in err


def test_perspective_mutually_exclusive_with_names_only(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as e:
        main(
            [
                str(tmp_path),
                "--perspective",
                "llm_brief",
                "--names-only",
                "-q",
                "x",
            ]
        )
    assert e.value.code == 2


def test_perspective_agent_symbol_lines_with_annotate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    code = main(
        [
            str(tmp_path),
            "--perspective",
            "agent_symbol_lines",
            "-q",
            "flow",
            "--max-symbols",
            "2",
            "--annotate",
        ]
    )
    assert code == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip() and not ln.startswith("SAME_NAME")]
    assert lines, "expected annotated lines"
    assert " | c=" in lines[0]
