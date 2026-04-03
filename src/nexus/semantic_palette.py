"""
Kanonische Hex-Farben für Inference-Console und CLI (ohne PyQt-Import).

``nexus.ui.theme`` bezieht Basis- und Graph-Farben hierher; Terminal nutzt
dieselben Werte für Relationen, Layer-Badges und Fokus — eine Bedeutung, ein Hex.

Zwei UI-Paletten (Dunkel/Hell) steuern die Qt-Oberfläche; die Modul-Konstanten
unten bleiben **Dark** (CLI/Terminal unverändert).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiPalette:
    """Eine vollständige Farbfamilie für QSS + Graph + Tabellen-Semantik."""

    name: str
    bg_main: str
    bg_panel: str
    bg_header: str
    text_primary: str
    text_muted: str
    accent: str
    border: str
    border_hover: str
    graph_role_hex: dict[str, str]
    layer_cell_bg_hex: dict[str, str]
    kind_text_hex: dict[str, str]
    graph_edge: str
    graph_edge_dim: str
    graph_node_stroke: str
    table_selection_fg: str


PALETTE_DARK = UiPalette(
    name="dark",
    bg_main="#161616",
    bg_panel="#1e1e1e",
    bg_header="#2b2b2b",
    text_primary="#e8e8e8",
    text_muted="#a0a0a0",
    accent="#2e86c1",
    border="#3a3a3a",
    border_hover="#888888",
    graph_role_hex={
        "center": "#5a9fd4",
        "caller": "#6bcb77",
        "callee": "#d4a574",
    },
    layer_cell_bg_hex={
        "core": "#24384a",
        "interface": "#243a30",
        "support": "#32243a",
        "test": "#3a3424",
    },
    kind_text_hex={
        "class": "#5dade2",
        "function": "#58d68d",
        "method": "#48c9b0",
        "module": "#aab7b8",
    },
    graph_edge="#707070",
    graph_edge_dim="#5a5a5a",
    graph_node_stroke="#1a1a1a",
    table_selection_fg="#ffffff",
)

PALETTE_LIGHT = UiPalette(
    name="light",
    bg_main="#ececec",
    bg_panel="#ffffff",
    bg_header="#dedede",
    text_primary="#1a1a1a",
    text_muted="#5c5c5c",
    accent="#1565c0",
    border="#b8b8b8",
    border_hover="#757575",
    graph_role_hex={
        "center": "#0d47a1",
        "caller": "#1b5e20",
        "callee": "#bf360c",
    },
    layer_cell_bg_hex={
        "core": "#cfe8fc",
        "interface": "#c8e6c9",
        "support": "#e1bee7",
        "test": "#fff9c4",
    },
    kind_text_hex={
        "class": "#0277bd",
        "function": "#2e7d32",
        "method": "#00695c",
        "module": "#546e7a",
    },
    graph_edge="#616161",
    graph_edge_dim="#9e9e9e",
    graph_node_stroke="#bdbdbd",
    table_selection_fg="#ffffff",
)


# --- CLI / Terminal: fest Dark (unveränderte Semantik) ---
BG_MAIN = PALETTE_DARK.bg_main
BG_PANEL = PALETTE_DARK.bg_panel
BG_HEADER = PALETTE_DARK.bg_header
TEXT_PRIMARY = PALETTE_DARK.text_primary
TEXT_MUTED = PALETTE_DARK.text_muted
ACCENT = PALETTE_DARK.accent
BORDER = PALETTE_DARK.border
BORDER_HOVER = PALETTE_DARK.border_hover
GRAPH_ROLE_HEX: dict[str, str] = PALETTE_DARK.graph_role_hex
LAYER_CELL_BG_HEX: dict[str, str] = PALETTE_DARK.layer_cell_bg_hex
KIND_TEXT_HEX: dict[str, str] = PALETTE_DARK.kind_text_hex

# --- Semantische Kanten / Reason-Zeilen (CLI + eine Sprache mit UI-Graph) ---
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
    "PALETTE_DARK",
    "PALETTE_LIGHT",
    "SEMANTIC_RELATION_HEX",
    "TEXT_MUTED",
    "TEXT_PRIMARY",
    "UiPalette",
]
