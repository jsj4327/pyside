# -*- coding: utf-8 -*-

from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSplitter, QPlainTextEdit, QTextEdit
)
from PySide2.QtCore import Qt, Signal, QRect, QSize, QRegExp
from PySide2.QtGui import (
    QFont, QTextCursor, QSyntaxHighlighter, QTextCharFormat,
    QColor, QPainter, QPixmap, QIcon, QTextFormat
)


# ==================== 1. Python 语法高亮器 ====================
class PythonHighlighter(QSyntaxHighlighter):
    """Python 语法高亮组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 关键字格式 (蓝色 + 加粗)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)

        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "None", "nonlocal", "not", "or", "pass", "raise", "return",
            "True", "try", "while", "with", "yield"
        ]

        for kw in keywords:
            pattern = QRegExp(r"\b" + kw + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # 类定义格式 (青蓝色)
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#2B91AF"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"), class_format))

        # 函数定义格式 (棕金色)
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#74531F"))
        func_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"), func_format))

        # 字符串格式 (深红色)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#A31515"))
        self.highlighting_rules.append((QRegExp(r'".*?"'), string_format))
        self.highlighting_rules.append((QRegExp(r"'.*?'"), string_format))

        # 注释格式 (深绿色)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((QRegExp(r"#.*"), comment_format))

        # 数字格式 (绿色)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))
        self.highlighting_rules.append((QRegExp(r"\b\d+\b"), number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)


# ==================== 2. 带行号区域的代码编辑器 ====================
class LineNumberArea(QWidget):
    """用于绘制代码行号的侧边栏组件"""

    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """具有行号显示和高亮扩展能力的编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#888888"))
                painter.setFont(self.font())
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())


# ==================== 3. 主源码编辑器视图 ====================
class SourceEditorView(QWidget):
    """高级源码浏览与编辑器视图"""

    save_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(self.splitter)

        # ========== 左侧：代码编辑主区域 ==========
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        toolbar_layout = QHBoxLayout()
        self.lbl_file_path = QLabel("未打开文件", self)
        self.lbl_file_path.setStyleSheet("font-weight: bold; color: #555555;")
        toolbar_layout.addWidget(self.lbl_file_path)

        toolbar_layout.addStretch()

        self.btn_save = QPushButton("保存源码 (Ctrl+S)", self)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(lambda: self.save_requested.emit(self.editor.toPlainText()))
        toolbar_layout.addWidget(self.btn_save)

        editor_layout.addLayout(toolbar_layout)

        # 创建带行号的代码编辑器
        self.editor = CodeEditor(self)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("background-color: #fafafa; color: #333333; border: 1px solid #cccccc;")
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(lambda: self.btn_save.setEnabled(True))
        
        # 挂载语法高亮器
        self.highlighter = PythonHighlighter(self.editor.document())

        editor_layout.addWidget(self.editor)
        self.splitter.addWidget(editor_widget)

        # ========== 右侧：代码结构大纲区域 ==========
        outline_widget = QWidget()
        outline_layout = QVBoxLayout(outline_widget)
        outline_layout.setContentsMargins(0, 0, 0, 0)

        outline_layout.addWidget(QLabel("代码大纲 (类与函数):"))

        self.outline_list = QListWidget(self)
        self.outline_list.itemDoubleClicked.connect(self._jump_to_line)
        outline_layout.addWidget(self.outline_list)

        self.splitter.addWidget(outline_widget)
        self.splitter.setSizes([750, 210])

    def update_editor_content(self, file_path, content):
        """更新编辑器文件内容"""
        self.lbl_file_path.setText(file_path)
        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self.btn_save.setEnabled(False)

    def update_outline(self, symbols):
        """更新大纲树列表，生成红色 C 与蓝色 F 图标"""
        self.outline_list.clear()

        # 生成红色 C 和蓝色 F 图标
        icon_c = self._create_letter_icon("C", "#E53935")
        icon_f = self._create_letter_icon("F", "#1E88E5")

        for sym in symbols:
            is_class = (sym["type"] == "class")
            icon = icon_c if is_class else icon_f
            
            item_text = f" {sym['name']} (行 {sym['lineno']})"
            item = QListWidgetItem(icon, item_text)
            item.setData(Qt.UserRole, sym["lineno"])
            self.outline_list.addItem(item)

    def _create_letter_icon(self, letter, color_hex):
        """动态绘制字符图标：红色 C 字母与蓝色 F 字母"""
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景圆角徽章
        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 18, 18, 4, 4)

        # 绘制白色大写字母
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, letter)
        painter.end()

        return QIcon(pixmap)

    def _jump_to_line(self, item):
        """大纲双击跳转：滚动到对应行并设置黄色背景高亮"""
        lineno = item.data(Qt.UserRole)
        if lineno:
            block = self.editor.document().findBlockByNumber(lineno - 1)
            cursor = QTextCursor(block)
            self.editor.setTextCursor(cursor)
            self.editor.setFocus()

            # 设置整行黄色高亮样式
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#FFF2A8"))  # 明亮浅黄色
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = cursor
            selection.cursor.clearSelection()

            # 应用当前选区高亮
            self.editor.setExtraSelections([selection])