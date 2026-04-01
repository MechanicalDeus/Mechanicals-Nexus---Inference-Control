from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

from nexus.analysis.mutation_chains import build_qualified_name_index
from nexus.output.confidence_brief import format_confidence_line

if TYPE_CHECKING:
    from nexus.core.graph import InferenceGraph
    from nexus.core.models import Edge, SymbolRecord


def build_callers_index(edges: list[Edge]) -> dict[str, list[str]]:
    m: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.type == "calls":
            m[e.to_id].append(e.from_id)
    return m


def detect_special_query_mode(q: str) -> str:
    qn = q.strip().lower()
    if "impact" in qn:
        return "impact"
    if "mutation chain" in qn or "full mutation" in qn:
        return "mutation_chain"
    if "core system" in qn or "core flow" in qn:
        return "core_flow"
    if "core mutation" in qn:
        return "core_mutation"
    if "why" in qn:
        return "why"
    return ""


def impact_target_phrase(raw_query: str) -> str | None:
    low = raw_query.lower()
    if "impact" not in low:
        return None
    i = low.index("impact") + len("impact")
    rest = raw_query[i:].strip()
    return rest if rest else None


def why_keywords(q: str) -> list[str]:
    low = q.lower()
    if "why" not in low:
        return []
    i = low.index("why") + 3
    rest = low[i:].strip().strip("?")
    stop = {
        "is",
        "are",
        "the",
        "a",
        "an",
        "does",
        "do",
        "changed",
        "change",
        "happening",
        "happen",
        "being",
        "was",
        "were",
    }
    return [w for w in rest.split() if w.lower() not in stop and len(w) > 2]


def _sym_text_blob(s: SymbolRecord) -> str:
    parts = list(s.writes) + list(s.indirect_writes) + list(s.transitive_writes)
    return " ".join(parts).lower()


def core_runtime_query_boost(s: SymbolRecord, q_lower: str) -> float:
    """Heuristischer Boost, wenn die Query Resolver/Runtime/Commit thematisiert."""
    if not any(k in q_lower for k in ("runtime", "resolver", "commit")):
        return 0.0
    boost = 0.0
    qn = s.qualified_name.lower()
    if s.layer == "core":
        boost += 0.2
    if "resolver" in q_lower and "resolver" in qn:
        boost += 0.25
    if "runtime" in q_lower and "runtime" in qn:
        boost += 0.25
    if "commit" in q_lower and "commit" in qn:
        boost += 0.2
    return boost


def format_mutation_chain_row(index: int, path: list[str], sym: SymbolRecord) -> str:
    i = index - 1
    ps = sym.mutation_path_scores[i] if i < len(sym.mutation_path_scores) else None
    pc = sym.mutation_path_confidence[i] if i < len(sym.mutation_path_confidence) else None
    if ps is not None and pc is not None:
        return f"  chain {index} (path_score={ps}, path_conf={pc}): {' → '.join(path)}"
    return f"  chain {index}: {' → '.join(path)}"


def _why_path_reason_lines(path: list[str], qn_to_sym: dict[str, SymbolRecord]) -> list[str]:
    """Kurze, strukturierte Erklärzeilen (heuristisch, kein echter Reasoner)."""
    nodes = [qn_to_sym.get(qn) for qn in path]
    nodes = [n for n in nodes if n is not None]
    if not nodes:
        return []
    lines: list[str] = []
    blob = " ".join(path).lower()
    if "resolver" in blob or any("resolver" in (n.file or "").lower() for n in nodes):
        lines.append("    reason: Auslöser-Pfad enthält Resolver/Orchestrierung (Namens-/Pfad-Heuristik).")
    elif nodes[0].layer == "core":
        lines.append("    reason: Einstieg in der Core-Schicht.")
    mids = [n for n in nodes[1:-1]]
    if mids and any(n.layer == "core" for n in mids):
        lines.append("    reason: Läuft über Core-Logik (z. B. Runtime/Dienste).")
    last = nodes[-1]
    if last.layer == "infrastructure":
        lines.append("    reason: Endet bei Infrastruktur/Persistenz-Schicht.")
    if last.writes:
        w = ", ".join(last.writes[:4])
        lines.append(f"    reason: Terminal schreibt direkt: {w}")
    return lines[:5]


