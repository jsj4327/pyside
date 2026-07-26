#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import ast
import textwrap  # ← 新增导入
import subprocess
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTextEdit,
    QMessageBox, QFileDialog, QPlainTextEdit,
    QStatusBar, QToolBar, QAction, QDialog, QCheckBox, QSplitter
)
from PySide2.QtCore import Qt, QProcess, QRect, QSettings, QSize
from PySide2.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QKeySequence, QPalette, QPainter, QTextDocument, QTextCursor,
    QIcon
)


# ==================== 语法高亮（可开关，默认关闭） ====================
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self.highlighting_rules = []

        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue',
            'def', 'del', 'elif', 'else', 'except', 'exec',
            'finally', 'for', 'from', 'global', 'if', 'import',
            'in', 'is', 'lambda', 'not', 'or', 'pass',
            'print', 'raise', 'return', 'try', 'while',
            'yield', 'None', 'True', 'False'
        ]
        operators = [
            '=', '==', '!=', '<', '<=', '>', '>=',
            '\\+', '-', '\\*', '/', '//', '%', '\\*\\*',
            '\\+=', '-=', '\\*=', '/=', '%=', '&=', '\\|=',
            '^=', '>>=', '<<='
        ]

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(0, 0, 200))
        keyword_format.setFontWeight(QFont.Bold)

        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor(200, 100, 0))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 150, 0))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(100, 100, 100))
        comment_format.setFontItalic(True)

        number_format = QTextCharFormat()
        number_format.setForeground(QColor(150, 0, 150))

        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0, 0, 180))
        function_format.setFontWeight(QFont.Bold)

        class_format = QTextCharFormat()
        class_format.setForeground(QColor(0, 128, 128))
        class_format.setFontWeight(QFont.Bold)

        for kw in keywords:
            self.highlighting_rules.append((r'\b' + kw + r'\b', keyword_format))
        for op in operators:
            self.highlighting_rules.append((r'' + op + r'(?!=)', operator_format))
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))
        self.highlighting_rules.append((r'\b[0-9]+\b', number_format))
        self.highlighting_rules.append((r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\\()', function_format))
        self.highlighting_rules.append((r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_format))
        self.highlighting_rules.append((r'#[^\n]*', comment_format))

    def set_enabled(self, enabled):
        if self._enabled != enabled:
            self._enabled = enabled
            self.rehighlight()

    def highlightBlock(self, text):
        if not self._enabled:
            return
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


# ==================== 查找与替换对话框 ====================
class FindReplaceDialog(QDialog):
    def __init__(self, editor_widget, parent=None):
        super().__init__(parent)
        self.editor_widget = editor_widget
        self.setWindowTitle("查找与替换")
        self.setFixedSize(380, 160)

        layout = QVBoxLayout(self)
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("查找:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("替换:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        opt_layout = QHBoxLayout()
        self.case_checkbox = QCheckBox("区分大小写")
        opt_layout.addWidget(self.case_checkbox)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        btn_layout = QHBoxLayout()
        self.find_btn = QPushButton("查找下一个")
        self.find_btn.clicked.connect(self.find_next)
        btn_layout.addWidget(self.find_btn)

        self.replace_btn = QPushButton("替换")
        self.replace_btn.clicked.connect(self.replace_current)
        btn_layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("替换全部")
        self.replace_all_btn.clicked.connect(self.replace_all)
        btn_layout.addWidget(self.replace_all_btn)

        layout.addLayout(btn_layout)

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return
        flags = QTextDocument.FindFlags()
        if self.case_checkbox.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        found = self.editor_widget.find(text, flags)
        if not found:
            self.editor_widget.moveCursor(self.editor_widget.textCursor().Start)
            found = self.editor_widget.find(text, flags)
            if not found:
                QMessageBox.information(self, "提示", "未找到指定文本！")

    def replace_current(self):
        cursor = self.editor_widget.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        text = self.find_input.text()
        replacement = self.replace_input.text()
        if not text:
            return
        content = self.editor_widget.toPlainText()
        if self.case_checkbox.isChecked():
            new_content = content.replace(text, replacement)
        else:
            pattern = re.compile(re.escape(text), re.IGNORECASE)
            new_content = pattern.sub(replacement, content)
        self.editor_widget.setPlainText(new_content)
        QMessageBox.information(self, "提示", "替换完成！")


# ==================== 行号侧边栏组件 ====================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


# ==================== 代码编辑器（行号+大文本优化） ====================
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 15 + self.fontMetrics().width('9') * digits
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

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(230, 240, 250)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    # ---------- 修正缩进：以下三个方法必须属于类内部 ----------
    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(120, 120, 120))
                painter.setFont(self.font())
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 int(Qt.AlignRight | Qt.AlignVCenter), number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            if len(text) > 1500:
                cursor = self.textCursor()
                cursor.beginEditBlock()
                if cursor.hasSelection():
                    cursor.removeSelectedText()
                cursor.insertText(text)
                cursor.endEditBlock()
                return
        super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key_Tab:
            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                cursor.beginEditBlock()
                start_block = self.document().findBlock(start)
                end_block = self.document().findBlock(end)
                if end_block.position() == end and end_block != start_block:
                    end_block = end_block.previous()
                block = start_block
                while block.isValid():
                    cursor.setPosition(block.position())
                    cursor.insertText("    ")
                    if block == end_block:
                        break
                    block = block.next()
                cursor.endEditBlock()
                return
            else:
                cursor.insertText("    ")
                return
        elif event.key() == Qt.Key_Backtab:
            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                cursor.beginEditBlock()
                start_block = self.document().findBlock(start)
                end_block = self.document().findBlock(end)
                if end_block.position() == end and end_block != start_block:
                    end_block = end_block.previous()
                block = start_block
                while block.isValid():
                    text = block.text()
                    if text.startswith("    "):
                        cursor.setPosition(block.position())
                        cursor.movePosition(cursor.Right, cursor.KeepAnchor, 4)
                        cursor.removeSelectedText()
                    elif text.startswith("\t"):
                        cursor.setPosition(block.position())
                        cursor.movePosition(cursor.Right, cursor.KeepAnchor, 1)
                        cursor.removeSelectedText()
                    if block == end_block:
                        break
                    block = block.next()
                cursor.endEditBlock()
                return
        pairs = {
            Qt.Key_ParenLeft: ('(', ')'),
            Qt.Key_BracketLeft: ('[', ']'),
            Qt.Key_BraceLeft: ('{', '}'),
            Qt.Key_QuoteDbl: ('"', '"'),
            Qt.Key_Apostrophe: ("'", "'")
        }
        if event.key() in pairs and not cursor.hasSelection():
            left, right = pairs[event.key()]
            cursor.insertText(left + right)
            cursor.movePosition(cursor.Left)
            self.setTextCursor(cursor)
            event.accept()
        else:
            super().keyPressEvent(event)


# ==================== 代码标签页（含高亮开关） ====================
class CodeTab(QWidget):
    def __init__(self, filename, work_dir, parent=None, main_window=None):
        super().__init__(parent)
        self.filename = filename
        self.file_path = None
        self.work_dir = work_dir
        self.main_window = main_window
        self.process = None
        self.is_running = False

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.editor = CodeEditor()
        self.editor.setFont(QFont("Courier New", 11))
        self.editor.setTabStopWidth(4)
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #b0d0ff;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                font-family: "Courier New";
                font-size: 12px;
            }
        """)
        self.editor.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.editor.document().modificationChanged.connect(self.on_modification_changed)

        self.highlighter = PythonHighlighter(self.editor.document())
        self.main_layout.addWidget(self.editor)

        # 控制栏
        control_layout = QHBoxLayout()
        self.run_button = QPushButton("▶ 运行")
        self.run_button.setStyleSheet("""
            QPushButton { background-color: #2d7d2d; color: white; padding: 6px 15px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #3d9d3d; }
            QPushButton:disabled { background-color: #cccccc; color: #666; }
        """)
        self.run_button.clicked.connect(self.run_code)
        control_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("■ 停止")
        self.stop_button.setStyleSheet("""
            QPushButton { background-color: #8d2d2d; color: white; padding: 6px 15px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #ad3d3d; }
            QPushButton:disabled { background-color: #cccccc; color: #666; }
        """)
        self.stop_button.clicked.connect(self.stop_code)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.highlight_checkbox = QCheckBox("启用语法高亮")
        self.highlight_checkbox.setChecked(False)
        self.highlight_checkbox.stateChanged.connect(self.on_highlight_toggled)
        control_layout.addWidget(self.highlight_checkbox)

        control_layout.addStretch()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #333; padding: 5px;")
        control_layout.addWidget(self.status_label)
        self.main_layout.addLayout(control_layout)

        # 输出区域
        output_top_layout = QHBoxLayout()
        output_top_layout.addWidget(QLabel("<b>控制台输出:</b>"))
        output_top_layout.addStretch()
        self.clear_output_button = QPushButton("🗑️ 清空输出")
        self.clear_output_button.setStyleSheet("""
            QPushButton { background-color: #e0e0e0; color: #333; padding: 3px 10px; border: 1px solid #b0b0b0; border-radius: 3px; font-size: 11px; }
            QPushButton:hover { background-color: #d0d0d0; }
        """)
        self.clear_output_button.clicked.connect(self.clear_output)
        output_top_layout.addWidget(self.clear_output_button)
        self.main_layout.addLayout(output_top_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 10))
        self.output_text.setStyleSheet("""
            QTextEdit { background-color: #f8f8f8; color: #000000; border: 1px solid #c0c0c0; border-radius: 4px; font-family: "Courier New"; font-size: 11px; }
        """)
        self.output_text.setMaximumHeight(150)
        self.main_layout.addWidget(self.output_text)

        self.setLayout(self.main_layout)
        self.add_example_code()

    def on_highlight_toggled(self, state):
        self.highlighter.set_enabled(state == Qt.Checked)
        self.status_label.setText("高亮已启用" if state else "高亮已禁用（性能优化）")
        self.status_label.setStyleSheet("color: #333; padding: 5px;")

    def add_example_code(self):
        example = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Hello, World!")
print("新特性：已加入大文本粘贴防卡死优化机制！")

def calculate_sum(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total

print("1到100求和结果:", calculate_sum(100))
'''
        self.editor.setPlainText(example)
        self.editor.document().setModified(False)

    def get_code(self):
        return self.editor.toPlainText()

    def set_code(self, code):
        self.editor.setPlainText(code)
        self.editor.document().setModified(False)

    def clear_output(self):
        self.output_text.clear()

    def on_cursor_position_changed(self):
        if self.main_window and self.main_window.tab_widget.currentWidget() == self:
            cursor = self.editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.main_window.update_cursor_position_display(line, col)

    def on_modification_changed(self, modified):
        if self.main_window:
            self.main_window.update_tab_title(self)

    def save_to_file(self, target_dir=None):
        if target_dir is None:
            target_dir = self.work_dir
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except:
                target_dir = os.path.expanduser("~")
        if self.file_path and os.path.dirname(self.file_path) == target_dir:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.get_code())
                self.editor.document().setModified(False)
                return True
            except:
                return False
        new_path = os.path.join(target_dir, self.filename)
        try:
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(self.get_code())
            self.file_path = new_path
            self.work_dir = target_dir
            self.editor.document().setModified(False)
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败：{str(e)}")
            return False

    def run_code(self):
        if self.is_running:
            return
        if not self.save_to_file():
            return
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.handle_finished)
        self.is_running = True
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("正在运行...")
        self.status_label.setStyleSheet("color: #2d7d2d; padding: 5px;")
        self.output_text.append("=" * 50)
        self.output_text.append(f"执行文件: {self.filename}")
        self.output_text.append("=" * 50)
        self.process.start("python3", [self.file_path])

    def handle_output(self):
        data = self.process.readAllStandardOutput()
        text = data.data().decode('utf-8', errors='ignore')
        self.output_text.append(text)
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def handle_error(self):
        data = self.process.readAllStandardError()
        text = data.data().decode('utf-8', errors='ignore')
        self.output_text.append(f"<span style='color:#cc0000'>{text}</span>")
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def handle_finished(self, exit_code, exit_status):
        self.is_running = False
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if exit_code == 0:
            self.status_label.setText("运行完成 ✓")
            self.status_label.setStyleSheet("color: #2d7d2d; padding: 5px;")
            self.output_text.append("=" * 50)
            self.output_text.append("✅ 程序运行成功\n")
        else:
            self.status_label.setText(f"运行失败 (退出码: {exit_code})")
            self.status_label.setStyleSheet("color: #8d2d2d; padding: 5px;")
            self.output_text.append("=" * 50)
            self.output_text.append(f"❌ 程序运行失败 (退出码: {exit_code})\n")
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def stop_code(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            self.process.waitForFinished(1000)
            if self.process.state() == QProcess.Running:
                self.process.kill()
            self.status_label.setText("已停止")
            self.status_label.setStyleSheet("color: #8d2d2d; padding: 5px;")
            self.output_text.append("⚠️ 程序已被用户停止\n")

    def closeEvent(self, event):
        try:
            if self.process and self.process.state() == QProcess.Running:
                self.process.kill()
                self.process.waitForFinished(1000)
        except:
            pass


# ==================== 代码分析与应用面板（支持嵌套定义） ====================
class CodeModifyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title_label = QLabel("<b>代码修改面板</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        info_label = QLabel("粘贴代码段，点击分析后，将根据类/函数名（含嵌套）修改或添加")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(info_label)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("在此粘贴要合并的代码...")
        self.input_edit.setFont(QFont("Courier New", 10))
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
        """)
        self.input_edit.setMinimumHeight(200)
        layout.addWidget(self.input_edit)

        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🔍 分析并应用")
        self.analyze_btn.setStyleSheet("""
            QPushButton { background-color: #0078d7; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #0066be; }
        """)
        self.analyze_btn.clicked.connect(self.analyze_and_apply)
        btn_layout.addWidget(self.analyze_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.input_edit.clear)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        self.log("就绪，等待粘贴代码...")

    def log(self, msg, color=None):
        if color:
            self.log_text.append(f'<span style="color:{color}">{msg}</span>')
        else:
            self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def parse_definitions(self, code):
        """
        解析Python代码，提取所有层级（包括嵌套）的类（class）和函数（def）定义。
        返回列表，每个元素包含：
            {'name': str, 'type': 'class'/'function', 'start': int, 'end': int, 'text': str}
        """
        tree = ast.parse(code)
        lines = code.splitlines(keepends=True)
        definitions = []

        def collect(node):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                name = node.name
                typ = 'class' if isinstance(node, ast.ClassDef) else 'function'
                start = node.lineno
                # 1. 优先使用 end_lineno (Python 3.8+)
                end = getattr(node, 'end_lineno', None)
                if end is None:
                    # 2. 如果 body 不为空，取 body 最后一个元素的 lineno
                    if hasattr(node, 'body') and node.body:
                        last_child = node.body[-1]
                        # 对于函数体，可能包含多行，取最后子节点行号
                        end = last_child.lineno
                        # 如果最后一个子节点是 Expr 或 Assign，可能有多行，但 lineno 是起始行，
                        # 我们可以尝试从 tokenize 获取，为了简单，再检查子节点是否有 end_lineno
                        if hasattr(last_child, 'end_lineno'):
                            end = last_child.end_lineno
                        # 如果 body 为空（如 pass），则 end 等于 start
                    else:
                        end = start
                # 确保 end >= start
                if end < start:
                    end = start
                # 提取文本块，注意切片结束索引为 end（因为行号从1开始，切片到 end 行）
                block_lines = lines[start-1:end]
                block_text = ''.join(block_lines)
                definitions.append({
                    'name': name,
                    'type': typ,
                    'start': start,
                    'end': end,
                    'text': block_text
                })
                # 记录日志（可选）
                # print(f"Found {typ} {name} lines {start}-{end}")
            # 递归收集嵌套定义
            for child in ast.iter_child_nodes(node):
                collect(child)

        collect(tree)
        return definitions

    def analyze_and_apply(self):
        raw_code = self.input_edit.toPlainText()
        if not raw_code.strip():
            self.log("⚠️ 请先粘贴要分析的代码段！", "#cc6600")
            return

        # 使用 textwrap.dedent 移除公共前导缩进，防止 ast.parse 报错
        code = textwrap.dedent(raw_code)

        main = self.main_window
        if not hasattr(main, 'tab_widget'):
            self.log("⚠️ 未找到主窗口的标签页组件！", "#cc6600")
            return
        current_tab = main.tab_widget.currentWidget()
        if not current_tab:
            self.log("⚠️ 没有打开任何编辑器标签页！", "#cc6600")
            return

        try:
            new_defs = self.parse_definitions(code)
        except Exception as e:
            self.log(f"❌ 解析粘贴代码失败: {str(e)}", "#cc0000")
            return

        if not new_defs:
            self.log("⚠️ 未检测到任何类或函数定义。", "#cc6600")
            return

        src_code = current_tab.get_code()
        try:
            existing_defs = self.parse_definitions(src_code)
        except Exception as e:
            self.log(f"❌ 解析当前源码失败: {str(e)}", "#cc0000")
            return

        # 构建现有定义字典 (名称,类型) -> 定义信息
        existing_dict = { (d['name'], d['type']): d for d in existing_defs }

        lines = src_code.splitlines(keepends=True)
        replacements = []
        appends = []

        for new_def in new_defs:
            key = (new_def['name'], new_def['type'])
            if key in existing_dict:
                old_def = existing_dict[key]
                # 记录替换信息
                replacements.append({
                    'start_idx': old_def['start'] - 1,   # 转为0基索引
                    'end_idx': old_def['end'],           # 切片结束索引（不包含），因为行号是1基，所以结束索引就是行号
                    'new_lines': new_def['text'].splitlines(keepends=True),
                    'name': new_def['name'],
                    'type': new_def['type'],
                    'old_start': old_def['start'],
                    'old_end': old_def['end']
                })
            else:
                appends.append(new_def)

        if not replacements and not appends:
            self.log("ℹ️ 没有需要修改的定义", "#888")
            return

        # 倒序替换，避免行号漂移
        replacements.sort(key=lambda x: x['start_idx'], reverse=True)
        for rep in replacements:
            # 打印调试信息
            self.log(f"替换 {rep['type']} '{rep['name']}' 行 {rep['old_start']}-{rep['old_end']} (共 {len(rep['new_lines'])} 行)", "#2d7d2d")
            # 执行替换
            lines[rep['start_idx']:rep['end_idx']] = rep['new_lines']

        # 处理追加：放在文件末尾，并确保换行
        if appends:
            # 确保末尾有换行
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            elif not lines:
                lines.append('\n')
            for new_def in appends:
                # 如果文件末尾已有空行，不再添加多余空行
                # 但为了保证清晰，添加一个换行再添加定义
                lines.append('\n')  # 与前面代码隔开
                lines.append(new_def['text'])
                if not new_def['text'].endswith('\n'):
                    lines.append('\n')
                self.log(f"追加 {new_def['type']} '{new_def['name']}' 到文件末尾", "#cc6600")

        # 生成新代码并设置到编辑器
        new_code = ''.join(lines)
        current_tab.set_code(new_code)
        self.log("🎉 修改完成！", "#0078d7")  

# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title_label = QLabel("<b>代码修改面板</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        info_label = QLabel("粘贴代码段，点击分析后，将根据类/函数名（含嵌套）修改或添加")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(info_label)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("在此粘贴要合并的代码...")
        self.input_edit.setFont(QFont("Courier New", 10))
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
        """)
        self.input_edit.setMinimumHeight(200)
        layout.addWidget(self.input_edit)

        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🔍 分析并应用")
        self.analyze_btn.setStyleSheet("""
            QPushButton { background-color: #0078d7; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #0066be; }
        """)
        self.analyze_btn.clicked.connect(self.analyze_and_apply)
        btn_layout.addWidget(self.analyze_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.input_edit.clear)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        self.log("就绪，等待粘贴代码...")

    # 以下所有方法保持不变（与你的原有代码一致）
    def update_work_dir_display(self):
        self.path_edit.setText(self.work_dir)
        display = self.work_dir
        if len(display) > 40:
            display = "..." + display[-37:]
        self.work_dir_label.setText(f"📁 {display}")
        self.settings.setValue("work_dir", self.work_dir)

    def update_cursor_position_display(self, line, col):
        self.cursor_pos_label.setText(f"行 {line}, 列 {col}")

    def update_tab_title(self, code_tab):
        idx = self.tab_widget.indexOf(code_tab)
        if idx >= 0:
            title = code_tab.filename
            if code_tab.editor.document().isModified():
                title += " *"
            self.tab_widget.setTabText(idx, title)

    def set_work_dir(self, path):
        if os.path.isdir(path):
            self.work_dir = path
            self.update_work_dir_display()
            self.status_bar.showMessage(f"工作目录已切换: {path}")

    def on_path_edited(self):
        path = self.path_edit.text().strip()
        if os.path.exists(path) and os.path.isdir(path):
            self.set_work_dir(path)
        else:
            QMessageBox.warning(self, "警告", "输入的路径无效或不存在！")
            self.path_edit.setText(self.work_dir)

    def go_parent_path(self):
        parent_path = os.path.dirname(self.work_dir)
        if parent_path and os.path.exists(parent_path):
            self.set_work_dir(parent_path)
        else:
            QMessageBox.information(self, "提示", "已经是盘符根目录或最上层目录！")

    def open_current_directory(self):
        if not os.path.exists(self.work_dir):
            QMessageBox.warning(self, "错误", "当前工作目录不存在！")
            return
        try:
            if sys.platform == 'win32':
                os.startfile(self.work_dir)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.work_dir])
            else:
                subprocess.Popen(['xdg-open', self.work_dir])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开目录：{str(e)}")

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        new_action = QAction("新建文件", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.create_new_tab)
        file_menu.addAction(new_action)

        open_action = QAction("打开文件...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        self.recent_menu = file_menu.addMenu("最近打开")
        self.update_recent_files_menu()

        save_action = QAction("保存文件", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_current_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存为...", self)
        save_as_action.triggered.connect(self.save_current_file_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑")
        find_action = QAction("查找与替换...", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.show_find_replace_dialog)
        edit_menu.addAction(find_action)

        run_menu = menubar.addMenu("运行")
        run_action = QAction("运行当前文件", self)
        run_action.setShortcut(QKeySequence("F5"))
        run_action.triggered.connect(self.run_current_file)
        run_menu.addAction(run_action)

        stop_action = QAction("停止运行", self)
        stop_action.setShortcut(QKeySequence("F6"))
        stop_action.triggered.connect(self.stop_current_file)
        run_menu.addAction(stop_action)

    def create_toolbar(self):
        toolbar = self.addToolBar("工具栏")
        toolbar.setMovable(False)
        new_action = QAction("📄 新建", self)
        new_action.triggered.connect(self.create_new_tab)
        toolbar.addAction(new_action)

        open_action = QAction("📂 打开", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction("💾 保存", self)
        save_action.triggered.connect(self.save_current_file)
        toolbar.addAction(save_action)

        toolbar.addSeparator()
        find_action = QAction("🔍 查找", self)
        find_action.triggered.connect(self.show_find_replace_dialog)
        toolbar.addAction(find_action)

        toolbar.addSeparator()
        run_action = QAction("▶ 运行", self)
        run_action.triggered.connect(self.run_current_file)
        toolbar.addAction(run_action)

        stop_action = QAction("■ 停止", self)
        stop_action.triggered.connect(self.stop_current_file)
        toolbar.addAction(stop_action)

        toolbar.addSeparator()
        help_action = QAction("❓ 帮助", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

    def update_recent_files_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_files", [])
        if not recent_files:
            no_action = QAction("无最近打开记录", self)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return
        for path in recent_files:
            if os.path.exists(path):
                action = QAction(path, self)
                action.triggered.connect(lambda checked=False, p=path: self.open_file_by_path(p))
                self.recent_menu.addAction(action)

    def add_to_recent_files(self, file_path):
        recent_files = self.settings.value("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:5]
        self.settings.setValue("recent_files", recent_files)
        self.update_recent_files_menu()

    def show_find_replace_dialog(self):
        current = self.tab_widget.currentWidget()
        if current and isinstance(current, CodeTab):
            dialog = FindReplaceDialog(current.editor, self)
            dialog.show()

    def create_new_tab(self):
        filename = self.filename_edit.text().strip()
        if not filename:
            filename = f"program{self.file_counter}.py"
            self.file_counter += 1
        else:
            if not filename.endswith('.py'):
                filename += '.py'
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).replace(" *", "") == filename:
                self.tab_widget.setCurrentIndex(i)
                return
        code_tab = CodeTab(filename, self.work_dir, main_window=self)
        self.tab_widget.addTab(code_tab, filename)
        self.tab_widget.setCurrentWidget(code_tab)
        self.filename_edit.clear()
        self.status_bar.showMessage(f"已创建新文件: {filename}")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开 Python 文件", self.work_dir,
            "Python 文件 (*.py);;所有文件 (*.*)"
        )
        if file_path:
            self.open_file_by_path(file_path)

    def open_file_by_path(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件不存在或已被移除！")
            return
        filename = os.path.basename(file_path)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, CodeTab) and widget.file_path == file_path:
                self.tab_widget.setCurrentIndex(i)
                return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            work_dir = os.path.dirname(file_path)
            code_tab = CodeTab(filename, work_dir, main_window=self)
            code_tab.set_code(content)
            code_tab.file_path = file_path
            code_tab.work_dir = work_dir
            self.set_work_dir(work_dir)
            self.tab_widget.addTab(code_tab, filename)
            self.tab_widget.setCurrentWidget(code_tab)
            self.add_to_recent_files(file_path)
            self.status_bar.showMessage(f"已打开文件: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败：{str(e)}")

    def save_current_file(self):
        current = self.tab_widget.currentWidget()
        if not current or not isinstance(current, CodeTab):
            return
        if current.save_to_file(self.work_dir):
            if current.file_path:
                self.add_to_recent_files(current.file_path)
            self.update_tab_title(current)
            self.status_bar.showMessage(f"已保存: {current.filename}")
        else:
            self.save_current_file_as()

    def save_current_file_as(self):
        current = self.tab_widget.currentWidget()
        if not current or not isinstance(current, CodeTab):
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", os.path.join(self.work_dir, current.filename),
            "Python 文件 (*.py);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(current.get_code())
                current.file_path = file_path
                current.filename = os.path.basename(file_path)
                current.work_dir = os.path.dirname(file_path)
                current.editor.document().setModified(False)
                self.set_work_dir(current.work_dir)
                self.update_tab_title(current)
                self.add_to_recent_files(file_path)
                idx = self.tab_widget.indexOf(current)
                if idx >= 0:
                    self.tab_widget.setTabText(idx, current.filename)
                self.status_bar.showMessage(f"已另存为: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{str(e)}")

    def set_work_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录", self.work_dir)
        if dir_path:
            self.set_work_dir(dir_path)

    def run_current_file(self):
        current = self.tab_widget.currentWidget()
        if current and isinstance(current, CodeTab):
            current.run_code()

    def stop_current_file(self):
        current = self.tab_widget.currentWidget()
        if current and isinstance(current, CodeTab):
            current.stop_code()

    def on_tab_changed(self, index):
        current = self.tab_widget.widget(index)
        if current and isinstance(current, CodeTab):
            current.on_cursor_position_changed()

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget and isinstance(widget, CodeTab):
            if widget.editor.document().isModified():
                reply = QMessageBox.question(
                    self, "确认关闭",
                    f"文件 '{widget.filename}' 有未保存的更改，是否先保存？",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    if not widget.save_to_file(self.work_dir):
                        return
                elif reply == QMessageBox.Cancel:
                    return
        self.tab_widget.removeTab(index)
        if widget:
            widget.close()

    def show_help(self):
        help_text = """
        <h2>Python 代码编辑器 - 性能优化版</h2>
        <h3>大文本粘贴加速 & 可开关高亮 & 智能代码合并</h3>
        <ul>
            <li><b>大文本粘贴优化：</b>超过 1500 字符的粘贴自动批量写入，消除卡顿。</li>
            <li><b>语法高亮默认关闭</b>，可勾选“启用语法高亮”随时打开。</li>
            <li><b>右侧“代码修改面板”</b>：粘贴代码段，自动分析所有层级的类/函数，<b>存在则替换，不存在则添加</b>。</li>
            <li>支持行号显示、自动括号补全、Tab/Shift+Tab 缩进。</li>
            <li>运行/停止、查找替换、最近打开记录等完整功能。</li>
        </ul>
        """
        QMessageBox.information(self, "帮助", help_text)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("work_dir", self.work_dir)
        event.accept()


# ==================== 启动 ====================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PyEditor")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()