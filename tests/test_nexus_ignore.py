from __future__ import annotations

from pathlib import Path

from nexus import attach
from nexus.parsing.nexus_ignore import NEXUS_IGNORE_NAME, NexusIgnore


def test_nexusignore_stub_no_symbols(tmp_path: Path) -> None:
    (tmp_path / NEXUS_IGNORE_NAME).write_text("secrets.py\n", encoding="utf-8")
    (tmp_path / "secrets.py").write_text("def api_key(): return 'sk-xx'\n", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def y(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    redacted = [f for f in g.files if f.redacted]
    assert len(redacted) == 1
    assert redacted[0].path == "secrets.py"
    assert redacted[0].module_hint == "<redacted>"
    assert not any(s.file == "secrets.py" for s in g.symbols.values())
    assert any(s.name == "y" for s in g.symbols.values())


def test_nexusignore_parent_directory_covers_children(tmp_path: Path) -> None:
    (tmp_path / NEXUS_IGNORE_NAME).write_text("vault/\n", encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "inner.py").write_text("def x(): pass\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def m(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    paths_redacted = {f.path for f in g.files if f.redacted}
    assert "vault/inner.py" in paths_redacted
    assert not any(s.file.startswith("vault/") for s in g.symbols.values())


def test_nexusignore_to_json_flags_redacted(tmp_path: Path) -> None:
    (tmp_path / NEXUS_IGNORE_NAME).write_text("x.py\n", encoding="utf-8")
    (tmp_path / "x.py").write_text("pass\n", encoding="utf-8")
    g = attach(tmp_path)
    d = g.to_json_dict()
    files = d["files"]
    xf = next(f for f in files if f["path"] == "x.py")
    assert xf.get("redacted") is True


def test_nexus_ignore_covers_file_helper(tmp_path: Path) -> None:
    (tmp_path / NEXUS_IGNORE_NAME).write_text("a/**\n", encoding="utf-8")
    ig = NexusIgnore(tmp_path)
    assert ig.covers_file("a/b/c.py")
