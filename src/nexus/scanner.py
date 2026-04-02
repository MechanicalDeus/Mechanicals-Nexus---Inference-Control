from __future__ import annotations

import sys
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from nexus.analysis.layers import infer_layer
from nexus.analysis.mutation_chains import (
    build_qualified_name_index,
    compute_mutation_paths,
    rank_mutation_paths,
)
from nexus.core.graph import InferenceGraph
from nexus.core.models import Edge, FileRecord, SymbolRecord
from nexus.parsing.ast_analyze import FileAnalysis, analyze_file
from nexus.parsing.loader import discover_py_files, path_to_module_hint
from nexus.parsing.nexus_deny import NexusDeny
from nexus.parsing.nexus_ignore import NexusIgnore
from nexus.resolution.imports import qualify_call_name


@contextmanager
def _deep_recursion(min_depth: int = 20000) -> object:
    prev = sys.getrecursionlimit()
    sys.setrecursionlimit(max(prev, min_depth))
    try:
        yield
    finally:
        sys.setrecursionlimit(prev)


def _symbol_id(qualified_name: str) -> str:
    return f"symbol:{qualified_name}"


def _is_toplevel_in_module(qualified_name: str, module_hint: str) -> bool:
    if not qualified_name.startswith(module_hint + "."):
        return False
    rest = qualified_name[len(module_hint) + 1 :]
    return "." not in rest


def _resolve_base_qnames(expr: str, module_hint: str) -> list[str]:
    s = expr.strip()
    if not s or "(" in s or "[" in s:
        return []
    if "." in s:
        return [s]
    return [f"{module_hint}.{s}"]


def _add_alias_target(
    targets: dict[str, list[str]],
    local: str,
    fqn: str,
) -> None:
    if not local or not fqn:
        return
    lst = targets.setdefault(local, [])
    if fqn not in lst:
        lst.append(fqn)


def _build_module_exports(analyses_by_path: dict[str, FileAnalysis]) -> dict[str, list[tuple[str, str]]]:
    exports: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fa in analyses_by_path.values():
        m = fa.module_hint
        for rs in fa.symbols:
            if rs.kind not in ("function", "class"):
                continue
            if not _is_toplevel_in_module(rs.qualified_name, m):
                continue
            exports[m].append((rs.name, rs.qualified_name))
    return exports


def _merge_star_imports(
    symbol_alias_targets: dict[str, list[str]],
    star_modules: list[str],
    exports_by_module: dict[str, list[tuple[str, str]]],
) -> list[str]:
    unresolved: list[str] = []
    for mod in star_modules:
        ex = exports_by_module.get(mod)
        if not ex:
            unresolved.append(mod)
            continue
        for name, fqn in ex:
            _add_alias_target(symbol_alias_targets, name, fqn)
    return unresolved


def _compute_symbol_confidence(sym: SymbolRecord) -> float:
    """
    Heuristischer Vertrauenswert [0, 1] nach Scan (Tags + Mutationsgrad).

    Start 1.0; Abzüge für Unsicherheit und fehlende Mutations-Evidenz;
    Zuschläge für erkannte State-Mutation.
    """
    score = 1.0
    tags = sym.semantic_tags
    if "ambiguous-call" in tags:
        score -= 0.4
    if "dynamic-call" in tags:
        score -= 0.7
    if "unknown-import" in tags:
        score -= 0.8
    if "delegate" in tags:
        score -= 0.2
    state = bool(sym.writes or sym.indirect_writes or sym.transitive_writes)
    if sym.calls and not state:
        score -= 0.3
    if sym.writes:
        score += 0.3
    if sym.indirect_writes:
        score += 0.2
    if sym.transitive_writes:
        score += 0.1
    return round(max(0.0, min(1.0, score)), 4)


def _tag_symbol(sym: SymbolRecord) -> None:
    tags: list[str] = []
    tw = sym.transitive_writes
    iw = sym.indirect_writes
    w = sym.writes
    if w or iw or tw:
        tags.append("mutator")
    if w:
        tags.append("direct-mutation")
    if iw:
        tags.append("indirect-mutation")
    if tw:
        tags.append("transitive-mutation")
    if sym.calls and not w and not iw and not tw:
        tags.append("delegate")
    if not sym.calls and not w and not iw and not tw:
        tags.append("leaf")
    if sym.has_dynamic_call:
        tags.append("dynamic-call")
    if sym.has_local_assign:
        tags.append("local-write")
    sym.semantic_tags = tags


