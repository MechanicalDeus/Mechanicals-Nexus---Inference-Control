"""
Epistemische Trennung: ``heuristic_slice`` (reine Heuristik) vs. ``llm_brief``
(Spezialmodi). Regression-Schutz gegen versehentliche Angleichung.
"""

from __future__ import annotations

from nexus import attach
from nexus.output.perspective import (
    CenterKind,
    PerspectiveDriver,
    PerspectiveKind,
    PerspectivePayloadKind,
    PerspectiveRequest,
    render_perspective,
)


def _fight_repo(tmp_path):
    code = """
class Enemy:
    hp: int

def deal_damage(target):
    target.hp -= 5

def attack(enemy):
    deal_damage(enemy)
"""
    (tmp_path / "fight.py").write_text(code, encoding="utf-8")
    return attach(tmp_path)


def test_llm_brief_impact_mode_is_not_heuristic_slice_as_text(tmp_path) -> None:
    """Spezialmodus impact liefert eine eigene Brief-Form; Heuristik bleibt unabhängig."""
    g = _fight_repo(tmp_path)
    q = "impact deal_damage"
    h = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.HEURISTIC_SLICE,
            graph=g,
            query=q,
            max_symbols=25,
        )
    )
    b = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.LLM_BRIEF,
            graph=g,
            query=q,
            max_symbols=25,
        )
    )
    assert h.payload_kind is PerspectivePayloadKind.SYMBOL_LIST
    assert h.symbols is not None
    assert b.payload_kind is PerspectivePayloadKind.TEXT
    text = b.payload_text or ""
    assert "QUERY (impact):" in text
    flat_names = "\n".join(s.qualified_name for s in h.symbols)
    assert text.strip() != flat_names.strip()


def test_agent_names_rejects_impact_while_heuristic_slice_still_runs(tmp_path) -> None:
    """agent_names bricht bei Spezialquery ab; heuristic_slice nicht (anderer Erkenntnispfad)."""
    g = _fight_repo(tmp_path)
    q = "impact deal_damage"
    an = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.AGENT_NAMES,
            graph=g,
            query=q,
            max_symbols=25,
        )
    )
    h = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.HEURISTIC_SLICE,
            graph=g,
            query=q,
            max_symbols=25,
        )
    )
    assert an.payload_kind is PerspectivePayloadKind.ERROR
    assert h.payload_kind is PerspectivePayloadKind.SYMBOL_LIST
    assert h.symbols


def test_llm_brief_why_mode_distinct_from_plain_header(tmp_path) -> None:
    g = _fight_repo(tmp_path)
    q = "why runtime changed"
    b = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.LLM_BRIEF,
            graph=g,
            query=q,
            max_symbols=15,
        )
    )
    assert b.payload_kind is PerspectivePayloadKind.TEXT
    assert "QUERY (why" in (b.payload_text or "")


def test_focus_graph_provenance_is_center_not_query(tmp_path) -> None:
    """Zentrierte Perspektive: driver center (Grammatik), nicht query-getrieben."""
    (tmp_path / "m.py").write_text(
        "def a():\n    b()\ndef b():\n    pass\n",
        encoding="utf-8",
    )
    g = attach(tmp_path)
    sym = next(s for s in g.symbols.values() if s.name == "a")
    r = render_perspective(
        PerspectiveRequest(
            kind=PerspectiveKind.FOCUS_GRAPH,
            graph=g,
            center_kind=CenterKind.SYMBOL_ID,
            center_ref=sym.id,
        )
    )
    assert r.payload_kind is PerspectivePayloadKind.GRAPH_JSON
    assert r.provenance is not None
    assert r.provenance.driver is PerspectiveDriver.CENTER
    assert r.provenance.center_qualified_name == sym.qualified_name
