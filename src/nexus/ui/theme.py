"""
Zentrale Farben und QSS für die Inference Console.

Alle semantischen Farben liegen hier; Widgets nutzen Helper (QColor/QPen) statt
verstreuter RGB-Literale. Dark-Theme, damit Kontrast und Tönung konsistent sind.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPen

from nexus.semantic_palette import (
    ACCENT,
    BG_HEADER,
    BG_MAIN,
    BG_PANEL,
    BORDER,
    BORDER_HOVER,
    GRAPH_ROLE_HEX,
    KIND_TEXT_HEX,
    LAYER_CELL_BG_HEX,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

# --- Konfidenz: Gewichtung (weniger Signal = gedimmt/ausgegraut, kein „Fehler-Rot“) ---
def confidence_text_qcolor(confidence: float) -> QColor | None:
    c = float(confidence)
    if c >= 0.82:
        return None
    if c >= 0.55:
        out = QColor(TEXT_PRIMARY)
        out.setAlphaF(0.62)
        return out
    out = QColor(TEXT_MUTED)
    out.setAlphaF(0.9)
    return out


def graph_role_qcolor(role: str) -> QColor:
    h = GRAPH_ROLE_HEX.get(role, "#888888")
    return QColor(h)


def graph_edge_pen() -> QPen:
    p = QPen(QColor("#707070"))
    p.setWidthF(1.25)
    return p


def graph_edge_pen_highlight() -> QPen:
    p = QPen(QColor(ACCENT))
    p.setWidthF(2.25)
    return p


def graph_edge_pen_dim() -> QPen:
    c = QColor("#5a5a5a")
    c.setAlphaF(0.38)
    p = QPen(c)
    p.setWidthF(1.0)
    return p


def layer_cell_qcolor(layer: str) -> QColor | None:
    key = (layer or "").strip().lower()
    h = LAYER_CELL_BG_HEX.get(key)
    if not h:
        return None
    return QColor(h)


def kind_text_qcolor(kind: str) -> QColor | None:
    key = (kind or "").strip().lower()
    h = KIND_TEXT_HEX.get(key)
    if not h:
        return None
    return QColor(h)


def application_stylesheet() -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {BG_MAIN};
        color: {TEXT_PRIMARY};
    }}
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 4px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {TEXT_MUTED};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 4px 6px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QPushButton {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        border: 1px solid {BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {BG_HEADER};
    }}
    QTableView {{
        background-color: {BG_PANEL};
        alternate-background-color: {BG_MAIN};
        color: {TEXT_PRIMARY};
        gridline-color: {BORDER};
        border: 1px solid {BORDER};
        border-radius: 3px;
    }}
    QTableView::item:selected {{
        background-color: {ACCENT};
        color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {BG_HEADER};
        color: {TEXT_PRIMARY};
        padding: 6px;
        border: none;
        border-bottom: 2px solid {ACCENT};
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 3px;
        top: -1px;
        background-color: {BG_MAIN};
    }}
    QTabBar::tab {{
        background-color: {BG_HEADER};
        color: {TEXT_MUTED};
        padding: 6px 14px;
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
    }}
    QTextEdit, QPlainTextEdit {{
        background-color: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: 3px;
    }}
    QCheckBox {{
        color: {TEXT_PRIMARY};
    }}
    QLabel {{
        color: {TEXT_PRIMARY};
    }}
    QSplitter::handle {{
        background-color: {BORDER};
        width: 3px;
        height: 3px;
    }}
    QStatusBar {{
        background-color: {BG_HEADER};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER};
    }}
    """
