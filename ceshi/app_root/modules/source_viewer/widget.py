# -*- coding:utf-8 -*-
import os
import sys
import json
import re
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox,
    QPushButton, QLineEdit, QTextEdit, QSizePolicy,
    QListWidget, QListWidgetItem, QTreeView, QFileSystemModel,
    QHeaderView, QCheckBox, QGroupBox
)
from PySide2.QtCore import Qt, QProcess, QDir, QEvent, QTimer, Signal
from PySide2.QtGui import QBrush, QColor, QFont

from .code_editor import CodeEditor
from .symbol_parser import SymbolParser
from core import FileAnalyzer


def extract_json_from_response(text):
    if not text:
        return None
    def strip_line_numbers(content):
        lines = content.splitlines()
        stripped_lines = []
        for line in lines:
            stripped = re.sub(r'^\s*\d+[\.\)]?\s*', '', line)
            stripped_lines.append(stripped)
        return '\n'.join(stripped_lines)
    candidates = []
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        candidates.append(match.group(1).strip())
    match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if match:
        candidates.append(match.group(1).strip())
    match = re.search(r'【?[\u4e00-\u9fa5]*\s*(?:json|JSON|代码块|结果)\s*】?\s*([\s\S]*?)\s*【?[\u4e00-\u9fa5]*\s*(?:结束|结尾|完毕)\s*】?', text)
    if match:
        candidates.append(match.group(1).strip())
    candidates.append(text.strip())
    for raw in candidates:
        cleaned = strip_line_numbers(raw)
        try:
            return json.loads(cleaned)
        except:
            pass
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
    json_match = re.search(r'(\{[\s\S]*\})', text)
    if json_match:
        try:
            candidate = json_match.group(1)
            cleaned = strip_line_numbers(candidate)
            return json.loads(cleaned)
        except:
            pass
    return None


