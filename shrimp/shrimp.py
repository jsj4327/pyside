# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
import re
import subprocess
import sys

from PySide2.QtCore import QObject, QSettings, Qt, Signal, Slot
from PySide2.QtNetwork import QHostAddress
from PySide2.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide2.QtWebSockets import QWebSocket, QWebSocketServer
from PySide2.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QShortcut,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """简易实用的 Python 语法高亮器"""

    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
            "self",
            "async",
            "await",
        ]
        for word in keywords:
            pattern = re.compile(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#A31515"))
        self.highlighting_rules.append(
            (
                re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'),
                self.string_format,
            )
        )
        self.highlighting_rules.append(
            (
                re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"),
                self.string_format,
            )
        )

        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#795E26"))
        function_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append(
            (re.compile(r"\bdef\s+(\w+)"), function_format)
        )

        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#267F99"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append(
            (re.compile(r"\bclass\s+(\w+)"), class_format)
        )

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append(
            (re.compile(r"#[^\n]*"), comment_format)
        )

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))
        self.highlighting_rules.append(
            (re.compile(r"\b\d+\b"), number_format)
        )

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                if match.lastindex and match.lastindex > 0:
                    start = match.start(1)
                    end = match.end(1)
                self.setFormat(start, end - start, fmt)


