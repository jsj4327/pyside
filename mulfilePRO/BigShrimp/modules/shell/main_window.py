# -*- coding: utf-8 -*-
"""Shell：主窗口（UI 只调各模块 api）。"""
from datetime import datetime

from PySide2.QtCore import Qt, Slot
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QShortcut,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from modules.agent.api import AgentApi
from modules.bridge.api import BridgeApi
from modules.shell.components.code_editor.python_highlighter import (
    PythonSyntaxHighlighter,
)
from modules.workspace.api import WorkspaceApi


class MainWindow(QWidget):
    def __init__(
        self,
        bridge: BridgeApi,
        workspace: WorkspaceApi,
        agent: AgentApi,
        parent=None,
    ):
        super().__init__(parent)
        self.bridge = bridge
        self.workspace = workspace
        self.agent = agent

        self.setWindowTitle("PySide 与 插件自动化代码同步工作台 (原样保存版)")
        self.resize(1350, 950)

        self.current_preview_filename = None

        root_layout = QVBoxLayout(self)
        self.main_tab_widget = QTabWidget(self)
        self.main_tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #ccc; } "
            "QTabBar::tab { font-weight: bold; padding: 8px 16px; font-size: 13px; }"
        )

        self._build_workspace_tab()
        self._build_preview_tab()
        self._build_history_tab()
        root_layout.addWidget(self.main_tab_widget)

        self.bridge.files_received.connect(self.handle_files_received)
        self.append_structured_log(
            "系统就绪",
            "WebSocket 服务已启动，已配置为原样保存接收到的代码内容。",
            "INFO",
        )

    def _build_workspace_tab(self):
        workspace_widget = QWidget(self)
        workspace_layout = QVBoxLayout(workspace_widget)

        top_layout = QVBoxLayout()
        command_label_layout = QHBoxLayout()
        command_label_layout.addWidget(
            QLabel("<b>✏️ 输入指令 (将替换 Prompt 模板中的 $_$ 占位符):</b>", self)
        )
        self.send_btn = QPushButton("发送命令给 AI", self)
        self.send_btn.setMaximumWidth(130)
        self.send_btn.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 4px;"
        )
        self.send_btn.clicked.connect(self.send_command_to_extension)
        command_label_layout.addWidget(self.send_btn)
        top_layout.addLayout(command_label_layout)

        self.command_input = QTextEdit(self)
        self.command_input.setMinimumHeight(100)
        self.command_input.setPlaceholderText("在此处输入要让 AI 执行的详细编程指令...")
        self.command_input.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #ffffff;"
        )
        top_layout.addWidget(self.command_input)

        sub_ctrl_layout = QHBoxLayout()
        self.dir_btn = QPushButton("选择本地保存目录", self)
        self.dir_btn.setMaximumWidth(150)
        self.dir_btn.clicked.connect(self.select_save_directory)
        sub_ctrl_layout.addWidget(self.dir_btn)
        sub_ctrl_layout.addStretch()
        top_layout.addLayout(sub_ctrl_layout)
        workspace_layout.addLayout(top_layout)

        prompt_main_layout = QVBoxLayout()
        prompt_top_layout = QHBoxLayout()
        prompt_top_layout.addWidget(
            QLabel("<b>⚙️ Prompt 模板配置 (支持使用 $_$ 作为占位符):</b>", self)
        )
        self.save_prompt_btn = QPushButton("保存当前 Prompt", self)
        self.save_prompt_btn.setMaximumWidth(130)
        self.save_prompt_btn.clicked.connect(self.save_current_system_prompt)
        prompt_top_layout.addWidget(self.save_prompt_btn)
        prompt_main_layout.addLayout(prompt_top_layout)

        self.prompt_tab_widget = QTabWidget(self)
        self.prompt_editors = {}
        for title, text in self.agent.prompts.items():
            editor = QTextEdit(self)
            editor.setMinimumHeight(120)
            editor.setStyleSheet(
                "font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fffde7;"
            )
            editor.setPlainText(text)
            self.prompt_editors[title] = editor
            self.prompt_tab_widget.addTab(editor, title)
        prompt_main_layout.addWidget(self.prompt_tab_widget)
        workspace_layout.addLayout(prompt_main_layout)

        self.path_label = QLabel(f"当前本地保存路径: {self.workspace.save_dir}", self)
        self.path_label.setStyleSheet(
            "color: #555; font-size: 11px; font-weight: bold; margin: 2px 0;"
        )
        workspace_layout.addWidget(self.path_label)

        middle_splitter = QSplitter(Qt.Horizontal, self)
        left_box = QWidget(self)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(
            QLabel("<b>📁 接收到的代码文件索引 (点击可跳转大屏预览):</b>", self)
        )
        self.file_list_widget = QListWidget(self)
        self.file_list_widget.itemClicked.connect(self.on_file_item_clicked)
        left_layout.addWidget(self.file_list_widget)
        middle_splitter.addWidget(left_box)

        right_box = QWidget(self)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>📋 结构化同步运行日志:</b>", self))
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fdfdfd;"
        )
        right_layout.addWidget(self.log_view)
        middle_splitter.addWidget(right_box)
        workspace_layout.addWidget(middle_splitter)

        self.main_tab_widget.addTab(workspace_widget, "🛠️ 工作台与控制中心")

    def _build_preview_tab(self):
        preview_widget = QWidget(self)
        preview_layout = QVBoxLayout(preview_widget)
        preview_top_layout = QHBoxLayout()
        preview_top_layout.addWidget(
            QLabel("<b>📄 选中文件的全屏高亮代码编辑区:</b>", self)
        )
        self.current_preview_file_label = QLabel("当前未选中任何文件", self)
        self.current_preview_file_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        preview_top_layout.addWidget(self.current_preview_file_label)
        preview_top_layout.addStretch()
        self.save_preview_btn = QPushButton("💾 保存修改 (Ctrl+S)", self)
        self.save_preview_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 4px 10px;"
        )
        self.save_preview_btn.clicked.connect(self.save_current_preview_to_disk)
        preview_top_layout.addWidget(self.save_preview_btn)
        preview_layout.addLayout(preview_top_layout)

        self.code_preview_edit = QTextEdit(self)
        self.code_preview_edit.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #fafafa;"
        )
        self.highlighter = PythonSyntaxHighlighter(self.code_preview_edit.document())
        preview_layout.addWidget(self.code_preview_edit)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.code_preview_edit)
        self.save_shortcut.activated.connect(self.save_current_preview_to_disk)
        self.main_tab_widget.addTab(preview_widget, "📂 代码大屏预览与编辑中心")

    def _build_history_tab(self):
        history_widget = QWidget(self)
        history_layout = QVBoxLayout(history_widget)
        history_top_layout = QHBoxLayout()
        history_top_layout.addWidget(
            QLabel("<b>📜 下发给插件的所有命令历史记录:</b>", self)
        )
        self.clear_history_btn = QPushButton("清空历史记录", self)
        self.clear_history_btn.setMaximumWidth(120)
        self.clear_history_btn.clicked.connect(lambda: self.history_view.clear())
        history_top_layout.addWidget(self.clear_history_btn)
        history_top_layout.addStretch()
        history_layout.addLayout(history_top_layout)

        self.history_view = QTextEdit(self)
        self.history_view.setReadOnly(True)
        self.history_view.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #fbfbfb;"
        )
        history_layout.addWidget(self.history_view)
        self.main_tab_widget.addTab(history_widget, "📜 发送命令历史")

    def save_current_system_prompt(self):
        current_index = self.prompt_tab_widget.currentIndex()
        current_title = self.prompt_tab_widget.tabText(current_index)
        editor = self.prompt_editors.get(current_title)
        if editor:
            self.agent.set_prompt(current_title, editor.toPlainText(), persist=True)
            self.append_structured_log(
                "配置持久化", f"场景 [{current_title}] 的 Prompt 已保存。", "CONFIG"
            )

    def closeEvent(self, event):
        for title, editor in self.prompt_editors.items():
            self.agent.set_prompt(title, editor.toPlainText(), persist=False)
        self.agent.persist_all()
        event.accept()

    def select_save_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择代码保存文件夹", self.workspace.save_dir
        )
        if dir_path:
            self.workspace.set_save_dir(dir_path)
            self.path_label.setText(f"当前本地保存路径: {self.workspace.save_dir}")
            self.append_structured_log(
                "目录更改", f"保存路径变更为: {self.workspace.save_dir}", "CONFIG"
            )

    def send_command_to_extension(self):
        user_input = self.command_input.toPlainText().strip()
        if not user_input:
            return
        current_title = self.prompt_tab_widget.tabText(
            self.prompt_tab_widget.currentIndex()
        )
        editor = self.prompt_editors.get(current_title)
        if editor:
            self.agent.set_prompt(current_title, editor.toPlainText(), persist=False)

        final_system_content = self.agent.build_command(current_title, user_input)
        if not final_system_content:
            return

        self.bridge.send_to_extension(final_system_content)
        self.append_structured_log(
            "指令发送", f"已下发指令 (场景: [{current_title}])", "SEND"
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""<div style="border-bottom: 2px solid #ddd; margin-bottom: 12px; padding-bottom: 8px;">
<div style="background-color: #e3f2fd; padding: 4px 8px; font-weight: bold; color: #0d47a1;">🕒 {timestamp} | 场景: [{current_title}]</div>
<pre style="background: #f5f5f5; padding: 8px; margin: 0;">{final_system_content}</pre></div>"""
        self.history_view.append(html)
        self.command_input.clear()

    def append_structured_log(self, category, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#2196F3",
            "SUCCESS": "#4CAF50",
            "WARN": "#FF9800",
            "ERROR": "#F44336",
            "CONFIG": "#9C27B0",
            "SEND": "#00BCD4",
        }
        color = color_map.get(level, "#333")
        html = f"""<div style="border-bottom: 1px dashed #eee; padding-bottom: 4px; margin-bottom: 4px;">
<span style="color: #888; font-size: 10px;">[{timestamp}]</span>
<span style="color: {color}; font-weight: bold;">[{category}]</span>
<span style="color: #333;">{message}</span></div>"""
        self.log_view.append(html)

    @Slot(list)
    def handle_files_received(self, files):
        self.append_structured_log(
            "接收同步", f"收到批量文件，共 {len(files)} 个。", "SUCCESS"
        )
        results = self.workspace.save_received_files(files)
        for rel, ok, payload in results:
            if ok:
                if not self.file_list_widget.findItems(rel, Qt.MatchExactly):
                    self.file_list_widget.addItem(rel)
                self.append_structured_log(
                    "文件保存", f"成功原样保存文件: <b>{rel}</b>", "SUCCESS"
                )
            else:
                self.append_structured_log("保存失败", f"{rel}: {payload}", "ERROR")

    def on_file_item_clicked(self, item):
        filename = item.text()
        self.current_preview_filename = filename
        cached = self.workspace.get_cached(filename)
        if cached is not None:
            self.code_preview_edit.setPlainText(cached)
            self.current_preview_file_label.setText(f"当前编辑: {filename}")
            self.main_tab_widget.setCurrentIndex(1)

    def save_current_preview_to_disk(self):
        if not self.current_preview_filename:
            return
        current_code = self.code_preview_edit.toPlainText()
        ok, msg = self.workspace.save_file(self.current_preview_filename, current_code)
        if ok:
            self.append_structured_log(
                "手动保存",
                f"文件 <b>{self.current_preview_filename}</b> 已成功保存。",
                "SUCCESS",
            )
        else:
            self.append_structured_log("保存失败", msg, "ERROR")