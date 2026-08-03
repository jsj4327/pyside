# -*- coding: utf-8 -*-

"""
顶部搜索栏组件
"""

from PySide2.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PySide2.QtCore import Signal


class SearchBar(QWidget):
    """源码搜索栏"""
    search_triggered = Signal(str)
    next_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addWidget(QLabel("🔍 搜索:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字回车查找...")
        self.search_input.returnPressed.connect(lambda: self.search_triggered.emit(self.search_input.text()))
        layout.addWidget(self.search_input)

        self.btn_find = QPushButton("查找")
        self.btn_find.clicked.connect(lambda: self.search_triggered.emit(self.search_input.text()))
        layout.addWidget(self.btn_find)

        self.setStyleSheet("""
            QWidget { background: #f8f9fa; border-bottom: 1px solid #e0e0e0; }
            QLineEdit { background: white; border: 1px solid #ccc; border-radius: 3px; padding: 2px 5px; }
            QPushButton { padding: 3px 10px; background: #e0e0e0; border: none; border-radius: 3px; }
            QPushButton:hover { background: #d0d0d0; }
        """)