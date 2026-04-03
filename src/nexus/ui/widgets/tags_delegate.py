from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFontMetrics, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from nexus.ui import theme


class TagsChipDelegate(QStyledItemDelegate):
    """Tags-Spalte: kleine „Chips“ statt Komma-String (Lesbarkeit)."""

    TAGS_LIST_ROLE = Qt.ItemDataRole.UserRole + 20

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        tags = index.data(self.TAGS_LIST_ROLE)
        if not isinstance(tags, list) or not tags:
            super().paint(painter, option, index)
            return

        painter.save()
        pal = theme.ui_palette()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            fg = option.palette.color(option.palette.ColorRole.HighlightedText)
        else:
            fg = QColor(pal.text_primary)

        fm = QFontMetrics(option.font)
        x = option.rect.x() + 4
        cy = option.rect.center().y()
        for tag in tags[:5]:
            label = str(tag)
            chip_w = fm.horizontalAdvance(label) + 10
            chip_h = min(20, option.rect.height() - 4)
            y = cy - chip_h // 2
            rect = QRect(x, y, chip_w, chip_h)
            painter.setPen(QColor(pal.border))
            painter.setBrush(QColor(pal.bg_header))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(fg)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            x += chip_w + 4
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        tags = index.data(self.TAGS_LIST_ROLE)
        if not isinstance(tags, list) or not tags:
            return super().sizeHint(option, index)
        fm = QFontMetrics(option.font)
        w = 8
        for tag in tags[:5]:
            w += fm.horizontalAdvance(str(tag)) + 10 + 4
        return QSize(max(w, 32), max(22, fm.height() + 8))
