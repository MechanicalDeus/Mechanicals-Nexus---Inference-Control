from __future__ import annotations

from pathlib import Path

from nexus import attach


def test_attack_deal_damage_indirect_write(tmp_path: Path) -> None:
    code = '''
class Enemy:
    hp: int

def deal_damage(target):
    target.hp -= 5

def attack(enemy):
    deal_damage(enemy)
'''
    p = tmp_path / "fight.py"
    p.write_text(code, encoding="utf-8")
    g = attach(tmp_path)
    attack = next(s for s in g.symbols.values() if s.name == "attack")
    assert "deal_damage" in attack.calls
    assert any("hp" in w for w in attack.indirect_writes) or any(
        "hp" in w for w in attack.writes
    )


def test_direct_write(tmp_path: Path) -> None:
    p = tmp_path / "m.py"
    p.write_text(
        "def f():\n    self.x = 1\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    f = next(s for s in g.symbols.values() if s.name == "f")
    assert "self.x" in f.writes


def test_class_inherits(tmp_path: Path) -> None:
    p = tmp_path / "c.py"
    p.write_text(
        "class A: pass\nclass B(A): pass\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    b = next(s for s in g.symbols.values() if s.name == "B" and s.kind == "class")
    assert "A" in "".join(b.inherits_from)


def test_find_writers(tmp_path: Path) -> None:
    p = tmp_path / "s.py"
    p.write_text(
        "def set_hp(o):\n    o.hp = 10\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    writers = g.find_writers("hp")
    assert any(s.name == "set_hp" for s in writers)


def test_json_export_keys(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text("def a(): pass\n", encoding="utf-8")
    g = attach(tmp_path)
    d = g.to_json_dict()
    assert "repo" in d and "files" in d and "symbols" in d and "edges" in d
