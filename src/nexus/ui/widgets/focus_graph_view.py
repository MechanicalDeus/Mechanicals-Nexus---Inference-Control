from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, QPropertyAnimation, Qt, QEasingCurve
from PyQt6.QtGui import QBrush, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsOpacityEffect,
    QGraphicsScene,
    QGraphicsView,
)

from nexus.ui import theme


class FocusGraphView(QGraphicsView):
    """Mitte = Auswahl, links = callers, rechts = callees; Fokus = Center + Kanten, Nachbarn gedimmt."""

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(220)
        self._fade_anim: QPropertyAnimation | None = None

    def set_from_layout(self, layout: dict[str, Any] | None, *, animate: bool = True) -> None:
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        self.setGraphicsEffect(None)

        self._scene.clear()
        if not layout or not layout.get("nodes"):
            return

        nodes: list[dict[str, str]] = layout["nodes"]
        edges: list[dict[str, str]] = layout.get("edges", [])

        center_id: str | None = None
        for n in nodes:
            if n.get("role") == "center":
                center_id = n["id"]
                break

        x_by_role = {"caller": -220.0, "center": 0.0, "callee": 220.0}
        pos: dict[str, QPointF] = {}
        role_counts: dict[str, int] = {}

        for n in nodes:
            role = n.get("role", "center")
            i = role_counts.get(role, 0)
            role_counts[role] = i + 1
            x = x_by_role.get(role, 0.0)
            y = (i - role_counts[role] / 2.0) * 70.0
            pos[n["id"]] = QPointF(x, y)

        for e in edges:
            p0 = pos.get(e["from"])
            p1 = pos.get(e["to"])
            if not p0 or not p1:
                continue
            touches_center = bool(
                center_id and (e["from"] == center_id or e["to"] == center_id)
            )
            pen = theme.graph_edge_pen_highlight() if touches_center else theme.graph_edge_pen_dim()
            line = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
            line.setPen(pen)
            self._scene.addItem(line)

        r = 38.0
        for n in nodes:
            p = pos.get(n["id"])
            if not p:
                continue
            role = n.get("role", "center")
            ellipse = QGraphicsEllipseItem(p.x() - r, p.y() - r, 2 * r, 2 * r)
            ellipse.setBrush(QBrush(theme.graph_role_qcolor(role)))
            ellipse.setPen(theme.graph_node_outline_pen())
            if role != "center":
                ellipse.setOpacity(0.55)
            self._scene.addItem(ellipse)
            ellipse.setToolTip(f"{n.get('label', n['id'])}\n({role})")

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._run_fade_in(animate)

    def _run_fade_in(self, animate: bool) -> None:
        if not animate:
            return
        eff = QGraphicsOpacityEffect(self)
        eff.setOpacity(0.0)
        self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(80)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim = anim
        anim.start()