def _resolve_call_targets(
    call_name: str,
    same_file_ids: set[str],
    name_to_ids: dict[str, list[str]],
    qualified_index: dict[str, str],
    import_hints: list[str] | None,
    *,
    module_hint: str,
    class_qnames: set[str],
    class_bases: dict[str, list[str]],
) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def add_sid(sid: str) -> None:
        if sid not in seen:
            seen.add(sid)
            collected.append(sid)

    for h in import_hints or []:
        if h in qualified_index:
            add_sid(qualified_index[h])

    if collected:
        return collected

    if call_name in qualified_index:
        return [qualified_index[call_name]]

    if "." in call_name:
        suffix_matches = [
            sid
            for q, sid in qualified_index.items()
            if q == call_name or q.endswith("." + call_name)
        ]
        if len(suffix_matches) == 1:
            return suffix_matches
        same = [m for m in suffix_matches if m in same_file_ids]
        if len(same) == 1:
            return same
        if len(suffix_matches) > 1:
            return suffix_matches

        qual, _, method = call_name.rpartition(".")
        class_keys: list[str] = []
        if qual in class_qnames:
            class_keys.append(qual)
        elif module_hint:
            fq_cls = f"{module_hint}.{qual}"
            if fq_cls in class_qnames:
                class_keys.append(fq_cls)
        for ck in class_keys:
            for b in class_bases.get(ck, []):
                cand = f"{b}.{method}"
                if cand in qualified_index:
                    add_sid(qualified_index[cand])
        if collected:
            return collected

    ids = name_to_ids.get(call_name, [])
    if not ids:
        return []
    same = [i for i in ids if i in same_file_ids]
    if len(same) == 1:
        return same
    if len(ids) == 1:
        return ids
    return []


def _fixpoint_transitive_writes(
    symbols: dict[str, SymbolRecord],
    callees_by_caller: dict[str, list[str]],
    *,
    max_iterations: int,
) -> dict[str, set[str]]:
    """
    Iterative Propagation: pro Symbol alle Writes/Indirect/Transitive der Callees
    (Fixpunkt), bis stabil — erfasst längere Ketten als ein DFS mit Tiefenlimit.
    """
    trans: dict[str, set[str]] = {sid: set() for sid in symbols}
    cap = max(1, max_iterations)
    for _ in range(cap):
        new_t: dict[str, set[str]] = {}
        changed = False
        for sid, sym in symbols.items():
            acc: set[str] = set()
            for c in callees_by_caller.get(sid, []):
                t = symbols.get(c)
                if not t:
                    continue
                acc.update(t.writes)
                acc.update(t.indirect_writes)
                acc.update(trans[c])
            out = acc - set(sym.writes)
            new_t[sid] = out
            if out != trans[sid]:
                changed = True
        trans = new_t
        if not changed:
            break
    return trans


def scan(
    path: str | Path,
    *,
    include_tests: bool = True,
    follow_imports: bool = False,
    transitive_depth: int = 12,
) -> InferenceGraph:
    """
    Baue eine InferenceGraph aus einem Verzeichnis oder einer einzelnen .py-Datei.

    ``follow_imports`` bleibt für künftige externe Auflösung reserviert; intra-repo
    Imports werden immer über die Import-Tabelle aufgelöst.
    """
    _ = follow_imports
    with _deep_recursion():
        return _scan_impl(
            path,
            include_tests=include_tests,
            follow_imports=follow_imports,
            transitive_depth=transitive_depth,
        )


