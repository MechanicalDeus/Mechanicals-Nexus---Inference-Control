"""
Zentrale Farben und QSS für die Inference Console.

Semantik pro ``UiPalette`` (Dunkel/Hell); Widgets nutzen ``ui_palette()`` und Helper
(QColor/QPen), keine verstreuten RGB-Literale.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPen

from nexus.semantic_palette import PALETTE_DARK, UiPalette

_active: UiPalette = PALETTE_DARK


def ui_palette() -> UiPalette:
    return _active


def set_ui_palette(p: UiPalette) -> None:
    global _active
    _active = p


# --- Konfidenz: Gewichtung (weniger Signal = gedimmt/ausgegraut, kein „Fehler-Rot“) ---
def confidence_text_qcolor(confidence: float) -> QColor | None:
    pal = ui_palette()
    c = float(confidence)
    if c >= 0.82:
        return None
    if c >= 0.55:
        out = QColor(pal.text_primary)
        out.setAlphaF(0.62)
        return out
    out = QColor(pal.text_muted)
    out.setAlphaF(0.9)
    return out


def graph_role_qcolor(role: str) -> QColor:
    h = ui_palette().graph_role_hex.get(role, "#888888")
    return QColor(h)


def graph_edge_pen() -> QPen:
    p = QPen(QColor(ui_palette().graph_edge))
    p.setWidthF(1.25)
    return p


def graph_edge_pen_highlight() -> QPen:
    p = QPen(QColor(ui_palette().accent))
    p.setWidthF(2.25)
    return p


def graph_edge_pen_dim() -> QPen:
    pal = ui_palette()
    c = QColor(pal.graph_edge_dim)
    c.setAlphaF(0.38)
    p = QPen(c)
    p.setWidthF(1.0)
    return p


def graph_node_outline_pen() -> QPen:
    pal = ui_palette()
    pen_node = QPen(QColor(pal.graph_node_stroke))
    pen_node.setWidthF(1.5)
    return pen_node


def layer_cell_qcolor(layer: str) -> QColor | None:
    key = (layer or "").strip().lower()
    h = ui_palette().layer_cell_bg_hex.get(key)
    if not h:
        return None
    return QColor(h)


def kind_text_qcolor(kind: str) -> QColor | None:
    key = (kind or "").strip().lower()
    h = ui_palette().kind_text_hex.get(key)
    if not h:
        return None
    return QColor(h)


def application_stylesheet(p: UiPalette | None = None) -> str:
    pal = p if p is not None else ui_palette()
    return f"""
    QMainWindow, QWidget {{
        background-color: {pal.bg_main};
        color: {pal.text_primary};
    }}
    QGroupBox {{
        border: 1px solid {pal.border};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 4px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {pal.text_muted};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {pal.bg_panel};
        color: {pal.text_primary};
        border: 1px solid {pal.border};
        border-radius: 3px;
        padding: 4px 6px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {pal.accent};
    }}
    QPushButton {{
        background-color: {pal.bg_panel};
        color: {pal.text_primary};
        border: 1px solid {pal.border};
        border-radius: 3px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        border: 1px solid {pal.border_hover};
    }}
    QPushButton:pressed {{
        background-color: {pal.bg_header};
    }}
    QTableView {{
        background-color: {pal.bg_panel};
        alternate-background-color: {pal.bg_main};
        color: {pal.text_primary};
        gridline-color: {pal.border};
        border: 1px solid {pal.border};
        border-radius: 3px;
    }}
    QTableView::item:selected {{
        background-color: {pal.accent};
        color: {pal.table_selection_fg};
    }}
    QHeaderView::section {{
        background-color: {pal.bg_header};
        color: {pal.text_primary};
        padding: 6px;
        border: none;
        border-bottom: 2px solid {pal.accent};
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border: 1px solid {pal.border};
        border-radius: 3px;
        top: -1px;
        background-color: {pal.bg_main};
    }}
    QTabBar::tab {{
        background-color: {pal.bg_header};
        color: {pal.text_muted};
        padding: 6px 14px;
        border: 1px solid {pal.border};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {pal.bg_panel};
        color: {pal.text_primary};
    }}
    QTextEdit, QPlainTextEdit {{
        background-color: {pal.bg_panel};
        color: {pal.text_primary};
        border: 1px solid {pal.border};
        border-radius: 3px;
    }}
    QCheckBox {{
        color: {pal.text_primary};
    }}
    QLabel {{
        color: {pal.text_primary};
    }}
    QSplitter::handle {{
        background-color: {pal.border};
        width: 3px;
        height: 3px;
    }}
    QStatusBar {{
        background-color: {pal.bg_header};
        color: {pal.text_muted};
        border-top: 1px solid {pal.border};
    }}
    """
