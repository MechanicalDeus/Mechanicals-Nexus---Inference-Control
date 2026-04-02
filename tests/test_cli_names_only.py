from __future__ import annotations

from pathlib import Path

import pytest

from nexus.cli import main


def test_nexus_names_only_annotate_smoke(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    code = main(
        [
            str(repo_root),
            "-q",
            "flow",
            "--max-symbols",
            "3",
            "--names-only",
            "--annotate",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out, "expected at least one annotated line"
    # Example: qname | c=0.73 | tags=... | layer=... | file.py:1-10
    assert " | c=" in out[0]
    assert " | tags=" in out[0]
    assert " | layer=" in out[0]
    assert ":" in out[0] and "-" in out[0]


def test_nexus_annotate_requires_names_only() -> None:
    with pytest.raises(SystemExit) as e:
        main(["-q", "flow", "--annotate"])
    assert e.value.code == 2
