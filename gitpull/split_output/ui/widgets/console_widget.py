from PySide2.QtWidgets import QPlainTextEdit
from PySide2.QtGui import QTextCursor, QColor, QTextCharFormat


class ConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;"
        )

    def log(self, text: str, hex_color: str):
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.ensureCursorVisible()
