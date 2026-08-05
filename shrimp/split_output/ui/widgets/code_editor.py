# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QTextEdit
from utils.syntax_highlighter import PythonSyntaxHighlighter


class CodeEditor(QTextEdit):
    """带Python语法高亮的代码编辑器组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #fafafa;"
        )
        self.highlighter = PythonSyntaxHighlighter(self.document())
