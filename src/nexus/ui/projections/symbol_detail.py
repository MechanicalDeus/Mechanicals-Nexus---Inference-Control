from __future__ import annotations

from nexus.core.models import SymbolRecord


def format_symbol_detail(symbol: SymbolRecord) -> str:
    """Trust Engine: nur Felder aus SymbolRecord, keine erfundene Begründung."""
    lines: list[str] = [
        f"qualified_name: {symbol.qualified_name}",
        f"id: {symbol.id}",
        f"kind: {symbol.kind}",
        f"file: {symbol.file}:{symbol.line_start}-{symbol.line_end}",
        f"signature: {symbol.signature}",
        f"confidence: {symbol.confidence}",
        f"layer: {symbol.layer}",
    ]
    if symbol.docstring:
        lines.append(
            f"docstring: {symbol.docstring[:500]}{'…' if len(symbol.docstring) > 500 else ''}"
        )
    if symbol.semantic_tags:
        lines.append(f"semantic_tags: {', '.join(symbol.semantic_tags)}")
    lines.append(f"has_dynamic_call: {symbol.has_dynamic_call}")
    lines.append(f"has_local_assign: {symbol.has_local_assign}")
    if symbol.reads:
        lines.append(f"reads: {', '.join(symbol.reads[:40])}")
    if symbol.writes:
        lines.append(f"writes: {', '.join(symbol.writes[:40])}")
    if symbol.indirect_writes:
        lines.append(f"indirect_writes: {', '.join(symbol.indirect_writes[:30])}")
    if symbol.transitive_writes:
        lines.append(f"transitive_writes: {', '.join(symbol.transitive_writes[:30])}")
    if symbol.calls:
        lines.append(f"calls: {', '.join(sorted(symbol.calls)[:40])}")
    if symbol.called_by:
        lines.append(f"called_by (ids): {', '.join(symbol.called_by[:20])}")
    if symbol.constructs:
        lines.append(f"constructs: {', '.join(symbol.constructs[:20])}")
    if symbol.inherits_from:
        lines.append(f"inherits_from: {', '.join(symbol.inherits_from)}")
    if symbol.mutation_paths:
        lines.append("mutation_paths:")
        for i, path in enumerate(symbol.mutation_paths[:12]):
            score = symbol.mutation_path_scores[i] if i < len(symbol.mutation_path_scores) else None
            conf = (
                symbol.mutation_path_confidence[i]
                if i < len(symbol.mutation_path_confidence)
                else None
            )
            extra = []
            if score is not None:
                extra.append(f"score={score}")
            if conf is not None:
                extra.append(f"path_confidence={conf}")
            suf = f" ({', '.join(extra)})" if extra else ""
            lines.append(f"  {' → '.join(path)}{suf}")
    return "\n".join(lines)
