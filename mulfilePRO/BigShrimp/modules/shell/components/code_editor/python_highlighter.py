# -*- coding: utf-8 -*-
"""Shell：简易 Python 语法高亮。"""
import re

from PySide2.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del",
            "elif", "else", "except", "False", "finally", "for", "from", "global",
            "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or",
            "pass", "raise", "return", "True", "try", "while", "with", "yield",
            "self", "async", "await",
        ]
        for word in keywords:
            pattern = re.compile(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#A31515"))
        self.highlighting_rules.append(
            (re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), self.string_format)
        )
        self.highlighting_rules.append(
            (re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), self.string_format)
        )

        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#795E26"))
        function_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r"\bdef\s+(\w+)"), function_format))

        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#267F99"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r"\bclass\s+(\w+)"), class_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), comment_format))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))
        self.highlighting_rules.append((re.compile(r"\b\d+\b"), number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                if match.lastindex and match.lastindex > 0:
                    start = match.start(1)
                    end = match.end(1)
                self.setFormat(start, end - start, fmt)