def format_impact_view(
    graph: InferenceGraph,
    raw_query: str,
    *,
    cap: int,
    min_confidence: float | None,
    callers_index: dict[str, list[str]],
) -> str:
    phrase = impact_target_phrase(raw_query)
    if not phrase:
        phrase = ""
    needle = phrase.lower()
    targets = [
        s
        for s in graph.symbols.values()
        if needle in s.qualified_name.lower() or needle in s.name.lower()
    ]
    if not targets and phrase:
        targets = [
            s
            for s in graph.symbols.values()
            if any(
                needle in p.lower()
                for path in s.mutation_paths
                for p in path
            )
        ]
    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    lines.append(f"QUERY (impact): {raw_query.strip()}")
    lines.append(f"Matches: {len(targets)} symbol(s)")
    lines.append("")

    shown = 0
    for t in sorted(targets, key=lambda x: x.qualified_name):
        if min_confidence is not None and t.confidence < min_confidence:
            continue
        if shown >= cap:
            break
        shown += 1
        lines.append(f"## Target: {t.qualified_name} ({t.kind})  layer={t.layer}")
        lines.append(format_confidence_line(t))
        if t.writes:
            lines.append(f"  direct_writes: {', '.join(t.writes[:12])}")
        anc = _bfs_caller_qualified(t.id, callers_index, graph.symbols, limit=22)
        if anc:
            lines.append("  callers (reverse BFS, qualified names):")
            for a in anc:
                lines.append(f"    ← {a}")
        if t.mutation_paths:
            lines.append("  sample mutation_paths (best path_score first):")
            for i, p in enumerate(t.mutation_paths[:3], 1):
                lines.append(format_mutation_chain_row(i, p, t).replace("  chain ", "    path "))
        lines.append("")

    if not shown:
        lines.append("(no symbols matched the impact phrase — try a shorter class/function name)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _bfs_caller_qualified(
    start_id: str,
    callers_index: dict[str, list[str]],
    symbols: dict[str, SymbolRecord],
    *,
    limit: int,
) -> list[str]:
    q: deque[str] = deque([start_id])
    seen: set[str] = {start_id}
    out: list[str] = []
    while q and len(out) < limit:
        uid = q.popleft()
        for pid in callers_index.get(uid, []):
            if pid in seen:
                continue
            seen.add(pid)
            sym = symbols.get(pid)
            if sym:
                out.append(sym.qualified_name)
            q.append(pid)
            if len(out) >= limit:
                break
    return out


def format_mutation_chain_view(
    graph: InferenceGraph,
    raw_query: str,
    *,
    cap: int,
    min_confidence: float | None,
) -> str:
    syms = [
        s
        for s in graph.symbols.values()
        if s.kind in ("function", "method") and s.mutation_paths
    ]
    def _best_path_score(s: SymbolRecord) -> float:
        return max(s.mutation_path_scores, default=0.0)

    def _best_path_conf(s: SymbolRecord) -> float:
        return max(s.mutation_path_confidence, default=0.0)

    syms.sort(
        key=lambda s: (
            -_best_path_score(s),
            -_best_path_conf(s),
            -s.confidence,
            s.qualified_name,
        )
    )
    if min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]
    syms = syms[:cap]

    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    lines.append(f"QUERY (mutation chains): {raw_query.strip()}")
    lines.append(
        f"Symbols with ≥1 path to a direct writer: {len(syms)} (capped)"
    )
    lines.append("")
    for s in syms:
        lines.append(f"### {s.qualified_name}  layer={s.layer}")
        lines.append(format_confidence_line(s))
        for i, path in enumerate(s.mutation_paths[:10], 1):
            lines.append(format_mutation_chain_row(i, path, s))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_core_flow_view(
    graph: InferenceGraph,
    raw_query: str,
    *,
    cap: int,
    min_confidence: float | None,
) -> str:
    syms = [
        s
        for s in graph.symbols.values()
        if s.layer == "core"
        and (s.calls or s.writes or s.indirect_writes or s.transitive_writes)
        and s.kind in ("function", "method")
    ]
    syms.sort(key=_core_flow_sort_key)
    if min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]
    syms = syms[:cap]

    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    lines.append(f"QUERY (core system flow): {raw_query.strip()}")
    lines.append(f"Core-layer symbols in slice: {len(syms)}")
    lines.append("")
    for s in syms:
        lines.append(f"### {s.qualified_name}")
        lines.append(format_confidence_line(s))
        if s.writes:
            lines.append(f"  writes: {', '.join(s.writes[:10])}")
        if s.calls:
            lines.append(f"  calls: {', '.join(sorted(s.calls)[:15])}")
        if s.mutation_paths:
            lines.append(format_mutation_chain_row(1, s.mutation_paths[0], s))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _core_flow_sort_key(s: SymbolRecord) -> tuple[int, str]:
    role = 0
    if "resolver" in s.file.lower() or "resolver" in s.qualified_name.lower():
        role = 3
    elif "runtime" in s.file.lower() or "runtime" in s.qualified_name.lower():
        role = 2
    elif "chronicle" in s.file.lower() or "chronicle" in s.qualified_name.lower():
        role = 1
    return (-role, s.qualified_name)