class BridgeServer(QObject):
    """WebSocket 通信桥梁服务端"""

    message_received = Signal(dict)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self.server = QWebSocketServer(
            "PySideExtensionBridge", QWebSocketServer.NonSecureMode, self
        )
        self.clients = []

        if self.server.listen(QHostAddress.LocalHost, port):
            print(f"[WebSocket] 服务启动成功，监听端口: {port}")
            self.server.newConnection.connect(self._on_new_connection)
        else:
            print(f"[WebSocket] 启动失败: {self.server.errorString()}")

    def _on_new_connection(self):
        client = self.server.nextPendingConnection()
        client.textMessageReceived.connect(self._on_text_received)
        client.disconnected.connect(lambda: self._on_disconnected(client))
        self.clients.append(client)
        print("[WebSocket] 浏览器插件已连接")

    def _on_text_received(self, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            print(f"[WebSocket] 无法解析的非 JSON 消息: {message}")

    def _on_disconnected(self, client):
        if client in self.clients:
            self.clients.remove(client)
            client.deleteLater()
            print("[WebSocket] 浏览器插件已断开")

    @Slot(str)
    def send_to_extension(self, text_msg):
        for client in self.clients:
            client.sendTextMessage(text_msg)
        print(f"[WebSocket] 已向插件发送文本指令: {text_msg}")


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "PySide 与 插件自动化代码同步工作台 (原样保存版)"
        )
        self.resize(1350, 950)

        self.settings = QSettings("AIWorkspace", "CodeSyncAppRawSave")

        self.received_files_cache = {}
        self.current_preview_filename = None

        self.save_dir = os.path.join(os.getcwd(), "output_codes")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        root_layout = QVBoxLayout(self)

        self.main_tab_widget = QTabWidget(self)
        self.main_tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #ccc; } QTabBar::tab { font-weight: bold; padding: 8px 16px; font-size: 13px; }"
        )

        # ==================== Tab 1：工作台与控制中心 ====================
        workspace_widget = QWidget(self)
        workspace_layout = QVBoxLayout(workspace_widget)

        top_layout = QVBoxLayout()
        command_label_layout = QHBoxLayout()
        command_label_layout.addWidget(
            QLabel(
                "<b>✏️ 输入指令 (将替换 Prompt 模板中的 $_$ 占位符):</b>",
                self,
            )
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
        self.command_input.setPlaceholderText(
            "在此处输入要让 AI 执行的详细编程指令..."
        )
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

        # System Prompt 区
        prompt_main_layout = QVBoxLayout()
        prompt_top_layout = QHBoxLayout()
        prompt_top_layout.addWidget(
            QLabel(
                "<b>⚙️ Prompt 模板配置 (支持使用 $_$ 作为占位符):</b>",
                self,
            )
        )

        self.save_prompt_btn = QPushButton("保存当前 Prompt", self)
        self.save_prompt_btn.setMaximumWidth(130)
        self.save_prompt_btn.clicked.connect(self.save_current_system_prompt)
        prompt_top_layout.addWidget(self.save_prompt_btn)
        prompt_main_layout.addLayout(prompt_top_layout)

        self.prompt_tab_widget = QTabWidget(self)
        self.prompt_editors = {}

        default_prompts = {
            "代码生成助手": """{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个严谨的代码生成助手。请严格按照以下 JSON 格式输出，不要输出任何 Markdown 标记或额外解释：\\n\\n【核心要求】：\\n1. 代码字段（code）中必须完整保留规范的代码缩进结构。\\n2. 缩进统一使用 4 个空格。\\n3. 代码中的所有换行必须严格转义为 \\\\n，确保整个 JSON 结构合法且可被直接解析。\\n\\n【输出格式】：\\n{\\n  \\\"files\\\": [\\n    {\\n      \\\"filename\\\": \\\"文件名1.py\\\",\\n      \\\"code\\\": \\\"def foo():\\\\n    print('Hello World')\\\"\\n    }\\n  ]\\n}"
    },
    {
      "role": "user",
      "content": "$_$"
    }
  ],
  "response_format": {
    "type": "json_object"
  },
  "temperature": 0.1
}"""
        }

        for title, default_text in default_prompts.items():
            editor = QTextEdit(self)
            editor.setMinimumHeight(120)
            editor.setStyleSheet(
                "font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fffde7;"
            )
            saved_text = self.settings.value(f"prompt_{title}", default_text)
            editor.setPlainText(saved_text)
            self.prompt_editors[title] = editor
            self.prompt_tab_widget.addTab(editor, title)

        prompt_main_layout.addWidget(self.prompt_tab_widget)
        workspace_layout.addLayout(prompt_main_layout)

        self.path_label = QLabel(
            f"当前本地保存路径: {self.save_dir}", self
        )
        self.path_label.setStyleSheet(
            "color: #555; font-size: 11px; font-weight: bold; margin: 2px 0;"
        )
        workspace_layout.addWidget(self.path_label)

        middle_splitter = QSplitter(Qt.Horizontal, self)

        left_box = QWidget(self)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(
            QLabel(
                "<b>📁 接收到的代码文件索引 (点击可跳转大屏预览):</b>", self
            )
        )

        self.file_list_widget = QListWidget(self)
        self.file_list_widget.itemClicked.connect(
            self.on_file_item_clicked
        )
        left_layout.addWidget(self.file_list_widget)
        middle_splitter.addWidget(left_box)

        right_box = QWidget(self)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(
            QLabel("<b>📋 结构化同步运行日志:</b>", self)
        )

        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fdfdfd;"
        )
        right_layout.addWidget(self.log_view)
        middle_splitter.addWidget(right_box)

        workspace_layout.addWidget(middle_splitter)
        self.main_tab_widget.addTab(
            workspace_widget, "🛠️ 工作台与控制中心"
        )

        # ==================== Tab 2：代码大屏预览与编辑中心 ====================
        preview_widget = QWidget(self)
        preview_layout = QVBoxLayout(preview_widget)

        preview_top_layout = QHBoxLayout()
        preview_top_layout.addWidget(
            QLabel("<b>📄 选中文件的全屏高亮代码编辑区:</b>", self)
        )

        self.current_preview_file_label = QLabel(
            "当前未选中任何文件", self
        )
        self.current_preview_file_label.setStyleSheet(
            "color: #D32F2F; font-weight: bold;"
        )
        preview_top_layout.addWidget(self.current_preview_file_label)

        preview_top_layout.addStretch()

        self.save_preview_btn = QPushButton("💾 保存修改 (Ctrl+S)", self)
        self.save_preview_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 4px 10px;"
        )
        self.save_preview_btn.clicked.connect(
            self.save_current_preview_to_disk
        )
        preview_top_layout.addWidget(self.save_preview_btn)

        preview_layout.addLayout(preview_top_layout)

        self.code_preview_edit = QTextEdit(self)
        self.code_preview_edit.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #fafafa;"
        )
        self.highlighter = PythonSyntaxHighlighter(
            self.code_preview_edit.document()
        )
        preview_layout.addWidget(self.code_preview_edit)

        # 绑定 Ctrl+S 快捷键
        self.save_shortcut = QShortcut(
            QKeySequence("Ctrl+S"), self.code_preview_edit
        )
        self.save_shortcut.activated.connect(
            self.save_current_preview_to_disk
        )

        self.main_tab_widget.addTab(
            preview_widget, "📂 代码大屏预览与编辑中心"
        )

        # ==================== Tab 3：发送命令历史记录中心 ====================
        history_widget = QWidget(self)
        history_layout = QVBoxLayout(history_widget)

        history_top_layout = QHBoxLayout()
        history_top_layout.addWidget(
            QLabel("<b>📜 下发给插件的所有命令历史记录:</b>", self)
        )

        self.clear_history_btn = QPushButton("清空历史记录", self)
        self.clear_history_btn.setMaximumWidth(120)
        self.clear_history_btn.clicked.connect(
            lambda: self.history_view.clear()
        )
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

        root_layout.addWidget(self.main_tab_widget)

        # 启动 WebSocket 服务
        self.bridge = BridgeServer(port=9002, parent=self)
        self.bridge.message_received.connect(
            self.handle_extension_message
        )

        self.append_structured_log(
            "系统就绪",
            "WebSocket 服务已启动，已配置为原样保存接收到的代码内容。",
            "INFO",
        )

    def save_current_system_prompt(self):
        current_index = self.prompt_tab_widget.currentIndex()
        current_title = self.prompt_tab_widget.tabText(current_index)
        editor = self.prompt_editors.get(current_title)
        if editor:
            self.settings.setValue(
                f"prompt_{current_title}", editor.toPlainText()
            )
            self.append_structured_log(
                "配置持久化",
                f"场景 [{current_title}] 的 Prompt 已保存。",
                "CONFIG",
            )

    def closeEvent(self, event):
        for title, editor in self.prompt_editors.items():
            self.settings.setValue(f"prompt_{title}", editor.toPlainText())
        event.accept()

    def select_save_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择代码保存文件夹", self.save_dir
        )
        if dir_path:
            self.save_dir = dir_path
            self.path_label.setText(f"当前本地保存路径: {self.save_dir}")
            self.append_structured_log(
                "目录更改", f"保存路径变更为: {self.save_dir}", "CONFIG"
            )

    def send_command_to_extension(self):
        user_input = self.command_input.toPlainText().strip()
        if not user_input:
            return
        current_title = self.prompt_tab_widget.tabText(
            self.prompt_tab_widget.currentIndex()
        )
        prompt_template = self.prompt_editors[current_title].toPlainText()

        final_system_content = (
            prompt_template.replace("$_$", user_input)
            if "$_$" in prompt_template
            else f"{prompt_template}\n{user_input}"
        )
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

    def clean_raw_text(self, code_text):
        """仅做基础的转义还原，保持内容原汁原味"""
        if not code_text:
            return ""
        code_text = (
            code_text.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
        return code_text

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

    @Slot(dict)
    def handle_extension_message(self, data):
        files_data = (
            data.get("files", []) if isinstance(data, dict) else []
        )
        if files_data:
            self.append_structured_log(
                "接收同步",
                f"收到批量文件，共 {len(files_data)} 个。",
                "SUCCESS",
            )
            for file_item in files_data:
                raw_filename = file_item.get("filename", "unnamed.py")
                raw_code = file_item.get("code", "")

                norm_filename = raw_filename.replace("\\", "/")
                safe_relative_path = (
                    os.path.join(
                        *[
                            re.sub(r'[\\/*?:"<>|]', "", p).strip()
                            for p in norm_filename.split("/")
                        ]
                    )
                    or "script.py"
                )

                file_path = os.path.join(self.save_dir, safe_relative_path)
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # 纯粹还原转义字符，不执行任何格式化或缩进修改
                    final_code = self.clean_raw_text(raw_code)

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(final_code)

                    self.received_files_cache[safe_relative_path] = final_code
                    if not self.file_list_widget.findItems(
                        safe_relative_path, Qt.MatchExactly
                    ):
                        self.file_list_widget.addItem(safe_relative_path)

                    self.append_structured_log(
                        "文件保存",
                        f"成功原样保存文件: <b>{safe_relative_path}</b>",
                        "SUCCESS",
                    )
                except Exception as e:
                    self.append_structured_log("保存失败", str(e), "ERROR")

    def on_file_item_clicked(self, item):
        filename = item.text()
        self.current_preview_filename = filename
        if filename in self.received_files_cache:
            self.code_preview_edit.setPlainText(
                self.received_files_cache[filename]
            )
            self.current_preview_file_label.setText(f"当前编辑: {filename}")
            self.main_tab_widget.setCurrentIndex(1)

    def save_current_preview_to_disk(self):
        if not self.current_preview_filename:
            return
        current_code = self.code_preview_edit.toPlainText()
        file_path = os.path.join(
            self.save_dir, self.current_preview_filename
        )
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(current_code)
            self.received_files_cache[
                self.current_preview_filename
            ] = current_code
            self.append_structured_log(
                "手动保存",
                f"文件 <b>{self.current_preview_filename}</b> 已成功保存。",
                "SUCCESS",
            )
        except Exception as e:
            self.append_structured_log("保存失败", str(e), "ERROR")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())