from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QSplitter, QPlainTextEdit, QTextEdit, QShortcut
)
from PySide2.QtCore import Qt, Signal, QRect, QSize, QRegExp
from PySide2.QtGui import (
    QFont, QTextCursor, QSyntaxHighlighter, QTextCharFormat,
    QColor, QPainter, QPixmap, QIcon, QTextFormat, QKeySequence
)


class PythonHighlighter(QSyntaxHighlighter):
    """Python 语法高亮组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

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

        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#2B91AF"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"), class_format))

        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#74531F"))
        func_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"), func_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#A31515"))
        self.highlighting_rules.append((QRegExp(r'".*?"'), string_format))
        self.highlighting_rules.append((QRegExp(r"'.*?'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((QRegExp(r"#.*"), comment_format))

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


class SourceEditorView(QWidget):
    """高级源码浏览与编辑器视图"""

    save_requested = Signal(str)
    run_requested = Signal()  # 新增：直接运行当前文件信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file_path = ""
        self._init_ui()
        self._init_shortcuts()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(self.splitter)

        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        toolbar_layout = QHBoxLayout()
        self.lbl_file_path = QLabel("未打开文件", self)
        self.lbl_file_path.setStyleSheet("font-weight: bold; color: #333;")
        toolbar_layout.addWidget(self.lbl_file_path)

        toolbar_layout.addStretch()

        self.lbl_line_count = QLabel("行数: 0", self)
        self.lbl_line_count.setStyleSheet("color: #666; margin-right: 10px; font-weight: bold;")
        toolbar_layout.addWidget(self.lbl_line_count)

        # 新增：一键启动按钮
        self.btn_run = QPushButton("▶ 运行", self)
        self.btn_run.setEnabled(False)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.btn_run.clicked.connect(self.run_requested.emit)
        toolbar_layout.addWidget(self.btn_run)

        self.btn_save = QPushButton("保存源码 (Ctrl+S)", self)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._on_save_clicked)
        toolbar_layout.addWidget(self.btn_save)

        editor_layout.addLayout(toolbar_layout)

        self.editor = CodeEditor(self)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("background-color: #ffffff;")
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self._on_text_changed)
        
        self.highlighter = PythonHighlighter(self.editor.document())

        editor_layout.addWidget(self.editor)
        self.splitter.addWidget(editor_widget)

        outline_widget = QWidget()
        outline_layout = QVBoxLayout(outline_widget)
        outline_layout.setContentsMargins(0, 0, 0, 0)

        outline_layout.addWidget(QLabel("代码大纲 (类与函数):"))

        self.outline_list = QListWidget(self)
        self.outline_list.itemDoubleClicked.connect(self._jump_to_line)
        outline_layout.addWidget(self.outline_list)

        self.splitter.addWidget(outline_widget)
        self.splitter.setSizes([750, 210])

    def _init_shortcuts(self):
        """绑定 Ctrl+S 快捷键触发保存操作"""
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self._on_save_clicked)

    def _on_text_changed(self):
        """文本变动时激活保存按钮并实时更新行数"""
        self.btn_save.setEnabled(True)
        self._update_line_count()

    def _update_line_count(self):
        """更新当前编辑器代码总行数"""
        count = self.editor.blockCount()
        self.lbl_line_count.setText(f"行数: {count}")

    def _on_save_clicked(self):
        """触发保存：发送 save_requested 信号"""
        if self.btn_save.isEnabled():
            self.save_requested.emit(self.editor.toPlainText())

    def get_current_file_path(self):
        return self._current_file_path

    def update_editor_content(self, file_path, content):
        """更新编辑器文件内容并同步初始化状态"""
        self._current_file_path = file_path
        self.lbl_file_path.setText(file_path)
        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self.btn_save.setEnabled(False)
        
        # 打开有效文件时激活运行按钮
        self.btn_run.setEnabled(bool(file_path and file_path.endswith('.py')))
        self._update_line_count()

    def update_outline(self, symbols):
        """更新大纲列表"""
        self.outline_list.clear()

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
        """绘制首字母分类图标"""
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor(color_hex))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 18, 18, 4, 4)

        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, letter)
        painter.end()

        return QIcon(pixmap)

    def _jump_to_line(self, item):
        """跳转并高亮提示"""
        lineno = item.data(Qt.UserRole)
        if lineno:
            block = self.editor.document().findBlockByNumber(lineno - 1)
            cursor = QTextCursor(block)
            self.editor.setTextCursor(cursor)
            self.editor.setFocus()

            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#FFF2A8"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = cursor
            selection.cursor.clearSelection()

            self.editor.setExtraSelections([selection])