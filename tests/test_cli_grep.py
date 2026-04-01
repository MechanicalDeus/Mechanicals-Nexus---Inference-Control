from __future__ import annotations

from pathlib import Path

import pytest

from nexus.cli_grep import main


def test_nexus_grep_rejects_special_impact_query() -> None:
    assert main(["--query", "impact ResolverEngine"]) == 2


def test_nexus_grep_dry_run_on_repo_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    code = main(
        [
            str(repo_root),
            "-q",
            "flow",
            "--max-symbols",
            "3",
            "--dry-run",
        ]
    )
    assert code == 0
