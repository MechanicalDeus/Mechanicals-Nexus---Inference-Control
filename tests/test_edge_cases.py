from __future__ import annotations

from pathlib import Path

from nexus import attach


def test_ambiguous_import_two_targets(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def foo():\n    return 2\n", encoding="utf-8")
    (tmp_path / "c.py").write_text(
        "from a import foo\nfrom b import foo\n\ndef bar():\n    foo()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    bar = next(s for s in g.symbols.values() if s.name == "bar")
    assert "ambiguous-call" in bar.semantic_tags
    tos = [e.to_id for e in g.edges if e.from_id == bar.id]
    assert len(tos) >= 2


def test_star_import_in_repo(tmp_path: Path) -> None:
    (tmp_path / "lib.py").write_text("def exported():\n    pass\n", encoding="utf-8")
    (tmp_path / "use.py").write_text(
        "from lib import *\n\ndef run():\n    exported()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    run = next(s for s in g.symbols.values() if s.name == "run" and "use" in s.file)
    tos = [e.to_id for e in g.edges if e.from_id == run.id]
    assert any("exported" in t for t in tos)


def test_star_import_unknown_marks_unknown_import(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text(
        "from nonexistent_pkg_xyz import *\n\ndef f():\n    pass\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert "unknown-import" in f.semantic_tags


def test_inherited_method_resolution(tmp_path: Path) -> None:
    (tmp_path / "inh.py").write_text(
        "class A:\n"
        "    def run(self):\n"
        "        pass\n\n"
        "class B(A):\n"
        "    def use(self):\n"
        "        self.run()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    use = next(s for s in g.symbols.values() if s.name == "use" and s.kind == "method")
    tos = [e.to_id for e in g.edges if e.from_id == use.id]
    assert any("run" in t for t in tos)


def test_dynamic_call_tagged(tmp_path: Path) -> None:
    (tmp_path / "d.py").write_text(
        "def f():\n    (lambda: None)()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert "dynamic-call" in f.semantic_tags


def test_local_assign_not_state_write(tmp_path: Path) -> None:
    (tmp_path / "l.py").write_text(
        "def f():\n    x = 5\n    return x\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert "x" not in f.writes
    assert "local-write" in f.semantic_tags