class SourceViewerWidget(QWidget):
    directory_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = ""
        self.current_root_path = ""
        self.process = None
        self.modification_history = []
        self.current_request_type = None
        self.init_ui()
        self.set_root_path(QDir.homePath())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---------- 文件树区域 ----------
        splitter_main = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 文件树工具栏
        tree_toolbar = QHBoxLayout()
        btn_up = QPushButton("⬆ 上级")
        btn_up.clicked.connect(self.go_up_directory)
        tree_toolbar.addWidget(btn_up)
        tree_toolbar.addStretch()
        left_layout.addLayout(tree_toolbar)

        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(QDir.homePath())
        self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setRootIndex(self.tree_model.index(QDir.homePath()))
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(False)
        self.tree_view.doubleClicked.connect(self.on_tree_double_clicked)

        left_layout.addWidget(self.tree_view)

        # 意见输入区域
        self.opinion_group = QGroupBox("💬 功能改进意见")
        opinion_layout = QVBoxLayout(self.opinion_group)
        self.opinion_input = QTextEdit()
        self.opinion_input.setPlaceholderText("请输入程序功能问题或改进意见...")
        self.opinion_input.setMaximumHeight(100)
        opinion_layout.addWidget(self.opinion_input)

        self.btn_send_opinion = QPushButton("📤 发送意见给AI")
        self.btn_send_opinion.clicked.connect(self.send_custom_opinion)
        opinion_layout.addWidget(self.btn_send_opinion)

        left_layout.addWidget(self.opinion_group)

        splitter_main.addWidget(left_panel)

        # ---------- 右侧区域 ----------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 标题栏
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 3, 5, 3)
        self.btn_run = QPushButton("▶ 运行")
        self.btn_run.setEnabled(False)
        self.btn_run.setFixedWidth(80)
        self.btn_run.clicked.connect(self.run_current_file)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
            }
        """)
        title_layout.addWidget(self.btn_run)

        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setStyleSheet("background: #f0f0f0; border: none; padding: 4px 8px; font-weight: bold; font-size: 12px; border-radius: 3px;")
        self.path_display.setPlaceholderText("未打开文件")
        self.path_display.setToolTip("")
        self.path_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_layout.addWidget(self.path_display)

        right_layout.addLayout(title_layout)

        # 主分割：编辑器+大纲，输出+修改记录
        main_splitter = QSplitter(Qt.Vertical)

        # 编辑器 + 大纲
        h_splitter = QSplitter(Qt.Horizontal)
        self.editor = CodeEditor()
        h_splitter.addWidget(self.editor)

        right_panel2 = QWidget()
        right_layout2 = QVBoxLayout(right_panel2)
        right_layout2.setContentsMargins(0, 0, 0, 0)
        right_layout2.addWidget(QLabel("📖 结构大纲"))
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        right_layout2.addWidget(self.tree_widget)
        h_splitter.addWidget(right_panel2)
        h_splitter.setSizes([600, 200])
        main_splitter.addWidget(h_splitter)

        # 输出 + 修改记录
        bottom_splitter = QSplitter(Qt.Vertical)

        # 运行输出区域
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(5, 3, 5, 3)

        output_header = QHBoxLayout()
        output_header.setContentsMargins(0, 0, 0, 0)
        output_header.addWidget(QLabel("📟 运行输出"))

        self.btn_feedback_ai = QPushButton("🤖 向AI反馈错误")
        self.btn_feedback_ai.setEnabled(False)
        self.btn_feedback_ai.clicked.connect(self.send_error_to_ai)
        self.btn_feedback_ai.setFixedWidth(120)
        output_header.addWidget(self.btn_feedback_ai)

        self.test_input = QLineEdit("功能性测试")
        self.test_input.setFixedWidth(150)
        self.test_input.setPlaceholderText("输入测试消息...")
        output_header.addWidget(self.test_input)

        self.btn_test_plugin = QPushButton("📡 测试插件")
        self.btn_test_plugin.setFixedWidth(90)
        self.btn_test_plugin.clicked.connect(self.test_plugin_connection)
        output_header.addWidget(self.btn_test_plugin)

        # ---- 优化功能行：复选框 + 排除后缀输入框 + 优化按钮 ----
        optimize_layout = QHBoxLayout()
        self.checkbox_send_folder = QCheckBox("发送当前文件夹文件")
        self.checkbox_send_folder.setChecked(False)
        optimize_layout.addWidget(self.checkbox_send_folder)

        self.exclude_ext_input = QLineEdit()
        self.exclude_ext_input.setPlaceholderText("排除后缀: .pyc, .log, .tmp")
        self.exclude_ext_input.setFixedWidth(180)
        self.exclude_ext_input.setToolTip("输入要排除的文件后缀，用逗号或空格分隔")
        optimize_layout.addWidget(self.exclude_ext_input)

        self.btn_optimize = QPushButton("⚡ 优化程序")
        self.btn_optimize.setFixedWidth(90)
        self.btn_optimize.clicked.connect(self.optimize_program)
        optimize_layout.addWidget(self.btn_optimize)
        optimize_layout.addStretch()

        output_header.addLayout(optimize_layout)

        output_header.addStretch()
        output_layout.addLayout(output_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setPlaceholderText("运行输出将显示在这里...")
        output_layout.addWidget(self.output_text)
        bottom_splitter.addWidget(output_container)

        # 修改记录区域
        history_container = QWidget()
        history_layout = QVBoxLayout(history_container)
        history_layout.setContentsMargins(5, 3, 5, 3)

        history_header = QHBoxLayout()
        history_header.setContentsMargins(0, 0, 0, 0)
        history_header.addWidget(QLabel("📝 修改记录"))
        self.btn_apply_selected = QPushButton("✅ 应用选中")
        self.btn_apply_selected.setEnabled(False)
        self.btn_apply_selected.clicked.connect(self.apply_selected_modification)
        self.btn_apply_selected.setFixedWidth(90)
        self.btn_undo_selected = QPushButton("↩ 撤销选中")
        self.btn_undo_selected.setEnabled(False)
        self.btn_undo_selected.clicked.connect(self.undo_selected_modification)
        self.btn_undo_selected.setFixedWidth(90)
        self.btn_apply_all = QPushButton("✅ 全部应用")
        self.btn_apply_all.setEnabled(False)
        self.btn_apply_all.clicked.connect(self.apply_all_modifications)
        self.btn_apply_all.setFixedWidth(90)
        self.btn_undo_all = QPushButton("↩ 全部撤销")
        self.btn_undo_all.setEnabled(False)
        self.btn_undo_all.clicked.connect(self.undo_all_modifications)
        self.btn_undo_all.setFixedWidth(90)
        history_header.addWidget(self.btn_apply_selected)
        history_header.addWidget(self.btn_undo_selected)
        history_header.addWidget(self.btn_apply_all)
        history_header.addWidget(self.btn_undo_all)
        history_header.addStretch()
        history_layout.addLayout(history_header)

        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QListWidget.SingleSelection)
        self.history_list.itemSelectionChanged.connect(self.on_history_selection_changed)
        history_layout.addWidget(self.history_list)

        bottom_splitter.addWidget(history_container)
        bottom_splitter.setSizes([300, 200])
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([500, 200])
        right_layout.addWidget(main_splitter)

        splitter_main.addWidget(right_panel)
        splitter_main.setSizes([300, 700])
        layout.addWidget(splitter_main)

        # ---- QProcess ----
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.on_stdout_ready)
        self.process.readyReadStandardError.connect(self.on_stderr_ready)
        self.process.finished.connect(self.on_process_finished)

    # ---------- 文件树操作 ----------
    def set_root_path(self, path):
        if not os.path.isdir(path):
            return
        self.current_root_path = path
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.directory_changed.emit(path)

    def go_up_directory(self):
        current_path = self.tree_model.filePath(self.tree_view.rootIndex())
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and os.path.isdir(parent_path):
            self.set_root_path(parent_path)

    def on_tree_double_clicked(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            self.set_root_path(path)
        elif os.path.isfile(path):
            from core import FileAnalyzer
            if FileAnalyzer.is_text_file(path):
                self.load_file(path)
            else:
                QMessageBox.information(self, "提示", "非文本文件无法预览")

    # ---------- 文件加载 ----------
    def load_file(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件不存在:\n{file_path}")
            return
        try:
            content = FileAnalyzer.read_text_file(file_path)
            self.current_file = file_path
            self.path_display.setText(file_path)
            self.path_display.setToolTip(file_path)
            self.btn_run.setEnabled(True)
            self.editor.set_plain_text(content)
            self.build_outline(content, file_path)
            self.output_text.clear()
            self.clear_history()
            self.btn_feedback_ai.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件:\n{str(e)}")

    # ---------- 结构大纲 ----------
    def build_outline(self, content, file_path):
        self.tree_widget.clear()
        ext = os.path.splitext(file_path)[1]
        symbols = SymbolParser.parse_symbols(content, ext)
        root = self.tree_widget.invisibleRootItem()
        current_class = None
        for sym_type, name, line_num in symbols:
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, line_num)
            if sym_type == 'class':
                item.setText(0, f"[C] {name} (行 {line_num})")
                item.setForeground(0, QBrush(QColor("#D32F2F")))
                root.addChild(item)
                current_class = item
            elif sym_type == 'method':
                item.setText(0, f"[F] {name} (行 {line_num})")
                item.setForeground(0, QBrush(QColor("#1976D2")))
                if current_class:
                    current_class.addChild(item)
                else:
                    root.addChild(item)
        self.tree_widget.expandAll()

    def on_tree_item_clicked(self, item, column):
        line_num = item.data(0, Qt.UserRole)
        if line_num:
            self.editor.jump_to_line(line_num)

    # ---------- 运行功能 ----------
    def run_current_file(self):
        if not self.current_file:
            return
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
            return

        self.output_text.clear()
        self.output_text.append(f"🚀 正在运行: {self.current_file}\n")
        self.output_text.append("-" * 60 + "\n")
        self.btn_run.setText("⏹ 停止")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 3px;
            }
        """)
        self.btn_feedback_ai.setEnabled(False)
        self.clear_history()

        self.process.setProgram(sys.executable)
        self.process.setArguments([self.current_file])
        self.process.setWorkingDirectory(os.path.dirname(self.current_file))
        self.process.start()

    def on_stdout_ready(self):
        data = self.process.readAllStandardOutput()
        text = data.data().decode('utf-8', errors='ignore')
        self.output_text.append(text)

    def on_stderr_ready(self):
        data = self.process.readAllStandardError()
        text = data.data().decode('utf-8', errors='ignore')
        self.output_text.append(f"<font color='red'>{text}</font>")

    def on_process_finished(self, exit_code, exit_status):
        self.btn_run.setText("▶ 运行")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
            }
        """)
        if exit_code == 0:
            self.output_text.append("\n✅ 运行完成 (退出码 0)")
            self.btn_feedback_ai.setEnabled(False)
        else:
            self.output_text.append(f"\n❌ 运行失败 (退出码 {exit_code})")
            self.btn_feedback_ai.setEnabled(True)
        self.output_text.append("-" * 60 + "\n")
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    # ---------- 通用文件收集（带后缀过滤） ----------
    def collect_py_files(self, root_dir, exclude_exts=[]):
        py_files = []
        for r, dirs, files in os.walk(root_dir):
            for f in files:
                if f.endswith('.py'):
                    full_path = os.path.join(r, f)
                    ext = os.path.splitext(f)[1].lower()
                    if ext in exclude_exts:
                        continue
                    try:
                        with open(full_path, 'r', encoding='utf-8') as pf:
                            content = pf.read()
                        rel_path = os.path.relpath(full_path, root_dir)
                        py_files.append({'path': rel_path, 'content': content})
                    except:
                        pass
        return py_files

    # ---------- 向AI反馈错误 ----------
    def send_error_to_ai(self):
        if not self.current_file:
            return
        error_text = ""
        for line in self.output_text.toPlainText().splitlines():
            if "❌" in line or "Traceback" in line or "Error" in line:
                error_text += line + "\n"
        if not error_text:
            error_text = self.output_text.toPlainText()

        try:
            with open(self.current_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件: {e}")
            return

        prompt = (
            f"以下Python程序运行出错，请根据错误信息修复代码，并返回修复后的完整文件内容。\n"
            f"错误信息：\n{error_text}\n\n"
            f"文件内容：\n```python\n{content}\n```\n"
            f"请按以下JSON格式返回修复后的文件列表（如果只修改了一个文件，列表只含一项）：\n"
            f'[{{"path": "{os.path.basename(self.current_file)}", "content": "修复后的完整代码"}}]\n'
            f"注意：只返回JSON，不要其他内容，确保代码缩进正确。"
        )
        self.current_request_type = 'fix_error'
        self._send_prompt_to_ai(prompt)

    # ---------- 优化程序功能 ----------
    def optimize_program(self):
        if not self.current_file:
            QMessageBox.warning(self, "提示", "请先打开一个文件")
            return

        send_folder = self.checkbox_send_folder.isChecked()
        current_dir = os.path.dirname(self.current_file)

        exclude_raw = self.exclude_ext_input.text().strip()
        exclude_exts = []
        if exclude_raw:
            parts = re.split(r'[,\s]+', exclude_raw)
            for p in parts:
                p = p.strip()
                if p:
                    if not p.startswith('.'):
                        p = '.' + p
                    exclude_exts.append(p.lower())

        if send_folder:
            py_files = self.collect_py_files(current_dir, exclude_exts)
            if not py_files:
                QMessageBox.information(self, "提示", "当前目录没有找到 Python 文件")
                return
            files_json = json.dumps(py_files, ensure_ascii=False, indent=2)
            prompt = (
                f"请对以下项目中的所有 Python 文件进行优化、重构和完善功能。\n"
                f"要求：改进代码质量、添加必要注释、修复潜在问题、增强功能。\n"
                f"注意：必须保持原有功能不变，只优化代码结构和可读性。\n\n"
                f"文件列表：\n{files_json}\n\n"
                f"请按以下JSON格式返回修改后的文件列表（可以新建文件、修改已有文件）：\n"
                f'[{{"path": "相对路径/文件名", "content": "修改后的完整文件内容"}}]\n'
                f"请确保至少返回一个文件，即使文件没有变化也请返回原内容。"
            )
        else:
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法读取文件: {e}")
                return
            prompt = (
                f"请对以下文件进行优化、重构和完善功能：\n"
                f"要求：改进代码质量、添加必要注释、修复潜在问题、增强功能。\n"
                f"注意：必须保持原有功能不变，只优化代码结构和可读性。\n\n"
                f"文件内容：\n```python\n{content}\n```\n"
                f"请按以下JSON格式返回修改后的文件列表（如果只修改了一个文件，列表只含一项）：\n"
                f'[{{"path": "{os.path.basename(self.current_file)}", "content": "修改后的完整代码"}}]\n'
                f"请确保至少返回一个文件，即使没有变化也请返回原内容。"
            )
        self.current_request_type = 'optimize'
        self._send_prompt_to_ai(prompt)

    # ---------- 发送意见给AI ----------
    def send_custom_opinion(self):
        opinion = self.opinion_input.toPlainText().strip()
        if not opinion:
            QMessageBox.warning(self, "提示", "请输入意见内容")
            return
        if not self.current_file:
            QMessageBox.warning(self, "提示", "请先打开一个文件")
            return

        send_folder = self.checkbox_send_folder.isChecked()
        current_dir = os.path.dirname(self.current_file)

        if send_folder:
            exclude_raw = self.exclude_ext_input.text().strip()
            exclude_exts = []
            if exclude_raw:
                parts = re.split(r'[,\s]+', exclude_raw)
                for p in parts:
                    p = p.strip()
                    if p:
                        if not p.startswith('.'):
                            p = '.' + p
                        exclude_exts.append(p.lower())

            py_files = self.collect_py_files(current_dir, exclude_exts)
            if not py_files:
                QMessageBox.information(self, "提示", "当前目录没有找到 Python 文件")
                return
            files_json = json.dumps(py_files, ensure_ascii=False, indent=2)
            prompt = (
                f"用户对以下项目提出了改进意见，请根据意见修改代码。\n"
                f"用户意见：\n{opinion}\n\n"
                f"项目文件列表：\n{files_json}\n"
                f"请根据意见修改相关文件，并返回修改后的文件列表（可以新建文件、修改已有文件）。\n"
                f"请按以下JSON格式返回（只返回JSON）：\n"
                f'[{{"path": "相对路径/文件名", "content": "修改后的完整文件内容"}}]\n'
                f"请确保至少返回一个文件，即使文件没有变化也请返回原内容。"
            )
        else:
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法读取文件: {e}")
                return
            prompt = (
                f"用户对当前文件提出了改进意见，请根据意见修改代码。\n"
                f"用户意见：\n{opinion}\n\n"
                f"当前文件内容：\n```python\n{content}\n```\n"
                f"请根据意见修改此文件，并返回修改后的文件内容。\n"
                f"请按以下JSON格式返回（只返回JSON）：\n"
                f'[{{"path": "{os.path.basename(self.current_file)}", "content": "修改后的完整文件内容"}}]\n'
                f"请确保至少返回一个文件。"
            )

        self.current_request_type = 'opinion_with_files'
        self._send_prompt_to_ai(prompt)

    # ---------- 统一的发送方法 ----------
    def _send_prompt_to_ai(self, prompt):
        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.critical(self, "错误", "Bridge 服务未启动")
            self.output_text.append("\n❌ Bridge 服务未启动，无法发送")
            return
        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            self.output_text.append("\n⚠️ 没有插件客户端连接，请确保插件已连接")
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "ai_request",
            "content": prompt,
            "message": "AI 请求"
        }
        try:
            bridge.send_to_all_clients(payload)
            self.output_text.append("\n📤 已发送请求给AI，等待响应...")
            self.btn_send_opinion.setEnabled(False)
            self.btn_optimize.setEnabled(False)
            self.btn_feedback_ai.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")
            self.output_text.append(f"\n❌ 发送失败: {str(e)}")

    # ---------- 插件联通测试 ----------
    def test_plugin_connection(self):
        test_text = self.test_input.text().strip()
        if not test_text:
            test_text = "功能性测试"
            self.test_input.setText(test_text)

        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.critical(self, "错误", "Bridge 服务未启动")
            self.output_text.append("\n❌ Bridge 服务未启动，无法发送测试消息")
            return
        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            self.output_text.append("\n⚠️ 没有插件客户端连接，请确保插件已连接")
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "test_message",
            "content": test_text,
            "message": "插件联通测试"
        }
        try:
            bridge.send_to_all_clients(payload)
            self.output_text.append(f"\n📤 已发送测试消息到插件: \"{test_text}\"")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送测试消息失败: {str(e)}")
            self.output_text.append(f"\n❌ 发送测试消息失败: {str(e)}")

    # ---------- 接收 AI 响应 ----------
    def handle_ai_response(self, text):
        try:
            data = extract_json_from_response(text)
            if isinstance(data, list):
                self.display_modifications(data)
            elif isinstance(data, dict):
                if 'files' in data and isinstance(data['files'], list):
                    self.display_modifications(data['files'])
                elif 'path' in data and 'content' in data:
                    self.display_modifications([data])
                else:
                    self.output_text.append("⚠️ AI响应格式无法识别")
            else:
                self.output_text.append("⚠️ AI响应格式不是列表或字典，无法解析")
        except Exception as e:
            self.output_text.append(f"⚠️ 解析AI响应失败: {str(e)}")
        finally:
            self.btn_feedback_ai.setEnabled(True)
            self.btn_optimize.setEnabled(True)
            self.btn_send_opinion.setEnabled(True)
            self.current_request_type = None

    # ---------- 修改记录管理 ----------
    def clear_history(self):
        self.history_list.clear()
        self.modification_history.clear()
        self.btn_apply_all.setEnabled(False)
        self.btn_undo_all.setEnabled(False)
        self.btn_apply_selected.setEnabled(False)
        self.btn_undo_selected.setEnabled(False)

    def update_history_list(self):
        self.history_list.clear()
        for idx, record in enumerate(self.modification_history):
            status = "✅ 已应用" if record['applied'] else "⏳ 待应用"
            item = QListWidgetItem(f"{os.path.basename(record['file_path'])}  {status}")
            item.setData(Qt.UserRole, idx)
            self.history_list.addItem(item)

    def on_history_selection_changed(self):
        selected = self.history_list.selectedItems()
        if selected:
            idx = selected[0].data(Qt.UserRole)
            record = self.modification_history[idx]
            self.btn_apply_selected.setEnabled(not record['applied'])
            self.btn_undo_selected.setEnabled(record['applied'])
        else:
            self.btn_apply_selected.setEnabled(False)
            self.btn_undo_selected.setEnabled(False)

    def apply_modification(self, idx):
        record = self.modification_history[idx]
        if record['applied']:
            return
        try:
            dir_path = os.path.dirname(record['file_path'])
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            with open(record['file_path'], 'w', encoding='utf-8') as f:
                f.write(record['new_content'])
            record['applied'] = True
            self.update_history_list()
            self.output_text.append(f"✅ 已应用修改: {os.path.basename(record['file_path'])}")
            if record['file_path'] == self.current_file:
                self.editor.set_plain_text(record['new_content'])
            self.btn_undo_all.setEnabled(True)
            self.on_history_selection_changed()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用修改失败: {e}")

    def undo_modification(self, idx):
        record = self.modification_history[idx]
        if not record['applied']:
            return
        try:
            with open(record['file_path'], 'w', encoding='utf-8') as f:
                f.write(record['original_content'])
            record['applied'] = False
            self.update_history_list()
            self.output_text.append(f"↩ 已撤销修改: {os.path.basename(record['file_path'])}")
            if record['file_path'] == self.current_file:
                self.editor.set_plain_text(record['original_content'])
            any_applied = any(r['applied'] for r in self.modification_history)
            self.btn_undo_all.setEnabled(any_applied)
            self.on_history_selection_changed()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"撤销修改失败: {e}")

    def apply_selected_modification(self):
        selected = self.history_list.selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        self.apply_modification(idx)

    def undo_selected_modification(self):
        selected = self.history_list.selectedItems()
        if not selected:
            return
        idx = selected[0].data(Qt.UserRole)
        self.undo_modification(idx)

    def apply_all_modifications(self):
        for i in range(len(self.modification_history)):
            if not self.modification_history[i]['applied']:
                self.apply_modification(i)
        self.btn_apply_all.setEnabled(False)

    def undo_all_modifications(self):
        for i in range(len(self.modification_history)):
            if self.modification_history[i]['applied']:
                self.undo_modification(i)
        self.btn_undo_all.setEnabled(False)

    def display_modifications(self, mod_list):
        self.clear_history()
        self.modification_history = []
        for item in mod_list:
            if isinstance(item, dict) and 'path' in item and 'content' in item:
                file_path = item['path']
                if not os.path.isabs(file_path):
                    file_path = os.path.join(os.path.dirname(self.current_file), file_path)
                orig_content = ""
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            orig_content = f.read()
                    except:
                        pass
                self.modification_history.append({
                    'file_path': file_path,
                    'original_content': orig_content,
                    'new_content': item['content'],
                    'applied': False
                })
        self.update_history_list()
        if self.modification_history:
            self.btn_apply_all.setEnabled(True)
            self.btn_undo_all.setEnabled(False)
            self.output_text.append(f"✅ 收到 {len(self.modification_history)} 个修改建议")