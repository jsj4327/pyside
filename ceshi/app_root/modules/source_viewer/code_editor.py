# -*- coding:utf-8 -*-
import re
from PySide2.QtWidgets import QPlainTextEdit, QWidget
from PySide2.QtCore import Qt, QRect, QSize
from PySide2.QtGui import (
    QColor, QPainter, QTextCharFormat, QTextCursor,
    QFont, QSyntaxHighlighter
)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(50)

    def sizeHint(self):
        return QSize(50, self.editor.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(245, 245, 245))
        painter.setPen(QColor(220, 220, 220))
        painter.drawLine(self.width() - 1, event.rect().top(),
                         self.width() - 1, event.rect().bottom())

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(120, 120, 120))
                painter.drawText(0, int(top), 42, self.editor.fontMetrics().height(),
                                 Qt.AlignRight, str(block_number + 1))
            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
            'while', 'for', 'in', 'try', 'except', 'with', 'as', 'lambda',
            'True', 'False', 'None', 'and', 'or', 'not', 'pass', 'break', 'continue'
        ]
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((re.compile(pattern), keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((re.compile(r'".*?"|\'.*?\''), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'#.*$'), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)

        self.highlighter = PythonHighlighter(self.document())

        self.blockCountChanged.connect(self.update_line_number_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_width()

    def update_line_number_width(self):
        self.setViewportMargins(50, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), 50, cr.height()))

    def set_plain_text(self, text):
        self.setPlainText(text)
        self.update_line_number_width()
        self.moveCursor(QTextCursor.Start)