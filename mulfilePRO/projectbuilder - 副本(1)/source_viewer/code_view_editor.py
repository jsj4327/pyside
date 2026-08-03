"""
带行号及轻量级语法高亮的源码编辑器
"""

from PySide2.QtWidgets import QWidget, QPlainTextEdit
from PySide2.QtCore import Qt, QRect, QSize, Signal
from PySide2.QtGui import (
    QColor, QPainter, QTextCharFormat, QTextCursor,
    QFont, QSyntaxHighlighter, QKeyEvent
)


class PythonHighlighter(QSyntaxHighlighter):
    """简易 Python 语法高亮器（可扩展）"""
    def __init__(self, document, ext=".py"):
        super().__init__(document)
        self.ext = ext.lower()
        self.highlighting_rules = []

        # 关键字格式
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
            'while', 'for', 'in', 'try', 'except', 'with', 'as', 'lambda',
            'True', 'False', 'None', 'and', 'or', 'not', 'pass', 'break', 'continue'
        ]
        if self.ext in ['.cpp', '.c', '.java', '.js', '.ts']:
            keywords = ['class', 'struct', 'return', 'if', 'else', 'while', 'for', 'int', 'void', 'float', 'double', 'char', 'public', 'private', 'static']

        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((re_compile_pattern(pattern), keyword_format))

        # 字符串格式
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((re_compile_pattern(r'".*?"|\'.*?\''), self.string_format))

        # 注释格式
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#808080"))
        self.comment_format.setFontItalic(True)
        comment_pattern = r'#.*$' if self.ext == '.py' else r'//.*$'
        self.highlighting_rules.append((re_compile_pattern(comment_pattern), self.comment_format))

    def highlightBlock(self, text):
        import re
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


def re_compile_pattern(pattern):
    import re
    return re.compile(pattern)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(50)

    def sizeHint(self):
        return QSize(50, self.editor.height())

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeViewEditor(QPlainTextEdit):
    """源码编辑器，带有左侧行号及快捷键支持"""

    # 定义保存信号
    saved = Signal(str)

    def __init__(self, parent=None, ext=".py"):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        self.setReadOnly(False)
        self.setUndoRedoEnabled(True)  # 开启原生撤销恢复队列

        self.highlighter = PythonHighlighter(self.document(), ext)

        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_width()

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                selection-background-color: #add6ff;
                border: none;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent):
        """只显式拦截 Ctrl+S，Ctrl+Z 交由原生处理以保证撤回栈正常运作"""
        modifiers = event.modifiers()
        
        # 监听 Ctrl + S (保存)
        if modifiers == Qt.ControlModifier and event.key() == Qt.Key_S:
            self.saved.emit(self.toPlainText())
            event.accept()
            return

        super().keyPressEvent(event)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))

        painter.setPen(QColor(220, 220, 220))
        painter.drawLine(self.line_number_area.width() - 1, event.rect().top(),
                        self.line_number_area.width() - 1, event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = block_number + 1
                painter.setPen(QColor(120, 120, 120))
                painter.setFont(self.font())
                painter.drawText(0, int(top), 42, self.fontMetrics().height(),
                                Qt.AlignRight, str(number))

            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    def _update_line_number_width(self):
        self.setViewportMargins(50, 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), 50, cr.height()))

    def jump_to_line(self, line_number: int):
        """跳转并高亮目标行"""
        self.verticalScrollBar().setValue(0)
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()

        cursor.select(QTextCursor.LineUnderCursor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 100))
        cursor.setCharFormat(fmt)