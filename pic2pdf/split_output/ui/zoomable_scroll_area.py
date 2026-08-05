"""可缩放拖拽的图片预览滚动区域控件"""
from PySide2.QtWidgets import QScrollArea, QLabel
from PySide2.QtCore import Qt, QPoint
from PySide2.QtGui import QPixmap, QWheelEvent, QMouseEvent, QTransform
from config.constants import MIN_SCALE, MAX_SCALE, ZOOM_FACTOR


class ZoomableScrollArea(QScrollArea):
    """支持滚轮缩放、边界限制、鼠标左键拖拽平移及旋转的图片预览滚动区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_label = QLabel("在此处预览大图")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ccc; color: #666;"
        )
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)

        self.original_pixmap = QPixmap()
        self.scale_factor = 1.0
        self.rotation_angle = 0  # 旋转角度，仅支持90度倍数
        self.min_scale = MIN_SCALE
        self.max_scale = MAX_SCALE

        # 拖拽平移相关变量
        self.is_dragging = False
        self.drag_start_pos = QPoint()

    def set_pixmap(self, pixmap: QPixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.update_image_display()

    def rotate_image(self, angle: int):
        """旋转图片，angle应为90的倍数"""
        if self.original_pixmap.isNull():
            return
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.update_image_display()

    def update_image_display(self):
        if self.original_pixmap.isNull():
            return
        
        # 先应用旋转
        transform = QTransform()
        transform.rotate(self.rotation_angle)
        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # 再应用缩放
        new_width = int(rotated_pixmap.width() * self.scale_factor)
        new_height = int(rotated_pixmap.height() * self.scale_factor)
        scaled_pixmap = rotated_pixmap.scaled(
            new_width, new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def wheelEvent(self, event: QWheelEvent):
        if self.original_pixmap.isNull():
            return
        angle = event.angleDelta().y()
        if angle == 0:
            return
        factor = ZOOM_FACTOR if angle > 0 else 1.0 / ZOOM_FACTOR
        new_scale = self.scale_factor * factor
        new_scale = max(self.min_scale, min(new_scale, self.max_scale))
        if new_scale != self.scale_factor:
            self.scale_factor = new_scale
            self.update_image_display()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and not self.original_pixmap.isNull():
            self.is_dragging = True
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and not self.original_pixmap.isNull():
            delta = event.pos() - self.drag_start_pos
            self.drag_start_pos = event.pos()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)