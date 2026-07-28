# -*- coding: utf-8 -*-
import sys
import os
import json
import re
from datetime import datetime
from PySide2.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, 
                               QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                               QSplitter, QListWidget, QTabWidget)
from PySide2.QtCore import QObject, Signal, Slot, Qt, QSettings
from PySide2.QtWebSockets import QWebSocketServer, QWebSocket
from PySide2.QtNetwork import QHostAddress

class BridgeServer(QObject):
    """WebSocket 通信桥梁服务端"""
    message_received = Signal(dict)

    def __init__(self, port=9002, parent=None):
        super().__init__(parent)
        self.server = QWebSocketServer("PySideExtensionBridge", QWebSocketServer.NonSecureMode, self)
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

    @Slot(dict)
    def send_to_extension(self, data_dict):
        msg = json.dumps(data_dict, ensure_ascii=False)
        for client in self.clients:
            client.sendTextMessage(msg)
        print(f"[WebSocket] 已向插件发送指令: {msg}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide 与 插件自动化代码同步工作台 (标准 API 结构纠正版)")
        self.resize(1300, 900)

        # 初始化配置持久化 (QSettings)
        self.settings = QSettings("AIWorkspace", "CodeSyncAppAPIModel")

        # 内存缓存所有接收到的文件内容
        self.received_files_cache = {}

        # 默认本地保存路径
        self.save_dir = os.path.join(os.getcwd(), "output_codes")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # 整个窗口的外层根布局
        root_layout = QVBoxLayout(self)

        # ==================== 顶级大 Tab 控件 ====================
        self.main_tab_widget = QTabWidget(self)
        self.main_tab_widget.setStyleSheet("QTabWidget::pane { border: 1px solid #ccc; } QTabBar::tab { font-weight: bold; padding: 8px 16px; font-size: 13px; }")

        # ==================== Tab 1：工作台与控制中心 ====================
        workspace_widget = QWidget(self)
        workspace_layout = QVBoxLayout(workspace_widget)

        # 1. 顶部控制与大输入框区
        top_layout = QVBoxLayout()
        
        command_label_layout = QHBoxLayout()
        command_label_layout.addWidget(QLabel("<b>✏️ 输入指令 (支持多行长文本输入):</b>", self))
        
        self.send_btn = QPushButton("发送命令给 AI", self)
        self.send_btn.setMaximumWidth(130)
        self.send_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 4px;")
        self.send_btn.clicked.connect(self.send_command_to_extension)
        command_label_layout.addWidget(self.send_btn)
        top_layout.addLayout(command_label_layout)

        self.command_input = QTextEdit(self)
        self.command_input.setMinimumHeight(100)
        self.command_input.setPlaceholderText("在此处输入要让 AI 执行的详细编程指令（将自动填充至标准 API 的 user.content 中）...")
        self.command_input.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #ffffff;")
        top_layout.addWidget(self.command_input)

        sub_ctrl_layout = QHBoxLayout()
        self.dir_btn = QPushButton("选择本地保存目录", self)
        self.dir_btn.setMaximumWidth(150)
        self.dir_btn.clicked.connect(self.select_save_directory)
        sub_ctrl_layout.addWidget(self.dir_btn)
        sub_ctrl_layout.addStretch()
        top_layout.addLayout(sub_ctrl_layout)

        workspace_layout.addLayout(top_layout)

        # 2. System Prompt 多 Tab 切换配置区
        prompt_main_layout = QVBoxLayout()
        prompt_top_layout = QHBoxLayout()
        prompt_top_layout.addWidget(QLabel("<b>⚙️ System Prompt 多场景配置 (自动填充至标准 API 的 system.content 中):</b>", self))
        
        self.save_prompt_btn = QPushButton("保存当前 Prompt", self)
        self.save_prompt_btn.setMaximumWidth(130)
        self.save_prompt_btn.clicked.connect(self.save_current_system_prompt)
        prompt_top_layout.addWidget(self.save_prompt_btn)
        prompt_main_layout.addLayout(prompt_top_layout)

        self.prompt_tab_widget = QTabWidget(self)
        self.prompt_editors = {}

        default_prompts = {
            "代码生成助手": (
                "你是一个代码生成助手。请严格按照以下JSON格式输出，不要输出任何Markdown标记或额外解释：\n"
                "{\n"
                "  \"files\": [\n"
                "    {\n"
                "      \"filename\": \"文件名1.py\",\n"
                "      \"code\": \"代码内容1\"\n"
                "    },\n"
                "    {\n"
                "      \"filename\": \"文件名2.py\",\n"
                "      \"code\": \"代码内容2\"\n"
                "    }\n"
                "  ]\n"
                "}"
            ),
            "代码重构与优化": (
                "你是一个代码重构专家。请对代码进行逻辑优化与结构重构，并严格按指定的 JSON 格式返回文件列表。"
            ),
            "通用技术问答": (
                "你是一个技术顾问。请提供清晰的技术解答，并将结果以 JSON 格式结构化输出。"
            )
        }

        for title, default_text in default_prompts.items():
            editor = QTextEdit(self)
            editor.setMinimumHeight(130)
            editor.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fffde7;")
            
            saved_text = self.settings.value(f"prompt_{title}", default_text)
            editor.setPlainText(saved_text)
            
            self.prompt_editors[title] = editor
            self.prompt_tab_widget.addTab(editor, title)

        prompt_main_layout.addWidget(self.prompt_tab_widget)
        workspace_layout.addLayout(prompt_main_layout)

        # 路径提示
        self.path_label = QLabel(f"当前本地保存路径: {self.save_dir}", self)
        self.path_label.setStyleSheet("color: #555; font-size: 11px; font-weight: bold; margin: 2px 0;")
        workspace_layout.addWidget(self.path_label)

        # 3. 下半部分：左侧文件索引与右侧同步运行日志
        middle_splitter = QSplitter(Qt.Horizontal, self)

        left_box = QWidget(self)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>📁 接收到的代码文件索引 (点击可跳转大屏预览):</b>", self))
        
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
        self.log_view.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fdfdfd;")
        right_layout.addWidget(self.log_view)
        middle_splitter.addWidget(right_box)

        middle_splitter.setSizes([400, 750])
        workspace_layout.addWidget(middle_splitter)

        # 将 Tab 1 添加到主 Tab 容器
        self.main_tab_widget.addTab(workspace_widget, "🛠️ 工作台与控制中心")

        # ==================== Tab 2：全页面大小的代码大屏预览中心 ====================
        preview_widget = QWidget(self)
        preview_layout = QVBoxLayout(preview_widget)
        
        preview_top_layout = QHBoxLayout()
        preview_top_layout.addWidget(QLabel("<b>📄 选中文件的全屏沉浸式代码观察:</b>", self))
        
        self.current_preview_file_label = QLabel("当前未选中任何文件", self)
        self.current_preview_file_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        preview_top_layout.addWidget(self.current_preview_file_label)
        preview_top_layout.addStretch()
        
        preview_layout.addLayout(preview_top_layout)

        self.code_preview_edit = QTextEdit(self)
        self.code_preview_edit.setReadOnly(True)
        self.code_preview_edit.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #fafafa;")
        preview_layout.addWidget(self.code_preview_edit)

        # 将 Tab 2 添加到主 Tab 容器
        self.main_tab_widget.addTab(preview_widget, "📂 代码大屏预览中心")

        # ==================== Tab 3：发送命令历史记录中心 ====================
        history_widget = QWidget(self)
        history_layout = QVBoxLayout(history_widget)
        
        history_top_layout = QHBoxLayout()
        history_top_layout.addWidget(QLabel("<b>📜 下发给插件的所有命令历史记录 (标准 API 结构视图):</b>", self))
        
        self.clear_history_btn = QPushButton("清空历史记录", self)
        self.clear_history_btn.setMaximumWidth(120)
        self.clear_history_btn.clicked.connect(lambda: self.history_view.clear())
        history_top_layout.addWidget(self.clear_history_btn)
        history_top_layout.addStretch()
        
        history_layout.addLayout(history_top_layout)

        self.history_view = QTextEdit(self)
        self.history_view.setReadOnly(True)
        self.history_view.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 12px; background-color: #fbfbfb;")
        history_layout.addWidget(self.history_view)

        # 将 Tab 3 添加到主 Tab 容器
        self.main_tab_widget.addTab(history_widget, "📜 发送命令历史")

        # 将主 Tab 放入根布局
        root_layout.addWidget(self.main_tab_widget)

        # 4. 启动 WebSocket 服务
        self.bridge = BridgeServer(port=9002, parent=self)
        self.bridge.message_received.connect(self.handle_extension_message)

        self.append_structured_log("系统就绪", "WebSocket 服务已在 ws://localhost:9002 启动监听。", "INFO")

    def save_current_system_prompt(self):
        current_index = self.prompt_tab_widget.currentIndex()
        current_title = self.prompt_tab_widget.tabText(current_index)
        editor = self.prompt_editors.get(current_title)
        
        if editor:
            text = editor.toPlainText()
            self.settings.setValue(f"prompt_{current_title}", text)
            self.append_structured_log("配置持久化", f"场景 [{current_title}] 的 System Prompt 已成功保存。", "CONFIG")

    def closeEvent(self, event):
        for title, editor in self.prompt_editors.items():
            self.settings.setValue(f"prompt_{title}", editor.toPlainText())
        event.accept()

    def select_save_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择代码保存文件夹", self.save_dir)
        if dir_path:
            self.save_dir = dir_path
            self.path_label.setText(f"当前本地保存路径: {self.save_dir}")
            self.append_structured_log("目录更改", f"本地保存路径已变更为: {self.save_dir}", "CONFIG")

    def send_command_to_extension(self):
        user_input = self.command_input.toPlainText().strip()
        if not user_input:
            return

        # 获取当前激活的 System Prompt 内容
        current_index = self.prompt_tab_widget.currentIndex()
        current_title = self.prompt_tab_widget.tabText(current_index)
        active_system_prompt = self.prompt_editors[current_title].toPlainText().strip()

        # 【核心调整】严格按照你要求的标准 API 结构构建 payload
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": active_system_prompt
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "response_format": {
                "type": "json_object"
            },
            "temperature": 0.1
        }
        
        self.bridge.send_to_extension(payload)
        
        # 记录到运行日志
        self.append_structured_log("指令发送", f"已下发标准 API 格式消息 (Prompt 场景: [{current_title}])", "SEND")
        
        # 将发送的命令完整记录到“发送命令历史” Tab 中
        self.append_command_history(current_title, payload)

        self.command_input.clear()

    def append_command_history(self, prompt_scene, payload_dict):
        """向【发送命令历史】Tab 中追加格式化记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pretty_json = json.dumps(payload_dict, ensure_ascii=False, indent=4)
        
        html = f"""
        <div style="border-bottom: 2px solid #ddd; margin-bottom: 12px; padding-bottom: 8px;">
            <div style="background-color: #e3f2fd; padding: 4px 8px; font-weight: bold; color: #0d47a1; margin-bottom: 4px;">
                🕒 时间: {timestamp} &nbsp;|&nbsp; ⚙️ Prompt 场景: [{prompt_scene}]
            </div>
            <pre style="background-color: #f5f5f5; padding: 8px; border: 1px solid #e0e0e0; margin: 0; color: #333;">{pretty_json}</pre>
        </div>
        """
        self.history_view.append(html)

    def clean_and_format_code(self, code_text):
        if not code_text:
            return ""
        code_text = code_text.replace('\r\n', '\n')
        lines = [line.rstrip() for line in code_text.split('\n')]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        cleaned_lines = []
        for line in lines:
            formatted_line = line.replace('\t', '    ')
            cleaned_lines.append(formatted_line)
        return '\n'.join(cleaned_lines)

    def append_structured_log(self, category, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#2196F3",
            "SUCCESS": "#4CAF50",
            "WARN": "#FF9800",
            "ERROR": "#F44336",
            "CONFIG": "#9C27B0",
            "SEND": "#00BCD4"
        }
        color = color_map.get(level, "#333")

        html = f"""
        <div style="border-bottom: 1px dashed #eee; margin-bottom: 4px; padding-bottom: 4px;">
            <span style="color: #888; font-size: 10px;">[{timestamp}]</span>
            <span style="color: {color}; font-weight: bold;">[{category}]</span>
            <span style="color: #333;">{message}</span>
        </div>
        """
        self.log_view.append(html)

    @Slot(dict)
    def handle_extension_message(self, data):
        action = data.get("action")
        
        # 兼容处理直接返回的文件列表或包装在其他字段中的数据
        files_data = []
        if isinstance(data, dict):
            if "files" in data:
                files_data = data.get("files", [])
            elif "action" in data and data["action"] == "save_files_batch":
                files_data = data.get("files", [])

        if files_data:
            self.append_structured_log("接收同步", f"收到来自插件的批量文件，共 {len(files_data)} 个。", "SUCCESS")

            for file_item in files_data:
                raw_filename = file_item.get("filename", "unnamed.py")
                raw_code = file_item.get("code", "")

                safe_filename = re.sub(r'[\\/*?:"<>|]', "", raw_filename).strip()
                if not safe_filename:
                    safe_filename = "unnamed_script.py"

                cleaned_code = self.clean_and_format_code(raw_code)
                self.received_files_cache[safe_filename] = cleaned_code

                existing_items = self.file_list_widget.findItems(safe_filename, Qt.MatchExactly)
                if not existing_items:
                    self.file_list_widget.addItem(safe_filename)

                file_path = os.path.join(self.save_dir, safe_filename)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_code)
                    self.append_structured_log("文件保存", f"成功保存文件: <b>{safe_filename}</b> -> {file_path}", "SUCCESS")
                except Exception as e:
                    self.append_structured_log("保存失败", f"文件 {safe_filename} 保存异常: {str(e)}", "ERROR")
            
        else:
            self.append_structured_log("通用消息", f"{json.dumps(data, ensure_ascii=False)}", "INFO")

    def on_file_item_clicked(self, item):
        filename = item.text()
        if filename in self.received_files_cache:
            self.code_preview_edit.setPlainText(self.received_files_cache[filename])
            self.current_preview_file_label.setText(f"当前预览: {filename}")
            self.main_tab_widget.setCurrentIndex(1)
        else:
            self.code_preview_edit.setPlainText("# 找不到该文件的内存缓存内容")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())