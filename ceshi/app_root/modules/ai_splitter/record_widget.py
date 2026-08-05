# -*- coding:utf-8 -*-
import time
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QTextEdit, QLabel, QPushButton, QSplitter
)
from PySide2.QtCore import Qt


class AIRecordWidget(QWidget):
    """AI 响应历史记录器（Tab4）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []  # 存储 { 'text': str, 'is_error': bool, 'timestamp': float }
        self.init_ui()
        self._update_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(QLabel("📋 AI 响应历史（所有返回数据均记录在此）"))

        splitter = QSplitter(Qt.Vertical)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(QLabel("响应列表："))
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_item_selected)
        top_layout.addWidget(self.list_widget)
        splitter.addWidget(top_widget)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(QLabel("响应内容："))
        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        bottom_layout.addWidget(self.content_edit)
        splitter.addWidget(bottom_widget)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        btn_clear = QPushButton("清空所有记录")
        btn_clear.clicked.connect(self.clear_all)
        layout.addWidget(btn_clear)

    def append_record(self, text, is_error=False):
        record = {
            'text': text,
            'is_error': is_error,
            'timestamp': time.time()
        }
        self.records.append(record)
        self._update_list()

    def clear_all(self):
        self.records.clear()
        self._update_list()
        self.content_edit.clear()

    def _update_list(self):
        self.list_widget.clear()
        for idx, record in enumerate(self.records, start=1):
            time_str = time.strftime('%H:%M:%S', time.localtime(record['timestamp']))
            status = '❌ 错误' if record['is_error'] else '✅ 正常'
            display = f"#{idx}  {time_str}  {status}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, idx - 1)
            if record['is_error']:
                item.setForeground(Qt.red)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _on_item_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        if idx < len(self.records):
            record = self.records[idx]
            text = record['text']
            if record['is_error']:
                self.content_edit.setPlainText("⚠️ 该响应可能包含解析错误或异常信息\n\n" + text)
            else:
                self.content_edit.setPlainText(text)

    def check_and_add(self, text):
        is_error = self._check_error(text)
        self.append_record(text, is_error)

    def _check_error(self, text):
        error_keywords = ['错误', '失败', 'exception', 'error', '解析失败', '格式错误']
        text_lower = text.lower()
        for kw in error_keywords:
            if kw in text_lower:
                return True
        return False