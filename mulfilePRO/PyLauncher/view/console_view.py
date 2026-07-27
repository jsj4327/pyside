# -*- coding: utf-8 -*-

from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QGroupBox
from PySide2.QtGui import QTextCursor

class ConsoleView(QWidget):
    """终端控制台视图：独立展示子进程的标准输出与标准错误信息"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group_box = QGroupBox("实时控制台输出", self)
        group_layout = QVBoxLayout(group_box)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        # 浅色主题样式
        self.text_edit.setStyleSheet("background-color: #fafafa; color: #333333; font-family: Consolas, monospace; border: 1px solid #cccccc;")
        group_layout.addWidget(self.text_edit)

        tool_layout = QHBoxLayout()
        tool_layout.addStretch()
        
        self.btn_clear = QPushButton("清空控制台", self)
        self.btn_clear.clicked.connect(self.text_edit.clear)
        tool_layout.addWidget(self.btn_clear)

        group_layout.addLayout(tool_layout)
        layout.addWidget(group_box)

    def append_log(self, text):
        self.text_edit.insertPlainText(text)
        # 【已修复】正确的枚举值是 QTextCursor.End
        self.text_edit.moveCursor(QTextCursor.End)