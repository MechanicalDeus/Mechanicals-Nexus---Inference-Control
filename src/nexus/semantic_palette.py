"""
Kanonische Hex-Farben für Inference-Console und CLI (ohne PyQt-Import).

``nexus.ui.theme`` bezieht Basis- und Graph-Farben hierher; Terminal nutzt
dieselben Werte für Relationen, Layer-Badges und Fokus — eine Bedeutung, ein Hex.
"""

from __future__ import annotations

# --- Basis (QSS / allgemein) ---
BG_MAIN = "#161616"
BG_PANEL = "#1e1e1e"
BG_HEADER = "#2b2b2b"
TEXT_PRIMARY = "#e8e8e8"
TEXT_MUTED = "#a0a0a0"
ACCENT = "#2e86c1"
BORDER = "#3a3a3a"
BORDER_HOVER = "#888888"

# --- Graph-Rollen (Tabelle / Legende / FocusGraphView) ---
GRAPH_ROLE_HEX: dict[str, str] = {
    "center": "#5a9fd4",
    "caller": "#6bcb77",
    "callee": "#d4a574",
}

# --- Layer: Zellen-Hintergrund (Qt-Tabelle) ---
LAYER_CELL_BG_HEX: dict[str, str] = {
    "core": "#24384a",
    "interface": "#243a30",
    "support": "#32243a",
    "test": "#3a3424",
}

# --- Symbol-kind: Vordergrund (Kind-Spalte) ---
KIND_TEXT_HEX: dict[str, str] = {
    "class": "#5dade2",
    "function": "#58d68d",
    "method": "#48c9b0",
    "module": "#aab7b8",
}

# --- Semantische Kanten / Reason-Zeilen (CLI + eine Sprache mit UI-Graph) ---
# called_by = caller-Rolle (Einstieg); calls = Fluss (cyan, lesbar neben ACCENT-Blau);
# writes = Wirkung; reads = passiv.
SEMANTIC_RELATION_HEX: dict[str, str] = {
    "called_by": GRAPH_ROLE_HEX["caller"],
    "calls": "#2dd4e8",
    "writes": "#e74c3c",
    "reads": TEXT_MUTED,
}

# --- Layer-Badges in Text (Terminal; kompakt zu Zellen-Hintergrund) ---
LAYER_LABEL_HEX: dict[str, str] = {
    "core": "#c084fc",
    "interface": "#fbbf24",
    "support": TEXT_MUTED,
    "test": "#94a3b8",
}

# --- Fokus / aktiver Knoten ---
HEX_CENTER = GRAPH_ROLE_HEX["center"]
HEX_FOCUS_LOCK = "#9b59b6"
INFLUENCE_LABEL_HEX = HEX_FOCUS_LOCK

__all__ = [
    "ACCENT",
    "BG_HEADER",
    "BG_MAIN",
    "BG_PANEL",
    "BORDER",
    "BORDER_HOVER",
    "GRAPH_ROLE_HEX",
    "HEX_CENTER",
    "HEX_FOCUS_LOCK",
    "INFLUENCE_LABEL_HEX",
    "KIND_TEXT_HEX",
    "LAYER_CELL_BG_HEX",
    "LAYER_LABEL_HEX",
    "SEMANTIC_RELATION_HEX",
    "TEXT_MUTED",
    "TEXT_PRIMARY",
]
