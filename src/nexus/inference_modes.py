from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from nexus.core.graph import InferenceGraph
from nexus.core.models import Edge, FileRecord, SymbolRecord
from nexus.parsing.loader import discover_py_files
from nexus.parsing.nexus_ignore import NexusIgnore

InferenceMode = Literal["fresh", "persistent", "hybrid"]


@dataclass(frozen=True)
class CacheKey:
    repo_root: str
    include_tests: bool
    transitive_depth: int

    def stable_id(self) -> str:
        h = hashlib.sha256()
        h.update(self.repo_root.encode("utf-8"))
        h.update(b"\0")
        h.update(b"tests=1" if self.include_tests else b"tests=0")
        h.update(b"\0")
        h.update(f"td={self.transitive_depth}".encode("utf-8"))
        return h.hexdigest()[:24]


def graph_from_json_dict(d: dict[str, Any]) -> InferenceGraph:
    repo = str(d.get("repo") or "")
    files_raw = d.get("files") or []
    symbols_raw = d.get("symbols") or []
    edges_raw = d.get("edges") or []

    files: list[FileRecord] = []
    for f in files_raw:
        if not isinstance(f, dict):
            continue
        files.append(
            FileRecord(
                path=str(f.get("path") or ""),
                module_hint=str(f.get("module_hint") or ""),
                redacted=bool(f.get("redacted") or False),
            )
        )

    symbols: dict[str, SymbolRecord] = {}
    for s in symbols_raw:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        if not sid:
            continue
        symbols[sid] = SymbolRecord(
            id=sid,
            name=str(s.get("name") or ""),
            kind=str(s.get("kind") or ""),
            file=str(s.get("file") or ""),
            line_start=int(s.get("line_start") or 0),
            line_end=int(s.get("line_end") or 0),
            qualified_name=str(s.get("qualified_name") or ""),
            signature=str(s.get("signature") or ""),
            docstring=s.get("docstring"),
            reads=list(s.get("reads") or []),
            writes=list(s.get("writes") or []),
            indirect_writes=list(s.get("indirect_writes") or []),
            transitive_writes=list(s.get("transitive_writes") or []),
            calls=list(s.get("calls") or []),
            called_by=list(s.get("called_by") or []),
            constructs=list(s.get("constructs") or []),
            inherits_from=list(s.get("inherits_from") or []),
            semantic_tags=list(s.get("semantic_tags") or []),
            has_dynamic_call=bool(s.get("has_dynamic_call") or False),
            has_local_assign=bool(s.get("has_local_assign") or False),
            confidence=float(s.get("confidence") or 1.0),
            layer=str(s.get("layer") or "support"),
            mutation_paths=[list(p) for p in (s.get("mutation_paths") or [])],
            mutation_path_scores=list(s.get("mutation_path_scores") or []),
            mutation_path_confidence=list(s.get("mutation_path_confidence") or []),
        )

    edges: list[Edge] = []
    for e in edges_raw:
        if not isinstance(e, dict):
            continue
        edges.append(
            Edge(
                from_id=str(e.get("from") or ""),
                to_id=str(e.get("to") or ""),
                type=str(e.get("type") or ""),
            )
        )

    return InferenceGraph(repo_root=repo, files=files, symbols=symbols, edges=edges)


def repo_fingerprint(repo_root: Path, *, include_tests: bool) -> str:
    """
    Best-effort fingerprint without reading file contents.

    Intended for HYBRID mode: validate that a cached graph likely still matches the
    working tree. Uses file paths + mtime_ns + size for discovered .py files,
    excluding NexusIgnore-covered files.
    """
    root = repo_root.resolve()
    ig = NexusIgnore(root)
    files = discover_py_files(root, include_tests=include_tests)
    h = hashlib.sha256()
    for fp in files:
        rel = fp.resolve().relative_to(root).as_posix()
        if ig.covers_file(rel):
            continue
        try:
            st = fp.stat()
        except OSError:
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))).encode("utf-8"))
        h.update(b"\0")
        h.update(str(int(st.st_size)).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def cache_paths(cache_dir: Path, key: CacheKey) -> tuple[Path, Path]:
    cid = key.stable_id()
    return cache_dir / f"graph-{cid}.json", cache_dir / f"graph-{cid}.meta.json"


def load_cached_graph(
    cache_dir: Path, key: CacheKey
) -> tuple[InferenceGraph | None, dict[str, Any] | None]:
    graph_path, meta_path = cache_paths(cache_dir, key)
    try:
        g_raw = json.loads(graph_path.read_text(encoding="utf-8"))
        meta_raw = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    except OSError:
        return None, None
    except json.JSONDecodeError:
        return None, None
    if not isinstance(g_raw, dict):
        return None, None
    if meta_raw is not None and not isinstance(meta_raw, dict):
        meta_raw = {}
    return graph_from_json_dict(g_raw), meta_raw


def save_cached_graph(
    cache_dir: Path,
    key: CacheKey,
    *,
    graph: InferenceGraph,
    meta: dict[str, Any],
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    graph_path, meta_path = cache_paths(cache_dir, key)
    graph_path.write_text(graph.to_json(indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