def _scan_impl(
    path: str | Path,
    *,
    include_tests: bool,
    follow_imports: bool,
    transitive_depth: int,
) -> InferenceGraph:
    _ = follow_imports
    root = Path(path).resolve()
    repo_root = str(root if root.is_dir() else root.parent)

    if root.is_file() and root.suffix == ".py":
        parent = root.parent.resolve()
        deny = NexusDeny(parent)
        rel_one = root.name
        if deny.matches(rel_one, is_dir=False):
            files = []
        else:
            files = [root]
        repo_root = str(parent)
    else:
        files = discover_py_files(root, include_tests=include_tests)

    root_for_module = Path(repo_root).resolve()
    nexus_ignore = NexusIgnore(root_for_module)
    file_records: list[FileRecord] = []
    analyses_by_path: dict[str, FileAnalysis] = {}
    symbols: dict[str, SymbolRecord] = {}
    name_to_ids: dict[str, list[str]] = {}
    qualified_to_id: dict[str, str] = {}

    for fp in files:
        rel = fp.resolve().relative_to(root_for_module)
        rel_s = rel.as_posix()
        if nexus_ignore.covers_file(rel_s):
            file_records.append(
                FileRecord(
                    path=rel_s,
                    module_hint="<redacted>",
                    redacted=True,
                )
            )
            continue
        mod = path_to_module_hint(root_for_module, fp)
        file_records.append(FileRecord(path=rel_s, module_hint=mod))
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            fa = analyze_file(text, rel_path=rel_s, module_hint=mod)
        except (SyntaxError, RecursionError):
            continue
        analyses_by_path[rel_s] = fa

        for rs in fa.symbols:
            sid = _symbol_id(rs.qualified_name)
            sr = SymbolRecord(
                id=sid,
                name=rs.name,
                kind=rs.kind,
                file=rel_s,
                line_start=rs.line_start,
                line_end=rs.line_end,
                qualified_name=rs.qualified_name,
                signature=rs.signature,
                docstring=rs.docstring,
                reads=sorted(rs.reads),
                writes=sorted(rs.writes),
                calls=sorted(rs.calls),
                inherits_from=list(rs.inherits_from),
                constructs=list(rs.constructs),
                has_dynamic_call=rs.has_dynamic_call,
                has_local_assign=rs.has_local_assign,
            )
            symbols[sid] = sr
            name_to_ids.setdefault(rs.name, []).append(sid)
            qualified_to_id[rs.qualified_name] = sid

    exports_by_module = _build_module_exports(analyses_by_path)
    merged_aliases_by_file: dict[str, dict[str, list[str]]] = {}
    file_unknown_star: dict[str, list[str]] = {}

    for rel_s, fa in analyses_by_path.items():
        merged = {k: list(v) for k, v in fa.symbol_alias_targets.items()}
        unresolved = _merge_star_imports(merged, fa.star_import_modules, exports_by_module)
        merged_aliases_by_file[rel_s] = merged
        if unresolved:
            file_unknown_star[rel_s] = unresolved

    class_qnames = {s.qualified_name for s in symbols.values() if s.kind == "class"}
    class_bases: dict[str, list[str]] = {}
    for s in symbols.values():
        if s.kind != "class":
            continue
        fa = analyses_by_path.get(s.file)
        mh = fa.module_hint if fa else ""
        bases: list[str] = []
        for b_expr in s.inherits_from:
            for q in _resolve_base_qnames(b_expr, mh):
                if q in class_qnames:
                    bases.append(q)
        class_bases[s.qualified_name] = bases

    file_to_ids: dict[str, set[str]] = defaultdict(set)
    for sid, s in symbols.items():
        file_to_ids[s.file].add(sid)

    edges: list[Edge] = []
    callee_set: dict[str, set[str]] = defaultdict(set)
    edge_seen: set[tuple[str, str, str]] = set()
    ambiguous_callers: set[str] = set()

    for sid, s in symbols.items():
        same_file = file_to_ids.get(s.file, set())
        merged = merged_aliases_by_file.get(s.file, {})
        fa = analyses_by_path.get(s.file)
        ma = fa.module_aliases if fa else {}
        mh = fa.module_hint if fa else ""
        for callee in s.calls:
            hints = qualify_call_name(callee, merged, ma)
            targets = _resolve_call_targets(
                callee,
                same_file,
                name_to_ids,
                qualified_to_id,
                hints,
                module_hint=mh,
                class_qnames=class_qnames,
                class_bases=class_bases,
            )
            if len(targets) > 1:
                ambiguous_callers.add(sid)
            for tid in targets:
                ek = (sid, tid, "calls")
                if ek not in edge_seen:
                    edge_seen.add(ek)
                    edges.append(Edge(from_id=sid, to_id=tid, type="calls"))
                callee_set[sid].add(tid)
                if tid in symbols:
                    symbols[tid].called_by.append(sid)

    callees_by_caller: dict[str, list[str]] = {
        k: sorted(v) for k, v in callee_set.items()
    }

    for sid, s in symbols.items():
        indirect: set[str] = set()
        same_file = file_to_ids.get(s.file, set())
        merged = merged_aliases_by_file.get(s.file, {})
        fa = analyses_by_path.get(s.file)
        ma = fa.module_aliases if fa else {}
        mh = fa.module_hint if fa else ""
        for callee in s.calls:
            hints = qualify_call_name(callee, merged, ma)
            for tid in _resolve_call_targets(
                callee,
                same_file,
                name_to_ids,
                qualified_to_id,
                hints,
                module_hint=mh,
                class_qnames=class_qnames,
                class_bases=class_bases,
            ):
                t = symbols.get(tid)
                if t:
                    indirect.update(t.writes)
        s.indirect_writes = sorted(indirect - set(s.writes))

    max_iter = max(transitive_depth, len(symbols) + 5)
    trans_map = _fixpoint_transitive_writes(
        symbols,
        callees_by_caller,
        max_iterations=max_iter,
    )
    for sid, sym in symbols.items():
        sym.transitive_writes = sorted(trans_map.get(sid, set()))

    for s in symbols.values():
        s.called_by = sorted(set(s.called_by))
        _tag_symbol(s)

    for sid in ambiguous_callers:
        sym = symbols.get(sid)
        if sym is not None and "ambiguous-call" not in sym.semantic_tags:
            sym.semantic_tags.append("ambiguous-call")

    for rel_s, fa in analyses_by_path.items():
        same = file_to_ids.get(rel_s, set())
        merged = merged_aliases_by_file.get(rel_s, {})
        for ep in fa.entrypoint_calls:
            hints = qualify_call_name(ep, merged, fa.module_aliases)
            for tid in _resolve_call_targets(
                ep,
                same,
                name_to_ids,
                qualified_to_id,
                hints,
                module_hint=fa.module_hint,
                class_qnames=class_qnames,
                class_bases=class_bases,
            ):
                sym = symbols.get(tid)
                if sym is not None and "entrypoint" not in sym.semantic_tags:
                    sym.semantic_tags.append("entrypoint")

    for rel_s, unknown in file_unknown_star.items():
        _ = unknown
        for sid in file_to_ids.get(rel_s, set()):
            sym = symbols.get(sid)
            if sym is None:
                continue
            if sym.kind not in ("function", "method"):
                continue
            if "unknown-import" not in sym.semantic_tags:
                sym.semantic_tags.append("unknown-import")

    for sym in symbols.values():
        sym.confidence = _compute_symbol_confidence(sym)

    for sym in symbols.values():
        sym.layer = infer_layer(sym.file, sym.qualified_name)

    qn_index = build_qualified_name_index(symbols)

    for sym in symbols.values():
        if sym.kind not in ("function", "method"):
            sym.mutation_paths = []
            sym.mutation_path_scores = []
            sym.mutation_path_confidence = []
            continue
        raw_paths = compute_mutation_paths(
            sym.id,
            callees_by_caller,
            symbols,
            max_depth=14,
            max_paths=25,
        )
        paths, scores, pconfs = rank_mutation_paths(raw_paths, qn_index)
        sym.mutation_paths = paths
        sym.mutation_path_scores = scores
        sym.mutation_path_confidence = pconfs

    return InferenceGraph(
        repo_root=repo_root,
        files=file_records,
        symbols=symbols,
        edges=edges,
    )


