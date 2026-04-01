from __future__ import annotations

from pathlib import Path

from nexus.cursor_rules import iter_mdc_rules, rules_root
from nexus.cursor_rules_cli import main


def test_bundled_nexus_over_grep_mdc() -> None:
    names = [n for n, _ in iter_mdc_rules()]
    assert "nexus-over-grep.mdc" in names
    root = rules_root()
    text = root.joinpath("nexus-over-grep.mdc").read_text(encoding="utf-8")
    assert "Nexus statt breitem Grep" in text
    assert "nexus-cursor-rules install" in text


def test_install_creates_cursor_rules(tmp_path: Path) -> None:
    code = main([str(tmp_path), "--force"])
    assert code == 0
    target = tmp_path / ".cursor" / "rules" / "nexus-over-grep.mdc"
    assert target.is_file()
    assert "alwaysApply: true" in target.read_text(encoding="utf-8")


def test_install_skips_without_force(tmp_path: Path) -> None:
    assert main([str(tmp_path), "--force"]) == 0
    assert main([str(tmp_path)]) == 1
    assert main([str(tmp_path), "--force"]) == 0


def test_list_and_path_exit_zero() -> None:
    assert main(["--list"]) == 0
    assert main(["--path"]) == 0
