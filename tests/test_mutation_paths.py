from __future__ import annotations

from pathlib import Path

from nexus import attach


def test_mutation_paths_three_hop(tmp_path: Path) -> None:
    (tmp_path / "c.py").write_text(
        "def persist(x):\n    x.saved = True\n\n"
        "def commit(o):\n    persist(o)\n\n"
        "def run():\n    commit(object())\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    run = next(s for s in g.symbols.values() if s.name == "run")
    assert run.mutation_paths
    flat = [n for path in run.mutation_paths for n in path]
    assert any("persist" in n for n in flat)


def test_layer_core_runtime_path(tmp_path: Path) -> None:
    d = tmp_path / "app" / "runtime"
    d.mkdir(parents=True)
    (d / "x.py").write_text("def f():\n    pass\n", encoding="utf-8")
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert f.layer == "core"


def test_detect_mutation_chain_mode() -> None:
    from nexus.output.llm_query_modes import detect_special_query_mode

    assert detect_special_query_mode("full mutation chain") == "mutation_chain"
    assert detect_special_query_mode("impact ChronicleWriter") == "impact"


def test_mutation_paths_shorter_ranked_first(tmp_path: Path) -> None:
    """Kürzerer Pfad zum Writer soll höheren path_score und Index 0 haben."""
    (tmp_path / "w.py").write_text(
        "def writer(x):\n    x.v = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "m.py").write_text(
        "from w import writer\n"
        "def mid(o):\n    writer(o)\n"
        "def deep(o):\n    mid(o)\n"
        "def entry(o):\n    writer(o)\n    deep(o)\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    entry = next(s for s in g.symbols.values() if s.name == "entry")
    assert len(entry.mutation_paths) >= 2
    assert len(entry.mutation_path_scores) == len(entry.mutation_paths)
    assert len(entry.mutation_path_confidence) == len(entry.mutation_paths)
    # Kürzer: entry -> writer
    assert len(entry.mutation_paths[0]) < len(entry.mutation_paths[1])
    assert entry.mutation_path_scores[0] >= entry.mutation_path_scores[1]


def test_path_metrics_align_with_paths(tmp_path: Path) -> None:
    (tmp_path / "c.py").write_text(
        "def persist(x):\n    x.saved = True\n\n"
        "def commit(o):\n    persist(o)\n\n"
        "def run():\n    commit(object())\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    run = next(s for s in g.symbols.values() if s.name == "run")
    assert len(run.mutation_paths) == len(run.mutation_path_scores)
    d = run.to_dict()
    assert len(d["mutation_paths"]) == len(d["mutation_path_scores"])
