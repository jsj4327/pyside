#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide2.QtWidgets import QPlainTextEdit
from PySide2.QtGui import QFont, QTextCursor

class ConsoleWidget(QPlainTextEdit):
    """带自动滚动和行数限制的控制台组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setMaximumBlockCount(1500)  # 防止日志无限膨胀导致内存溢出
        self.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: none;")

    def append_output(self, text: str, is_error: bool = False):
        """追加输出内容"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        # 错误日志使用浅红色区分
        if is_error:
            self.appendHtml(f"<span style='color: #f44747;'>[错误] {text}</span>")
        else:
            self.insertPlainText(text)
        
        self.moveCursor(QTextCursor.End)