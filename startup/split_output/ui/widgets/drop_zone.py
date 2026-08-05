from PySide2.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide2.QtCore import Qt, Signal, QMimeData
from PySide2.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent
import os
from utils.path_utils import validate_file_extension

class DropZone(QFrame):
    """通用拖放接收区域"""
    pathDropped = Signal(str)

    def __init__(self, hint_text: str, accept_mode: str = "all", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(200, 110)
        self.hint_text = hint_text
        self.accept_mode = accept_mode
        self.current_path = None

        self._default_style = """
            DropZone {
                border: 2px dashed rgba(255,255,255,0.2);
                border-radius: 12px;
                background-color: rgba(255,255,255,0.03);
            }
        """
        self._hover_style = """
            DropZone {
                border: 2px dashed #3B82F6;
                border-radius: 12px;
                background-color: rgba(59,130,246,0.08);
            }
        """
        self.setStyleSheet(self._default_style)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        self.preview_label = QLabel(hint_text)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFont(QFont("Noto Sans CJK SC", 10))
        self.preview_label.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMinimumHeight(80)
        layout.addWidget(self.preview_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and self._is_valid(event.mimeData()):
            event.acceptProposedAction()
            self.setStyleSheet(self._hover_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._default_style)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self._default_style)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._validate(path):
                self.current_path = path
                self._update_preview(path)
                self.pathDropped.emit(path)

    def _is_valid(self, mime: QMimeData) -> bool:
        urls = mime.urls()
        if not urls:
            return False
        path = urls[0].toLocalFile()
        return self._validate(path)

    def _validate(self, path: str) -> bool:
        return validate_file_extension(path, self.accept_mode)

    def _update_preview(self, path: str):
        name = os.path.basename(path)
        if self.accept_mode == "image":
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                available_width = self.width() - 20
                available_height = self.height() - 20
                scaled_pixmap = pixmap.scaled(
                    available_width,
                    available_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                self.preview_label.setStyleSheet("background: transparent; border: none;")
            else:
                self.preview_label.setText(f"⚠️ 无法加载: {name}")
                self.preview_label.setStyleSheet("color: #F87171; background: transparent;")
        else:
            self.preview_label.clear()
            self.preview_label.setText(f"✅ {name}")
            self.preview_label.setStyleSheet("color: #4ADE80; background: transparent; font-weight: bold;")
