from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsView, QGraphicsLineItem

class FocusGraphView(QGraphicsView):
    """Fixes Layout: Mitte = selection, links = callers, rechts = callees — nicht mehr."""

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(220)

    def set_from_layout(self, layout: dict[str, Any] | None) -> None:
        self._scene.clear()
        if not layout or not layout.get("nodes"):
            return

        nodes: list[dict[str, str]] = layout["nodes"]
        edges: list[dict[str, str]] = layout.get("edges", [])

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

        pen_edge = QPen(QColor(100, 100, 100))
        for e in edges:
            p0 = pos.get(e["from"])
            p1 = pos.get(e["to"])
            if p0 and p1:
                line = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
                line.setPen(pen_edge)
                self._scene.addItem(line)

        colors = {
            "center": QColor(80, 120, 200),
            "caller": QColor(120, 160, 120),
            "callee": QColor(180, 140, 100),
        }
        r = 38.0
        for n in nodes:
            p = pos.get(n["id"])
            if not p:
                continue
            role = n.get("role", "center")
            ellipse = QGraphicsEllipseItem(p.x() - r, p.y() - r, 2 * r, 2 * r)
            ellipse.setBrush(QBrush(colors.get(role, QColor(150, 150, 150))))
            ellipse.setPen(QPen(Qt.GlobalColor.black))
            self._scene.addItem(ellipse)
            # Label via simple tooltip on scene — ohne QGraphicsTextItem-Import-Komplexität
            ellipse.setToolTip(f"{n.get('label', n['id'])}\n({role})")

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
