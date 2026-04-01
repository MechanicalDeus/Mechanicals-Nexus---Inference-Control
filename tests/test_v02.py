from __future__ import annotations

from pathlib import Path

from nexus import attach


def test_cross_file_import_resolves_mutation(tmp_path: Path) -> None:
    d = tmp_path / "combat"
    d.mkdir()
    (d / "damage.py").write_text(
        "def deal_damage(target):\n    target.hp -= 1\n",
        encoding="utf-8",
    )
    (d / "runner.py").write_text(
        "from combat.damage import deal_damage\n\n"
        "def attack(enemy):\n"
        "    deal_damage(enemy)\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    attack = next(s for s in g.symbols.values() if s.name == "attack")
    assert any("hp" in w for w in attack.indirect_writes) or any(
        "hp" in w for w in attack.transitive_writes
    )
    assert any(e.to_id.endswith("deal_damage") for e in g.edges if e.from_id == attack.id)


def test_transitive_multi_hop(tmp_path: Path) -> None:
    p = tmp_path / "chain.py"
    p.write_text(
        "def reduce_hp(t):\n    t.hp = 0\n\n"
        "def apply_effect(t):\n    reduce_hp(t)\n\n"
        "def attack(t):\n    apply_effect(t)\n",
        encoding="utf-8",
    )
    g = attach(tmp_path, transitive_depth=5)
    attack = next(s for s in g.symbols.values() if s.name == "attack")
    assert any("hp" in w for w in attack.transitive_writes)


def test_entrypoint_tag(tmp_path: Path) -> None:
    p = tmp_path / "cli.py"
    p.write_text(
        "def main():\n    pass\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    main = next(s for s in g.symbols.values() if s.name == "main")
    assert "entrypoint" in main.semantic_tags


def test_llm_brief_query_mutation_filter(tmp_path: Path) -> None:
    p = tmp_path / "m.py"
    p.write_text(
        "def ro(x):\n    return x\n\n"
        "def mut(y):\n    y.z = 1\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    brief = g.to_llm_brief(query="where is state mutated")
    assert "m.mut" in brief or "mut" in brief
    assert "Mutation" in brief and "state-touching" in brief