def attach(
    path: str | Path,
    *,
    include_tests: bool = True,
    follow_imports: bool = False,
    transitive_depth: int = 12,
    mode: "InferenceMode" = "fresh",
    cache_dir: str | Path | None = None,
) -> InferenceGraph:
    """Alias für :func:`scan` — API-Idee „Nexus an das Repo anbinden“.

    Modes:
    - fresh: rebuild the map on each call (no cache)
    - persistent: reuse a cached full graph if present (may be stale)
    - hybrid: reuse cached graph only if a cheap repo fingerprint still matches
    """
    from nexus.inference_modes import CacheKey, InferenceMode, load_cached_graph, repo_fingerprint, save_cached_graph

    _ = follow_imports
    root = Path(path).resolve()
    repo_root = root if root.is_dir() else root.parent
    key = CacheKey(repo_root=str(repo_root), include_tests=include_tests, transitive_depth=transitive_depth)

    if mode not in ("fresh", "persistent", "hybrid"):
        raise ValueError(f"Unknown mode: {mode!r}")

    if mode == "fresh":
        return scan(
            path,
            include_tests=include_tests,
            follow_imports=follow_imports,
            transitive_depth=transitive_depth,
        )

    if cache_dir is None:
        raise ValueError("mode requires cache_dir (security: explicit opt-in)")
    cache_dir_p = Path(cache_dir).resolve()

    cached, meta = load_cached_graph(cache_dir_p, key)
    if cached is not None:
        if mode == "persistent":
            return cached
        # hybrid
        fp_now = repo_fingerprint(repo_root, include_tests=include_tests)
        if meta and meta.get("fingerprint") == fp_now:
            return cached

    g = scan(
        path,
        include_tests=include_tests,
        follow_imports=follow_imports,
        transitive_depth=transitive_depth,
    )
    meta_out = {
        "repo_root": str(repo_root),
        "include_tests": include_tests,
        "transitive_depth": transitive_depth,
    }
    if mode == "hybrid":
        meta_out["fingerprint"] = repo_fingerprint(repo_root, include_tests=include_tests)
    save_cached_graph(cache_dir_p, key, graph=g, meta=meta_out)
    return g
