from __future__ import annotations

from pathlib import Path

import pytest

from nexus import attach
from nexus.core.models import SymbolRecord
from nexus.output.llm_format import (
    entry_point_heuristic_score,
    generic_query_symbol_slice,
    top_entry_point_symbols,
)


def _sym(
    *,
    name: str,
    file: str,
    qualified_name: str,
    kind: str = "function",
    calls: list[str] | None = None,
    writes: list[str] | None = None,
    line_start: int = 1,
    line_end: int = 10,
    called_by: list[str] | None = None,
    semantic_tags: list[str] | None = None,
) -> SymbolRecord:
    return SymbolRecord(
        id=f"id:{qualified_name}",
        name=name,
        kind=kind,
        file=file,
        line_start=line_start,
        line_end=line_end,
        qualified_name=qualified_name,
        signature="",
        docstring=None,
        calls=list(calls or []),
        writes=list(writes or []),
        called_by=list(called_by or []),
        semantic_tags=list(semantic_tags or []),
    )


def test_entry_point_prefers_service_commit_over_init() -> None:
    commit = _sym(
        name="commit_event",
        file="app/services/application.py",
        qualified_name="app.services.application.commit_event",
        calls=["a", "b"],
        writes=["state"],
    )
    init = _sym(
        name="__init__",
        file="app/services/application.py",
        qualified_name="app.services.application.ApplicationService.__init__",
        calls=["super"],
    )
    assert entry_point_heuristic_score(commit) > entry_point_heuristic_score(init)


def test_entry_point_deprioritizes_utils_and_getters() -> None:
    core = _sym(
        name="commit_preview",
        file="app/resolver/engine.py",
        qualified_name="app.resolver.engine.commit_preview",
        calls=["x"] * 5,
        writes=["y"],
    )
    util = _sym(
        name="fmt_ts",
        file="app/utils/timefmt.py",
        qualified_name="app.utils.timefmt.fmt_ts",
        line_end=2,
    )
    getter = _sym(
        name="get_foo",
        file="app/models/x.py",
        qualified_name="app.models.x.get_foo",
    )
    assert entry_point_heuristic_score(core) > entry_point_heuristic_score(util)
    assert entry_point_heuristic_score(core) > entry_point_heuristic_score(getter)


def test_top_entry_point_symbols_order() -> None:
    syms = [
        _sym(name="z", file="app/util/z.py", qualified_name="app.util.z.z"),
        _sym(
            name="commit_event",
            file="app/services/application.py",
            qualified_name="app.services.application.commit_event",
            calls=["a"],
            writes=["b"],
        ),
        _sym(name="__init__", file="app/x.py", qualified_name="app.x.C.__init__"),
    ]
    top = top_entry_point_symbols(syms, k=2)
    assert [s.name for s in top] == ["commit_event", "z"]


def test_generic_query_slice_orders_commit_event_before_resolver_process() -> None:
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "entry_rank_mini"
    g = attach(fixture_root)
    syms = generic_query_symbol_slice(g, "symbol overview", max_symbols=10)
    names = [s.name for s in syms]
    assert "commit_event" in names and "process_next" in names
    assert names.index("commit_event") < names.index("process_next")


def test_cli_grep_prints_entry_banner(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nexus.cli_grep import main

    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)
    code = main(
        [
            str(repo_root),
            "-q",
            "flow",
            "--max-symbols",
            "5",
            "--dry-run",
            "--no-entry-candidates",
        ]
    )
    assert code == 0
    out_no = capsys.readouterr().out
    assert "[ENTRY CANDIDATE" not in out_no

    code2 = main([str(repo_root), "-q", "flow", "--max-symbols", "5", "--dry-run"])
    assert code2 == 0
    out_yes = capsys.readouterr().out
    assert "[ENTRY CANDIDATE #1]" in out_yes
    assert "[ENTRY CANDIDATE #2]" in out_yes
    assert "[ENTRY CANDIDATE #3]" in out_yes
