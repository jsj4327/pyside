# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusView(QWidget):
    """文件浏览器状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#666;font-size:11px;")

        self.file_count_label = QLabel("")
        self.file_count_label.setStyleSheet("color:#666;font-size:11px;")

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.file_count_label)

    def update_status(self, message):
        self.status_label.setText(message)

    def update_path(self, path):
        self.update_status(f"当前目录: {path}")

    def update_file_count(self, dirs, files):
        self.file_count_label.setText(f"📁 {dirs} 个目录 | 📄 {files} 个文件")