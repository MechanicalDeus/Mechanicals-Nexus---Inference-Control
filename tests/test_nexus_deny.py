from __future__ import annotations

import os
from pathlib import Path

from nexus import attach
from nexus.parsing.loader import discover_py_files
from nexus.parsing.nexus_deny import NEXUS_DENY_NAME, NEXUS_SKIP_NAME, NexusDeny


def _repo_under_parent(tmp_path: Path) -> Path:
    """Mapped tree is tmp_path/repo; deny file is tmp_path/.nexusdeny."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    return repo


def test_nexusdeny_directory_prefix(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("secret/\n", encoding="utf-8")
    (repo / "keep").mkdir()
    (repo / "keep" / "a.py").write_text("def f(): pass\n", encoding="utf-8")
    (repo / "secret").mkdir()
    (repo / "secret" / "b.py").write_text("def g(): pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "keep/a.py" in paths
    assert "secret/b.py" not in paths


def test_nexusdeny_basename_glob(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("*.py\n", encoding="utf-8")
    (repo / "x.py").write_text("pass\n", encoding="utf-8")
    (repo / "sub").mkdir()
    (repo / "sub" / "y.py").write_text("pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert paths == set()


def test_nexus_skip_stops_subtree(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    box = repo / "boxed"
    box.mkdir()
    (box / NEXUS_SKIP_NAME).write_text("", encoding="utf-8")
    (box / "inner").mkdir()
    (box / "inner" / "z.py").write_text("def z(): pass\n", encoding="utf-8")
    (repo / "ok.py").write_text("def ok(): pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "ok.py" in paths
    assert not any(p.startswith("boxed/") for p in paths)


def test_attach_respects_nexusdeny_single_file(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("hidden.py\n", encoding="utf-8")
    (repo / "hidden.py").write_text("def x(): pass\n", encoding="utf-8")
    (repo / "vis.py").write_text("def y(): pass\n", encoding="utf-8")
    g_hidden = attach(repo / "hidden.py")
    assert not g_hidden.symbols
    g_vis = attach(repo / "vis.py")
    assert any(s.name == "y" for s in g_vis.symbols.values())


def test_nexusdeny_anchored_root_only(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("/cfg.py\n", encoding="utf-8")
    (repo / "cfg.py").write_text("pass\n", encoding="utf-8")
    nested = repo / "sub"
    nested.mkdir()
    (nested / "cfg.py").write_text("pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "cfg.py" not in paths
    assert "sub/cfg.py" in paths


def test_nexusdeny_comment_line(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("# *.py\n", encoding="utf-8")
    (repo / "a.py").write_text("pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "a.py" in paths


def test_nexus_deny_class_matches_paths(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    (tmp_path / NEXUS_DENY_NAME).write_text("x/**\n", encoding="utf-8")
    ig = NexusDeny(repo)
    assert ig.matches("x", is_dir=True)
    assert ig.matches("x/a/b", is_dir=False)


def test_nexusdeny_inside_mapped_tree_is_ignored(tmp_path: Path) -> None:
    """`.nexusdeny` inside the scan root must not be read (only parent file)."""
    repo = _repo_under_parent(tmp_path)
    (repo / NEXUS_DENY_NAME).write_text("*.py\n", encoding="utf-8")
    (repo / "keep.py").write_text("pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "keep.py" in paths


def test_nexusdeny_merges_multiple_parent_files(tmp_path: Path) -> None:
    """Ancestor directories may each contribute a `.nexusdeny`; all rules apply."""
    grand = tmp_path / "grand"
    parent = grand / "parent"
    repo = parent / "repo"
    repo.mkdir(parents=True)
    (grand / NEXUS_DENY_NAME).write_text("from_grand.py\n", encoding="utf-8")
    (parent / NEXUS_DENY_NAME).write_text("from_parent.py\n", encoding="utf-8")
    (repo / "from_grand.py").write_text("pass\n", encoding="utf-8")
    (repo / "from_parent.py").write_text("pass\n", encoding="utf-8")
    (repo / "ok.py").write_text("pass\n", encoding="utf-8")
    paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    assert "ok.py" in paths
    assert "from_grand.py" not in paths
    assert "from_parent.py" not in paths


def test_nexus_deny_env_path_extra(tmp_path: Path) -> None:
    repo = _repo_under_parent(tmp_path)
    extra = tmp_path / "global_deny.txt"
    extra.write_text("envblocked.py\n", encoding="utf-8")
    (repo / "envblocked.py").write_text("pass\n", encoding="utf-8")
    (repo / "ok.py").write_text("pass\n", encoding="utf-8")
    old = os.environ.get("NEXUS_DENY_PATH")
    try:
        os.environ["NEXUS_DENY_PATH"] = str(extra)
        paths = {p.relative_to(repo).as_posix() for p in discover_py_files(repo)}
    finally:
        if old is None:
            os.environ.pop("NEXUS_DENY_PATH", None)
        else:
            os.environ["NEXUS_DENY_PATH"] = old
    assert "envblocked.py" not in paths
    assert "ok.py" in paths
