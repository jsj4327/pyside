"""
双栏差异查看器
包含行号、高亮、同步滚动、即时生效的选项过滤以及彻底优化的渲染逻辑
"""

import os
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QLabel, QStatusBar, QPushButton,
    QMessageBox, QApplication, QCheckBox, QFileDialog
)
from PySide2.QtCore import Qt, QTimer, Signal, QRect, QSize
from PySide2.QtGui import (
    QColor, QPainter, QTextCharFormat, QTextCursor,
    QFont
)

from .diff_model import DiffModel


# ==========================================
# 行号区域
# ==========================================
class LineNumberArea(QWidget):
    """行号区域"""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(50)

    def sizeHint(self):
        return QSize(50, self.editor.height())

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


# ==========================================
# 代码编辑器（带行号 + Ctrl+V 支持）
# ==========================================
class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器，支持 Ctrl+V 粘贴"""

    content_changed = Signal()

    def __init__(self, parent=None, editable=False):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._editable = editable

        font = QFont("Consolas", 10)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)

        self._update_line_number_width()

        # 设置样式
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                selection-background-color: #aaccff;
                border: none;
            }
        """)

        if editable:
            self.setObjectName("right_editor")
            self.setReadOnly(False)
            self.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #fafffe;
                    selection-background-color: #aaccff;
                    border: 1px solid #e0e0e0;
                    border-radius: 3px;
                }
            """)
        else:
            self.setObjectName("left_editor")
            self.setReadOnly(True)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))

        # 分隔线
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

    def setPlainText(self, text):
        super().setPlainText(text)
        self._update_line_number_width()

    def keyPressEvent(self, event):
        """键盘事件 - 支持 Ctrl+V"""
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                self.insertPlainText(text)
                self.content_changed.emit()
            return
        super().keyPressEvent(event)


# ==========================================
# 差异高亮器
# ==========================================
class DiffHighlighter:
    """差异行高亮"""

    COLORS = {
        'insert': QColor(200, 255, 200),   # 浅绿
        'delete': QColor(255, 200, 200),   # 浅红
        'replace': QColor(255, 255, 180),  # 浅黄
        'equal': QColor(255, 255, 255),    # 白色
        'padding': QColor(245, 245, 245),  # 浅灰（占位行）
    }

    @staticmethod
    def apply_highlight(editor: CodeEditor, line_types: list, model: DiffModel):
        """应用行高亮（彻底重置格式并精准按行渲染，避免残留与错位）"""
        if not model or not model.is_processed:
            return

        doc = editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        # 1. 彻底清除整篇文档原有的背景色与特殊前景色
        cursor.select(QTextCursor.Document)
        default_fmt = QTextCharFormat()
        default_fmt.setBackground(QColor(255, 255, 255))
        default_fmt.setForeground(QColor(0, 0, 0))
        cursor.setCharFormat(default_fmt)

        # 2. 逐行应用对应的高亮颜色
        for i, line_type in enumerate(line_types):
            if i >= doc.blockCount():
                break

            block = doc.findBlockByNumber(i)
            if not block.isValid():
                continue

            cursor.setPosition(block.position())
            cursor.select(QTextCursor.LineUnderCursor)

            fmt = QTextCharFormat()
            color = DiffHighlighter.COLORS.get(line_type, DiffHighlighter.COLORS['equal'])
            fmt.setBackground(color)

            if line_type == 'padding':
                fmt.setForeground(QColor(180, 180, 180))
            else:
                fmt.setForeground(QColor(0, 0, 0))

            cursor.setCharFormat(fmt)

        cursor.endEditBlock()

    @staticmethod
    def apply_word_highlight(editor: CodeEditor, line_index: int, word_diff: list):
        """应用词法级高亮（下划线）"""
        if not word_diff or line_index >= len(word_diff):
            return

        diff = word_diff[line_index]
        if not diff:
            return

        doc = editor.document()
        block = doc.findBlockByNumber(line_index)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        for left_start, left_end, right_start, right_end in diff:
            start_pos = left_start if editor.objectName() == "left_editor" else right_start
            end_pos = left_end if editor.objectName() == "left_editor" else right_end
            
            cursor.setPosition(block.position() + start_pos)
            cursor.setPosition(block.position() + end_pos, QTextCursor.KeepAnchor)
            
            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
            fmt.setUnderlineColor(QColor(200, 50, 50))
            cursor.setCharFormat(fmt)


# ==========================================
# 双栏差异查看器
# ==========================================
class DiffViewer(QWidget):
    """双栏差异查看器"""

    compare_requested = Signal()
    left_content_changed = Signal(str)
    right_content_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: DiffModel = None
        self._diff_positions: list = []
        self._current_diff_index: int = -1
        self._left_file_path: str = ""
        self._right_file_path: str = ""

        self._setup_ui()
        self._setup_scroll_sync()
        self._setup_connections()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # ---- 工具栏 ----
        toolbar = QHBoxLayout()

        self.btn_compare = QPushButton("🔄 比对")
        self.btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
                color: #e8f5e9;
            }
        """)
        toolbar.addWidget(self.btn_compare)

        self.btn_prev = QPushButton("⬆ 上一处")
        self.btn_prev.clicked.connect(self._navigate_prev)
        toolbar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("⬇ 下一处")
        self.btn_next.clicked.connect(self._navigate_next)
        toolbar.addWidget(self.btn_next)

        toolbar.addWidget(QLabel("  |  "))

        # 【新增】右边合并到左侧按钮
        self.btn_merge_right = QPushButton("➡ 覆盖到左侧")
        self.btn_merge_right.setToolTip("将右侧源码复制并合并覆盖到左侧文件，并保存")
        self.btn_merge_right.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self.btn_merge_right.clicked.connect(self._merge_right_to_left)
        toolbar.addWidget(self.btn_merge_right)

        toolbar.addWidget(QLabel("  |  "))

        # 选项复选框
        self.chk_ignore_space = QCheckBox("忽略空白")
        self.chk_ignore_space.setChecked(True)
        self.chk_ignore_space.toggled.connect(self._on_option_changed)
        toolbar.addWidget(self.chk_ignore_space)

        self.chk_ignore_case = QCheckBox("忽略大小写")
        self.chk_ignore_case.setChecked(False)
        self.chk_ignore_case.toggled.connect(self._on_option_changed)
        toolbar.addWidget(self.chk_ignore_case)

        self.chk_ignore_blank = QCheckBox("忽略空白行")
        self.chk_ignore_blank.setChecked(False)
        self.chk_ignore_blank.toggled.connect(self._on_option_changed)
        toolbar.addWidget(self.chk_ignore_blank)

        toolbar.addStretch()

        self.btn_open_right = QPushButton("📂 打开右侧文件")
        self.btn_open_right.clicked.connect(self._open_right_file)
        toolbar.addWidget(self.btn_open_right)

        layout.addLayout(toolbar)

        # ---- 分割器 ----
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧编辑器
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        self.left_label = QLabel("📄 左侧 (从文件浏览器双击)")
        self.left_label.setStyleSheet("background: #e8f0fe; padding: 4px 8px; font-weight: bold;")
        left_layout.addWidget(self.left_label)

        self.left_editor = CodeEditor(editable=False)
        left_layout.addWidget(self.left_editor)

        # 右侧编辑器
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        self.right_label = QLabel("📝 右侧 (可编辑，Ctrl+V粘贴)")
        self.right_label.setStyleSheet("background: #fce8e8; padding: 4px 8px; font-weight: bold;")
        right_layout.addWidget(self.right_label)

        self.right_editor = CodeEditor(editable=True)
        self.right_editor.content_changed.connect(self._on_right_editor_changed)
        right_layout.addWidget(self.right_editor)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        self.splitter.setSizes([400, 400])

        layout.addWidget(self.splitter, 1)

        # ---- 状态栏 ----
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { background: #f5f5f5; border-top: 1px solid #e0e0e0; }")
        layout.addWidget(self.status_bar)

        self.right_editor.setPlaceholderText("在此粘贴代码...\n支持 Ctrl+V 粘贴")
        self._update_buttons()

    def _setup_connections(self):
        self.btn_compare.clicked.connect(self._on_compare_clicked)

    def _on_compare_clicked(self):
        self.compare_requested.emit()

    def _on_option_changed(self, checked):
        self.compare_requested.emit()

    def _on_right_editor_changed(self):
        content = self.right_editor.toPlainText()
        has_content = bool(content.strip())
        self.right_content_changed.emit(has_content)

    def _setup_scroll_sync(self):
        self.left_editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.right_editor.verticalScrollBar().setValue(v)
        )
        self.right_editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.left_editor.verticalScrollBar().setValue(v)
        )
        self.left_editor.horizontalScrollBar().valueChanged.connect(
            lambda v: self.right_editor.horizontalScrollBar().setValue(v)
        )
        self.right_editor.horizontalScrollBar().valueChanged.connect(
            lambda v: self.left_editor.horizontalScrollBar().setValue(v)
        )

    def set_left_content(self, content: str, file_path: str = ""):
        self._left_file_path = file_path
        self.left_editor.setPlainText(content)
        self.left_content_changed.emit(file_path)
        if file_path:
            self.left_label.setText(f"📄 {os.path.basename(file_path)}")

    def set_right_content(self, content: str):
        self.right_editor.setPlainText(content)
        self.right_label.setText("📝 粘贴内容")
        has_content = bool(content.strip())
        self.right_content_changed.emit(has_content)

    def set_right_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            self.set_right_content(content)
            self.right_label.setText(f"📄 {os.path.basename(file_path)}")
            self.right_content_changed.emit(True)
            return True
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件:\n{str(e)}")
            return False

    def _open_right_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择右侧文件", "", "所有文件 (*.*)"
        )
        if path:
            self.set_right_file(path)

    def _merge_right_to_left(self):
        """将右侧源码复制到左侧，并保存文件"""
        right_content = self.right_editor.toPlainText()
        if not right_content.strip():
            QMessageBox.warning(self, "警告", "右侧内容为空，无法合并！")
            return

        target_path = self._left_file_path
        if not target_path:
            target_path, _ = QFileDialog.getSaveFileName(
                self, "保存左侧文件", "", "所有文件 (*.*)"
            )
            if not target_path:
                return

        try:
            # 1. 写入文件
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(right_content)

            # 2. 更新左侧内容及标签
            self.set_left_content(right_content, target_path)
            
            # 3. 提示信息
            self.status_bar.showMessage(f"✅ 已成功将右侧代码合并覆盖并保存至: {target_path}", 5000)
            QMessageBox.information(self, "成功", f"文件已成功保存:\n{target_path}")

            # 4. 触发重新比对
            self.compare_requested.emit()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败:\n{str(e)}")

    def display_model(self, model: DiffModel):
        self.model = model

        if not model or not model.is_processed:
            self.status_bar.showMessage("无数据")
            return

        left_scroll = self.left_editor.verticalScrollBar().value()
        right_scroll = self.right_editor.verticalScrollBar().value()

        if len(model.left_lines) != self.left_editor.document().blockCount():
            self.left_editor.setPlainText('\n'.join(model.left_lines))
            self.right_editor.setPlainText('\n'.join(model.right_lines))
            self.left_editor.verticalScrollBar().setValue(left_scroll)
            self.right_editor.verticalScrollBar().setValue(right_scroll)

        DiffHighlighter.apply_highlight(self.left_editor, model.left_types, model)
        DiffHighlighter.apply_highlight(self.right_editor, model.right_types, model)

        for i, block in enumerate(model.blocks):
            if block.type == 'replace' and block.word_diff:
                for j, word_diff in enumerate(block.word_diff):
                    if word_diff:
                        line_idx = block.left_start + j
                        if line_idx < len(model.left_lines):
                            DiffHighlighter.apply_word_highlight(
                                self.left_editor, line_idx, [word_diff]
                            )
                            DiffHighlighter.apply_word_highlight(
                                self.right_editor, line_idx, [word_diff]
                            )

        self._collect_diff_positions(model)

        stats = model.statistics
        self.status_bar.showMessage(
            f"总行数: L{stats.total_lines_left} / R{stats.total_lines_right} | "
            f"新增: {stats.inserted} | 删除: {stats.deleted} | "
            f"修改: {stats.modified} | 相似度: {stats.similarity:.1f}%"
        )

        self._update_buttons()

    def _collect_diff_positions(self, model: DiffModel):
        self._diff_positions = []
        for i, (left_type, right_type) in enumerate(zip(model.left_types, model.right_types)):
            if left_type in ('insert', 'delete', 'replace') or right_type in ('insert', 'delete', 'replace'):
                self._diff_positions.append(i)
        self._current_diff_index = -1 if not self._diff_positions else 0

    def _navigate_prev(self):
        if not self._diff_positions:
            return
        self._current_diff_index = (self._current_diff_index - 1) % len(self._diff_positions)
        self._goto_diff(self._diff_positions[self._current_diff_index])

    def _navigate_next(self):
        if not self._diff_positions:
            return
        self._current_diff_index = (self._current_diff_index + 1) % len(self._diff_positions)
        self._goto_diff(self._diff_positions[self._current_diff_index])

    def _goto_diff(self, line_index: int):
        self._scroll_to_line(self.left_editor, line_index)
        self._scroll_to_line(self.right_editor, line_index)
        self._flash_line(self.left_editor, line_index)
        self._flash_line(self.right_editor, line_index)

    def _scroll_to_line(self, editor: CodeEditor, line_index: int):
        if line_index < 0 or line_index >= editor.document().blockCount():
            return
        cursor = QTextCursor(editor.document().findBlockByNumber(line_index))
        editor.setTextCursor(cursor)
        editor.centerCursor()

    def _flash_line(self, editor: CodeEditor, line_index: int):
        block = editor.document().findBlockByNumber(line_index)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        cursor.select(QTextCursor.LineUnderCursor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 100))
        cursor.setCharFormat(fmt)

        QTimer.singleShot(800, lambda: self._restore_line_format(editor, line_index))

    def _restore_line_format(self, editor: CodeEditor, line_index: int):
        if not self.model:
            return
        if editor == self.left_editor:
            DiffHighlighter.apply_highlight(editor, self.model.left_types, self.model)
        else:
            DiffHighlighter.apply_highlight(editor, self.model.right_types, self.model)

    def clear(self):
        self.left_editor.clear()
        self.right_editor.clear()
        self.model = None
        self._diff_positions.clear()
        self.status_bar.clearMessage()
        self._update_buttons()

    def get_compare_options(self):
        return {
            'ignore_space': self.chk_ignore_space.isChecked(),
            'ignore_case': self.chk_ignore_case.isChecked(),
            'ignore_blank': self.chk_ignore_blank.isChecked()
        }

    def _update_buttons(self):
        has_diff = bool(self._diff_positions)
        self.btn_prev.setEnabled(has_diff)
        self.btn_next.setEnabled(has_diff)