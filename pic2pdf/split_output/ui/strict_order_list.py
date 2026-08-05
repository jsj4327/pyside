"""支持严格纵向拖拽排序的缩略图列表控件"""
from PySide2.QtWidgets import QListWidget, QListWidgetItem
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QPainter, QPen, QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent
from config.constants import (
    THUMBNAIL_ICON_SIZE, THUMBNAIL_SPACING,
    DRAG_SCROLL_MARGIN, DRAG_SCROLL_SPEED
)


class StrictOrderListWidget(QListWidget):
    """自定义的 QListWidget，严格锁定单列纵向拖放，支持多选"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ListMode)
        self.setFlow(QListWidget.TopToBottom)
        self.setMovement(QListWidget.Free)

        self.setIconSize(QSize(THUMBNAIL_ICON_SIZE, THUMBNAIL_ICON_SIZE))
        self.setSpacing(THUMBNAIL_SPACING)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDropIndicatorShown(False)
        self.setSelectionMode(QListWidget.ExtendedSelection)

        self.dragging_row = -1
        self.drop_indicator_row = -1

    def startDrag(self, supportedActions):
        selected = self.selectedItems()
        if selected:
            self.dragging_row = self.row(selected[0])
        super().startDrag(supportedActions)
        self.dragging_row = -1
        self.drop_indicator_row = -1
        self.viewport().update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.source() == self:
            pos = event.pos()
            scrollbar = self.verticalScrollBar()
            if pos.y() < DRAG_SCROLL_MARGIN:
                scrollbar.setValue(scrollbar.value() - DRAG_SCROLL_SPEED)
            elif pos.y() > self.viewport().height() - DRAG_SCROLL_MARGIN:
                scrollbar.setValue(scrollbar.value() + DRAG_SCROLL_SPEED)

            constrained_x = self.viewport().width() // 2
            constrained_pos = pos
            constrained_pos.setX(constrained_x)

            item = self.itemAt(constrained_pos)
            if item:
                rect = self.visualItemRect(item)
                relative_y = constrained_pos.y() - rect.top()

                if rect.height() * 0.3 <= relative_y <= rect.height() * 0.7:
                    self.drop_indicator_row = -1
                    event.ignore()
                    self.viewport().update()
                    return

                row = self.row(item)
                if relative_y < rect.height() * 0.3:
                    self.drop_indicator_row = row
                else:
                    self.drop_indicator_row = row + 1
            else:
                if constrained_pos.y() < 0:
                    self.drop_indicator_row = 0
                else:
                    self.drop_indicator_row = self.count()

            event.acceptProposedAction()
            self.viewport().update()
        else:
            event.ignore()

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.dragging_row != -1:
            self.viewport().update()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.drop_indicator_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.source() == self:
            target_row = self.drop_indicator_row
            selected_items = self.selectedItems()
            if not selected_items:
                event.ignore()
                return

            source_item = selected_items[0]
            source_row = self.row(source_item)

            if target_row == -1:
                event.ignore()
                return

            if source_row < target_row:
                target_row -= 1

            taken_item = self.takeItem(source_row)
            self.insertItem(target_row, taken_item)

            self.setCurrentItem(taken_item)
            self.dragging_row = -1
            self.drop_indicator_row = -1

            event.accept()
            self.clearSelection()
            self.viewport().update()
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dragging_row != -1 and self.dragging_row < self.count():
            item = self.item(self.dragging_row)
            rect = self.visualItemRect(item)
            if rect.isValid():
                painter = QPainter(self.viewport())
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.fillRect(rect, QColor(255, 255, 255, 160))
                painter.end()

        if self.drop_indicator_row != -1:
            painter = QPainter(self.viewport())
            pen = QPen(QColor(0, 120, 215), 3, Qt.SolidLine)
            painter.setPen(pen)

            y_pos = 0
            if self.drop_indicator_row < self.count():
                item = self.item(self.drop_indicator_row)
                rect = self.visualItemRect(item)
                if rect.isValid():
                    y_pos = rect.top() - 3
            else:
                if self.count() > 0:
                    last_item = self.item(self.count() - 1)
                    rect = self.visualItemRect(last_item)
                    if rect.isValid():
                        y_pos = rect.bottom() + 3

            if y_pos != 0:
                painter.drawLine(10, y_pos, self.viewport().width() - 10, y_pos)
            painter.end()