def format_core_mutation_view(
    graph: InferenceGraph,
    raw_query: str,
    *,
    cap: int,
    min_confidence: float | None,
) -> str:
    syms = [
        s
        for s in graph.symbols.values()
        if s.layer == "core"
        and (s.writes or s.indirect_writes or s.transitive_writes)
    ]
    syms.sort(key=lambda s: (-s.confidence, s.qualified_name))
    if min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]
    syms = syms[:cap]

    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    lines.append(f"QUERY (core mutation): {raw_query.strip()}")
    lines.append(f"Symbols: {len(syms)}")
    lines.append("")
    for s in syms:
        lines.append(f"### {s.qualified_name}")
        lines.append(format_confidence_line(s))
        if s.writes:
            lines.append(f"  writes: {', '.join(s.writes[:12])}")
        if s.mutation_paths:
            for i, path in enumerate(s.mutation_paths[:4], 1):
                lines.append(format_mutation_chain_row(i, path, s))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_why_view(
    graph: InferenceGraph,
    raw_query: str,
    *,
    cap: int,
    min_confidence: float | None,
) -> str:
    keys = why_keywords(raw_query)
    if not keys:
        keys = ["state"]

    def matches(s: SymbolRecord) -> bool:
        blob = _sym_text_blob(s)
        return any(k.lower() in blob for k in keys)

    syms = [s for s in graph.symbols.values() if matches(s) and s.kind in ("function", "method")]
    q_low = raw_query.lower()
    boost_on = any(k in q_low for k in ("runtime", "resolver", "commit"))

    def _why_sort_key(s: SymbolRecord) -> tuple[float, float, float, int, str]:
        b = core_runtime_query_boost(s, q_low) if boost_on else 0.0
        best_sc = max(s.mutation_path_scores, default=0.0)
        return (-b, -s.confidence, -best_sc, -len(s.mutation_paths), s.qualified_name)

    syms.sort(key=_why_sort_key)
    if min_confidence is not None:
        syms = [s for s in syms if s.confidence >= min_confidence]
    syms = syms[:cap]

    lines: list[str] = []
    lines.append(f"REPO: {graph.repo_root}")
    lines.append(f"QUERY (why / cause→effect hints): {raw_query.strip()}")
    lines.append(f"Keywords: {keys}")
    lines.append(f"Symbols touching those state strings: {len(syms)}")
    lines.append("")
    qn_ix = build_qualified_name_index(graph.symbols)
    for s in syms:
        lines.append(f"### {s.qualified_name}  layer={s.layer}")
        lines.append(format_confidence_line(s))
        if s.writes:
            lines.append(f"  writes: {', '.join(s.writes[:10])}")
        if s.transitive_writes:
            lines.append(f"  transitive_writes: {', '.join(s.transitive_writes[:10])}")
        for i, path in enumerate(s.mutation_paths[:5], 1):
            lines.append(format_mutation_chain_row(i, path, s))
            for rline in _why_path_reason_lines(path, qn_ix):
                lines.append(rline)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
