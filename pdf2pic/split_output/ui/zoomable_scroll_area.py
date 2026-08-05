""" 可缩放与连续滚动的 ScrollArea 完整版 保留完整的缩放、平移、连续多页显示及安全防崩溃保护机制。 """

from PySide2.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel
from PySide2.QtCore import Qt, Signal, QPoint, QTimer
from PySide2.QtGui import QWheelEvent, QPixmap, QMouseEvent


class ZoomableScrollArea(QScrollArea):
    """支持连续页面显示、完整缩放、拖拽平移和安全滚轮交互的滚动区域"""
    # 页面视口切换信号
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        # 内部容器与布局
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(15)
        self.setWidget(self.content_widget)

        self._page_labels = []
        self._original_pixmaps = []
        self.continuous_mode = False
        self.zoom_factor = 1.0  # 默认缩放比例

        # 拖拽平移支持变量
        self._dragging = False
        self._drag_start_pos = QPoint()

        # 默认占位标签
        self.image_label = QLabel("在此处预览页面大图")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.image_label)
        self._page_labels.append(self.image_label)

        # 安全绑定滚动条信号
        self.verticalScrollBar().valueChanged.connect(self._safe_on_scroll_value_changed)

    def set_continuous_pages(self, pixmaps: list, target_index: int = None):
        """
        安全地设置连续多页预览并应用当前缩放比例
        :param pixmaps: 图片列表
        :param target_index: (可选) 指定旋转后滚动到第几页，修复旋转后位置丢失问题
        """
        self.blockSignals(True)
        self._original_pixmaps = pixmaps
        self.continuous_mode = bool(pixmaps)

        # 安全清理旧的 Label 控件
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._page_labels.clear()

        if not pixmaps:
            self.image_label = QLabel("在此处预览页面大图")
            self.image_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(self.image_label)
            self._page_labels.append(self.image_label)
            self.blockSignals(False)
            return

        # 批量创建页面标签
        for pixmap in pixmaps:
            lbl = QLabel()
            scaled_pixmap = self._scale_pixmap(pixmap)
            lbl.setPixmap(scaled_pixmap)
            lbl.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(lbl)
            self._page_labels.append(lbl)

        self.blockSignals(False)

        # 智能定位逻辑：如果不为空，尝试滚动到指定页面
        if target_index is not None and 0 <= target_index < len(self._page_labels):
            # 使用 QTimer.singleShot 确保在布局更新完毕后再滚动，防止滚偏
            QTimer.singleShot(0, lambda: self._scroll_to_index(target_index))
        else:
            # 如果没有指定索引，默认回到顶部
            self.verticalScrollBar().setValue(0)

    def _scroll_to_index(self, index: int):
        """内部辅助方法：滚动到指定索引的 Label 顶部或居中"""
        if 0 <= index < len(self._page_labels):
            target_label = self._page_labels[index]
            # 获取该 Label 在垂直方向的绝对坐标
            y = target_label.y()
            bar = self.verticalScrollBar()
            viewport_h = self.viewport().height()
            label_h = target_label.height()
            
            # 计算目标滚动值：让该 Label 居中
            scroll_target = y - (viewport_h - label_h) // 2
            bar.setValue(max(bar.minimum(), min(bar.maximum(), scroll_target)))

    def set_pixmap(self, pixmap: QPixmap):
        """设置单张大图预览并应用当前缩放比例"""
        self.blockSignals(True)
        self.continuous_mode = False
        self._original_pixmaps = [pixmap]

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._page_labels.clear()

        self.image_label = QLabel()
        scaled_pixmap = self._scale_pixmap(pixmap)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.image_label)
        self._page_labels.append(self.image_label)
        self.blockSignals(False)

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """根据当前 zoom_factor 缩放 QPixmap"""
        if pixmap.isNull() or self.zoom_factor == 1.0:
            return pixmap
        new_w = int(pixmap.width() * self.zoom_factor)
        new_h = int(pixmap.height() * self.zoom_factor)
        return pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def zoom_in(self):
        """放大图像"""
        if self._original_pixmaps:
            self.zoom_factor = min(3.0, self.zoom_factor + 0.15)
            self._refresh_view()

    def zoom_out(self):
        """缩小图像"""
        if self._original_pixmaps:
            self.zoom_factor = max(0.2, self.zoom_factor - 0.15)
            self._refresh_view()

    def reset_zoom(self):
        """重置缩放比例"""
        if self._original_pixmaps:
            self.zoom_factor = 1.0
            self._refresh_view()

    def fit_to_width(self):
        """自动缩放以适应窗口宽度（新增功能）"""
        if not self._original_pixmaps:
            return
        
        # 找出所有图片中最宽的一张
        max_width = 0
        for pixmap in self._original_pixmaps:
            if pixmap.width() > max_width:
                max_width = pixmap.width()
        
        if max_width == 0:
            return

        # 获取视口可用宽度（减去一点边距防止贴边）
        viewport_width = self.viewport().width() - 20
        
        # 计算缩放比例
        target_zoom = viewport_width / max_width
        
        # 应用新的缩放比例，限制在合理范围内
        self.zoom_factor = max(0.1, min(5.0, target_zoom))
        self._refresh_view()

    def _refresh_view(self):
        """刷新当前视图以应用缩放修改"""
        if not self._original_pixmaps:
            return
        if self.continuous_mode:
            self.set_continuous_pages(self._original_pixmaps)
        else:
            if len(self._original_pixmaps) == 1:
                self.set_pixmap(self._original_pixmaps[0])

    def wheelEvent(self, event: QWheelEvent):
        """重写滚轮事件：支持 Ctrl+滚轮缩放，普通滚轮安全滚动，防止段错误"""
        try:
            if event.modifiers() == Qt.ControlModifier:
                angle = event.angleDelta().y()
                if angle > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                event.accept()
            else:
                super().wheelEvent(event)
        except Exception:
            pass

    def mousePressEvent(self, event: QMouseEvent):
        """支持鼠标中键或 Alt+左键拖拽平移"""
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() == Qt.AltModifier):
            self._dragging = True
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """处理拖拽平移过程"""
        if self._dragging:
            delta = event.pos() - self._drag_start_pos
            self._drag_start_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """结束拖拽平移"""
        if self._dragging:
            self._dragging = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _safe_on_scroll_value_changed(self, value: int):
        """安全计算当前可见页面索引，防止野指针及段错误"""
        if not self.continuous_mode or not self._page_labels:
            return
        try:
            scroll_pos = self.verticalScrollBar().value()
            cumulative_height = 0
            for i, lbl in enumerate(self._page_labels):
                if not lbl or not isinstance(lbl, QLabel):
                    continue
                h = lbl.height()
                if scroll_pos <= cumulative_height + h // 2:
                    self.page_changed.emit(i)
                    break
                cumulative_height += h + self.content_layout.spacing()
        except RuntimeError:
            pass
        except Exception:
            pass
