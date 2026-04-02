from __future__ import annotations

from typing import Any

from nexus.core.models import SymbolRecord


def build_table_rows(slice_: list[SymbolRecord]) -> list[dict[str, Any]]:
    """Qt-freie Tabellenzeilen für die Inference Console (Primary Cognitive Interface)."""
    rows: list[dict[str, Any]] = []
    for s in slice_:
        rows.append(
            {
                "name": s.qualified_name,
                "confidence": s.confidence,
                "layer": s.layer,
                "writes_count": len(s.writes),
                "calls_count": len(s.calls),
                "_symbol": s,
            }
        )
    return rows
