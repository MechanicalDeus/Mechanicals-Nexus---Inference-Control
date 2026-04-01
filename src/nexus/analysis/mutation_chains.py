from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus.core.models import SymbolRecord

# Höher = wichtiger für Sortierung (core > infrastructure > interface).
LAYER_WEIGHT: dict[str, float] = {
    "core": 1.0,
    "infrastructure": 0.82,
    "interface": 0.65,
    "test": 0.35,
    "support": 0.55,
}


def build_qualified_name_index(symbols: dict[str, "SymbolRecord"]) -> dict[str, "SymbolRecord"]:
    """Ein Symbol pro qualified_name (bei Kollision höhere confidence gewinnt)."""
    out: dict[str, SymbolRecord] = {}
    for sym in symbols.values():
        qn = sym.qualified_name
        prev = out.get(qn)
        if prev is None or sym.confidence > prev.confidence:
            out[qn] = sym
    return out


def score_mutation_path(
    path_qnames: list[str],
    qn_to_sym: dict[str, "SymbolRecord"],
) -> tuple[float, float]:
    """
    Gibt (path_score, path_confidence) zurück — höherer Score = relevanter Pfad.
    path_confidence = Mittel der Symbol-``confidence`` entlang des Pfads.
    """
    nodes = [qn_to_sym[qn] for qn in path_qnames if qn in qn_to_sym]
    if not nodes:
        return 0.0, 0.0
    n = len(nodes)
    length_term = 8.0 / n
    layer_term = sum(LAYER_WEIGHT.get(sym.layer, 0.5) for sym in nodes) / n
    direct_bonus = 0.35 if n == 1 else 0.0
    transit = 0.0
    for i in range(len(nodes) - 1):
        a, b = nodes[i].layer, nodes[i + 1].layer
        if a == "core" and b == "infrastructure":
            transit += 0.12
    path_score = length_term + 2.2 * layer_term + direct_bonus + min(transit, 0.25)
    confs = [sym.confidence for sym in nodes]
    path_confidence = sum(confs) / len(confs)
    return path_score, path_confidence


def rank_mutation_paths(
    paths: list[list[str]],
    qn_to_sym: dict[str, "SymbolRecord"],
) -> tuple[list[list[str]], list[float], list[float]]:
    """Sortiert Pfade nach path_score (absteigend), dann path_confidence, dann kürzere Länge."""
    scored: list[tuple[float, float, int, list[str]]] = []
    for path in paths:
        ps, pc = score_mutation_path(path, qn_to_sym)
        scored.append((ps, pc, len(path), path))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
    return (
        [t[3] for t in scored],
        [round(t[0], 4) for t in scored],
        [round(t[1], 4) for t in scored],
    )


def compute_mutation_paths(
    start_id: str,
    callees_by_caller: dict[str, list[str]],
    symbols: dict[str, "SymbolRecord"],
    *,
    max_depth: int = 14,
    max_paths: int = 25,
) -> list[list[str]]:
    """
    Alle Call-Pfade ab ``start_id``, die bei einem Symbol mit mindestens einem
    ``writes``-Eintrag enden (Zyklus-sicher pro Pfad).
    """
    results: list[list[str]] = []
    seen_paths: set[tuple[str, ...]] = set()

    def dfs(curr_id: str, path_stack: list[str], in_path: set[str]) -> None:
        if len(results) >= max_paths:
            return
        sym = symbols.get(curr_id)
        if sym is None:
            return
        if curr_id in in_path:
            return
        qn = sym.qualified_name
        new_stack = path_stack + [qn]
        new_in = in_path | {curr_id}

        if sym.writes:
            key = tuple(new_stack)
            if key not in seen_paths:
                seen_paths.add(key)
                results.append(list(new_stack))

        if len(new_stack) >= max_depth:
            return

        for nxt in callees_by_caller.get(curr_id, []):
            dfs(nxt, new_stack, new_in)

    dfs(start_id, [], set())
    return results
