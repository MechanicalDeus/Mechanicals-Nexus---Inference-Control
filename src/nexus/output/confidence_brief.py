"""Interpretierbare Confidence-Zeilen für LLM- und CLI-Output."""

from __future__ import annotations

from nexus.core.models import SymbolRecord


def confidence_band(confidence: float) -> str:
    if confidence > 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def confidence_rationale(s: SymbolRecord) -> str:
    """Kurze, kommaseparierte Stichworte (Unsicherheit + Mutationsgrad)."""
    tags = s.semantic_tags
    bits: list[str] = []
    if "ambiguous-call" in tags:
        bits.append("ambiguous")
    if "dynamic-call" in tags:
        bits.append("dynamic")
    if "unknown-import" in tags:
        bits.append("unknown import")
    if s.writes:
        bits.append("direct mutation")
    elif s.indirect_writes:
        bits.append("indirect mutation")
    elif s.transitive_writes:
        bits.append("transitive mutation")
    elif not bits:
        bits.append("no tracked state writes")
    return ", ".join(bits[:5])


def format_confidence_line(s: SymbolRecord) -> str:
    return (
        f"  confidence: {s.confidence:.2f} "
        f"({confidence_band(s.confidence)}, {confidence_rationale(s)})"
    )
