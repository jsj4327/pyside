# -*- coding: utf-8 -*-
import os
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QSplitter, QListWidget, QShortcut,
    QFileDialog,
)

from config.settings import DEFAULT_SAVE_DIR, DEFAULT_PORT
from core.bridge_server import BridgeServer
from core.file_manager import FileManager
from core.prompt_manager import PromptManager
from ui.widgets.code_editor import CodeEditor
from ui.widgets.log_viewer import LogViewer
from controllers.workspace_controller import WorkspaceController
from controllers.preview_controller import PreviewController


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide 与 插件自动化代码同步工作台 (原样保存版)")
        self.resize(1350, 950)

        # Core services
        self.file_mgr = FileManager(DEFAULT_SAVE_DIR)
        self.prompt_mgr = PromptManager()
        self.bridge = BridgeServer(port=DEFAULT_PORT, parent=self)

        # Root layout
        root_layout = QVBoxLayout(self)
        self.main_tab = QTabWidget(self)
        self.main_tab.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #ccc; } QTabBar::tab { font-weight: bold; padding: 8px 16px; font-size: 13px; }"
        )

        # === Tab1: Workspace ===
        ws_widget = QWidget()
        ws_layout = QVBoxLayout(ws_widget)

        top = QVBoxLayout()
        cmd_row = QHBoxLayout()
        cmd_row.addWidget(QLabel("<b>✏️ 输入指令 (将替换 Prompt 模板中的 $_$ 占位符):</b>"))
        self.send_btn = QPushButton("发送命令给 AI")
        self.send_btn.setMaximumWidth(130)
        self.send_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 4px;")
        cmd_row.addWidget(self.send_btn)
        top.addLayout(cmd_row)

        self.cmd_input = QTextEdit()
        self.cmd_input.setMinimumHeight(100)
        self.cmd_input.setPlaceholderText("在此处输入要让 AI 执行的详细编程指令...")
        self.cmd_input.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #ffffff;")
        top.addWidget(self.cmd_input)

        sub = QHBoxLayout()
        self.dir_btn = QPushButton("选择本地保存目录")
        self.dir_btn.setMaximumWidth(150)
        sub.addWidget(self.dir_btn)
        sub.addStretch()
        top.addLayout(sub)
        ws_layout.addLayout(top)

        # Prompt area
        prompt_main = QVBoxLayout()
        prompt_top = QHBoxLayout()
        prompt_top.addWidget(QLabel("<b>⚙️ Prompt 模板配置 (支持使用 $_$ 作为占位符):</b>"))
        self.save_prompt_btn = QPushButton("保存当前 Prompt")
        self.save_prompt_btn.setMaximumWidth(130)
        prompt_top.addWidget(self.save_prompt_btn)
        prompt_main.addLayout(prompt_top)

        self.prompt_tabs = QTabWidget()
        self.prompt_editors = {}
        for title in self.prompt_mgr.get_default_titles():
            ed = QTextEdit()
            ed.setMinimumHeight(120)
            ed.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fffde7;")
            ed.setPlainText(self.prompt_mgr.load_prompt(title))
            self.prompt_editors[title] = ed
            self.prompt_tabs.addTab(ed, title)
        prompt_main.addWidget(self.prompt_tabs)
        ws_layout.addLayout(prompt_main)

        self.path_label = QLabel(f"当前本地保存路径: {self.file_mgr.save_dir}")
        self.path_label.setStyleSheet("color: #555; font-size: 11px; font-weight: bold; margin: 2px 0;")
        ws_layout.addWidget(self.path_label)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("<b>📁 接收到的代码文件索引 (点击可跳转大屏预览):</b>"))
        self.file_list = QListWidget()
        ll.addWidget(self.file_list)
        splitter.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("<b>📋 结构化同步运行日志:</b>"))
        self.log_viewer = LogViewer()
        rl.addWidget(self.log_viewer)
        splitter.addWidget(right)

        ws_layout.addWidget(splitter)
        self.main_tab.addTab(ws_widget, "🛠️ 工作台与控制中心")

        # === Tab2: Preview ===
        pv_widget = QWidget()
        pv_layout = QVBoxLayout(pv_widget)
        pv_top = QHBoxLayout()
        pv_top.addWidget(QLabel("<b>📄 选中文件的全屏高亮代码编辑区:</b>"))
        self.preview_label = QLabel("当前未选中任何文件")
        self.preview_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        pv_top.addWidget(self.preview_label)
        pv_top.addStretch()
        self.save_preview_btn = QPushButton("💾 保存修改 (Ctrl+S)")
        self.save_preview_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 4px 10px;")
        pv_top.addWidget(self.save_preview_btn)
        pv_layout.addLayout(pv_top)

        self.code_editor = CodeEditor()
        pv_layout.addWidget(self.code_editor)
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.code_editor)
        self.main_tab.addTab(pv_widget, "📂 代码大屏预览与编辑中心")

        # === Tab3: History ===
        hist_widget = QWidget()
        hl = QVBoxLayout(hist_widget)
        ht = QHBoxLayout()
        ht.addWidget(QLabel("<b>📜 下发给插件的所有命令历史记录:</b>"))
        self.clear_hist_btn = QPushButton("清空历史记录")
        self.clear_hist_btn.setMaximumWidth(120)
        ht.addWidget(self.clear_hist_btn)
        ht.addStretch()
        hl.addLayout(ht)
        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #fbfbfb;")
        hl.addWidget(self.history_view)
        self.main_tab.addTab(hist_widget, "📜 发送命令历史")

        root_layout.addWidget(self.main_tab)

        # Controllers
        self.ws_ctrl = WorkspaceController(self.bridge, self.prompt_mgr, self.log_viewer, self.history_view, self)
        self.pv_ctrl = PreviewController(self.file_mgr, self.code_editor, self.preview_label, self.main_tab, self.log_viewer, self)

        # Connect signals
        self.send_btn.clicked.connect(self._on_send_command)
        self.dir_btn.clicked.connect(self._on_select_dir)
        self.save_prompt_btn.clicked.connect(self._on_save_prompt)
        self.file_list.itemClicked.connect(lambda item: self.pv_ctrl.select_file(item.text()))
        self.save_preview_btn.clicked.connect(self.pv_ctrl.save_current)
        self.save_shortcut.activated.connect(self.pv_ctrl.save_current)
        self.clear_hist_btn.clicked.connect(self.history_view.clear)
        self.bridge.message_received.connect(self._on_extension_message)
        self.bridge.log_message.connect(lambda msg, lvl: self.log_viewer.append_log("WebSocket", msg, lvl))

        self.log_viewer.append_log("系统就绪", "WebSocket 服务已启动，已配置为原样保存接收到的代码内容。", "INFO")

    def _on_send_command(self):
        title = self.prompt_tabs.tabText(self.prompt_tabs.currentIndex())
        self.ws_ctrl.send_command(self.cmd_input.toPlainText(), title, self.prompt_editors)
        self.cmd_input.clear()

    def _on_select_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择代码保存文件夹", self.file_mgr.save_dir)
        if d:
            self.file_mgr.set_save_dir(d)
            self.path_label.setText(f"当前本地保存路径: {d}")
            self.ws_ctrl.on_dir_changed(d)

    def _on_save_prompt(self):
        idx = self.prompt_tabs.currentIndex()
        title = self.prompt_tabs.tabText(idx)
        editor = self.prompt_editors.get(title)
        self.ws_ctrl.save_prompt(title, editor)

    def _on_extension_message(self, data):
        files = data.get("files", []) if isinstance(data, dict) else []
        if not files:
            return
        self.log_viewer.append_log("接收同步", f"收到批量文件，共 {len(files)} 个。", "SUCCESS")
        for item in files:
            raw_name = item.get("filename", "unnamed.py")
            raw_code = item.get("code", "")
            safe = FileManager.sanitize_path(raw_name)
            final = FileManager.clean_raw_text(raw_code)
            try:
                self.file_mgr.save_file(safe, final)
                if not self.file_list.findItems(safe, Qt.MatchExactly):
                    self.file_list.addItem(safe)
                self.log_viewer.append_log("文件保存", f"成功原样保存文件: <b>{safe}</b>", "SUCCESS")
            except Exception as e:
                self.log_viewer.append_log("保存失败", str(e), "ERROR")

    def closeEvent(self, event):
        self.prompt_mgr.save_all(self.prompt_editors)
        event.accept()
