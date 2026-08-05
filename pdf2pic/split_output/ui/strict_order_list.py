"""
严格纵向拖放排序的缩略图列表组件。
"""
from PySide2.QtWidgets import QListWidget
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QPainter, QPen, QColor, QWheelEvent

from config import THUMBNAIL_SIZE, DRAG_SCROLL_MARGIN, DRAG_SCROLL_SPEED


class StrictOrderListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ListMode)
        self.setFlow(QListWidget.TopToBottom)
        self.setMovement(QListWidget.Free)

        self.setIconSize(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        self.setSpacing(5)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDropIndicatorShown(False)
        self.setSelectionMode(QListWidget.ExtendedSelection)

        self._dragging_row = -1
        self._drop_indicator_row = -1

    def startDrag(self, supportedActions):
        selected = self.selectedItems()
        if selected:
            self._dragging_row = self.row(selected[0])
        super().startDrag(supportedActions)
        self._dragging_row = -1
        self._drop_indicator_row = -1
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() != self:
            event.ignore()
            return

        pos = event.pos()

        sb = self.verticalScrollBar()
        if pos.y() < DRAG_SCROLL_MARGIN:
            sb.setValue(sb.value() - DRAG_SCROLL_SPEED)
        elif pos.y() > self.viewport().height() - DRAG_SCROLL_MARGIN:
            sb.setValue(sb.value() + DRAG_SCROLL_SPEED)

        constrained_pos = pos
        constrained_pos.setX(self.viewport().width() // 2)

        item = self.itemAt(constrained_pos)
        if item:
            rect = self.visualItemRect(item)
            rel_y = constrained_pos.y() - rect.top()
            h = rect.height()

            if h * 0.3 <= rel_y <= h * 0.7:
                self._drop_indicator_row = -1
                event.ignore()
                self.viewport().update()
                return

            row = self.row(item)
            self._drop_indicator_row = row if rel_y < h * 0.3 else row + 1
        else:
            self._drop_indicator_row = 0 if constrained_pos.y() < 0 else self.count()

        event.acceptProposedAction()
        self.viewport().update()

    def dragLeaveEvent(self, event):
        self._drop_indicator_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.source() != self:
            event.ignore()
            return

        target = self._drop_indicator_row
        selected = self.selectedItems()
        if not selected or target == -1:
            event.ignore()
            return

        src_item = selected[0]
        src_row = self.row(src_item)

        if src_row < target:
            target -= 1

        taken = self.takeItem(src_row)
        self.insertItem(target, taken)
        self.setCurrentItem(taken)

        self._dragging_row = -1
        self._drop_indicator_row = -1
        event.accept()
        self.clearSelection()
        self.viewport().update()

    def wheelEvent(self, event: QWheelEvent):
        super().wheelEvent(event)
        if self._dragging_row != -1:
            self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        try:
            if self._dragging_row != -1 and self._dragging_row < self.count():
                item = self.item(self._dragging_row)
                rect = self.visualItemRect(item)
                if rect.isValid():
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.fillRect(rect, QColor(255, 255, 255, 160))

            if self._drop_indicator_row != -1:
                painter.setPen(QPen(QColor(0, 120, 215), 3, Qt.SolidLine))
                y = 0
                if self._drop_indicator_row < self.count():
                    r = self.visualItemRect(self.item(self._drop_indicator_row))
                    if r.isValid():
                        y = r.top() - 3
                elif self.count() > 0:
                    r = self.visualItemRect(self.item(self.count() - 1))
                    if r.isValid():
                        y = r.bottom() + 3
                
                if y:
                    painter.drawLine(10, y, self.viewport().width() - 10, y)
        finally:
            painter.end()