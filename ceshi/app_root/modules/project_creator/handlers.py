# -*- coding:utf-8 -*-
import os
import sys
import re
from PySide2.QtCore import QProcess, QSettings
from PySide2.QtWidgets import QMessageBox
from PySide2.QtGui import QColor, QBrush
from PySide2.QtWidgets import QTreeWidgetItem
from PySide2.QtCore import Qt

from core import FileAnalyzer
from .prompt_builder import PromptBuilder
from ..source_viewer.symbol_parser import SymbolParser


class EventHandlers:
    def __init__(self, parent, controls):
        self.parent = parent
        self.ctrl = controls
        self.process = None
        self._init_process()
        self._current_feedback_prompt = ""
        self.current_request_type = ''

        self.ctrl['btn_feedback_ai'].setEnabled(True)
        self.ctrl['btn_view_feedback_prompt'].setEnabled(True)

    def _init_process(self):
        self.process = QProcess(self.parent)
        self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self.process.readyReadStandardError.connect(self._on_stderr_ready)
        self.process.finished.connect(self._on_process_finished)

    def on_file_selected(self, path):
        self._load_file(path)

    def on_directory_changed(self, path):
        self.ctrl['status_label'].setText(f"当前目录: {path}")
        has_file = bool(self.parent.current_file and os.path.exists(self.parent.current_file))
        self.ctrl['btn_improve'].setEnabled(has_file)
        self.ctrl['btn_view_improve_prompt'].setEnabled(has_file)

    def _load_file(self, file_path):
        if not os.path.exists(file_path):
            return
        try:
            content = FileAnalyzer.read_text_file(file_path)
            self.parent.current_file = file_path
            self.ctrl['file_path_display'].setText(os.path.basename(file_path))
            self.ctrl['code_editor'].set_plain_text(content)
            self.ctrl['btn_run'].setEnabled(True)
            self.ctrl['btn_improve'].setEnabled(True)
            self.ctrl['btn_view_improve_prompt'].setEnabled(True)
            self._update_outline()
            self.ctrl['output_text'].clear()
        except Exception as e:
            QMessageBox.warning(self.parent, "错误", f"无法加载文件: {str(e)}")

    def _update_outline(self):
        content = self.ctrl['code_editor'].toPlainText()
        ext = os.path.splitext(self.parent.current_file)[1] if self.parent.current_file else '.py'
        symbols = SymbolParser.parse_symbols(content, ext)
        tree = self.ctrl['outline_tree']
        tree.clear()
        root = tree.invisibleRootItem()
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
        tree.expandAll()

    def on_outline_clicked(self, item, column):
        line_num = item.data(0, Qt.UserRole)
        if line_num:
            self.ctrl['code_editor'].jump_to_line(line_num)

    def run_current_file(self):
        if not self.parent.current_file:
            return
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
            return

        self.ctrl['output_text'].clear()
        self.ctrl['output_text'].append(f"🚀 正在运行: {self.parent.current_file}\n")
        self.ctrl['output_text'].append("-" * 60 + "\n")
        self.ctrl['btn_run'].setText("⏹ 停止")
        self.ctrl['btn_run'].setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 12px;
                font-weight: bold;
                border-radius: 3px;
            }
        """)

        self.process.setProgram(sys.executable)
        self.process.setArguments([self.parent.current_file])
        self.process.setWorkingDirectory(os.path.dirname(self.parent.current_file))
        self.process.start()

    def _on_stdout_ready(self):
        data = self.process.readAllStandardOutput()
        text = data.data().decode('utf-8', errors='ignore')
        self.ctrl['output_text'].append(text)

    def _on_stderr_ready(self):
        data = self.process.readAllStandardError()
        text = data.data().decode('utf-8', errors='ignore')
        self.ctrl['output_text'].append(f"<font color='red'>{text}</font>")

    def _on_process_finished(self, exit_code, exit_status):
        self.ctrl['btn_run'].setText("▶ 运行")
        self.ctrl['btn_run'].setStyleSheet("""
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
            self.ctrl['output_text'].append("\n✅ 运行完成 (退出码 0)")
        else:
            self.ctrl['output_text'].append(f"\n❌ 运行失败 (退出码 {exit_code})")
        self.ctrl['output_text'].append("-" * 60 + "\n")
        self.ctrl['output_text'].verticalScrollBar().setValue(
            self.ctrl['output_text'].verticalScrollBar().maximum()
        )
        if self.parent.current_file:
            self._build_feedback_prompt()

    # ---------- 黑名单解析 ----------
    def _parse_blacklist(self):
        raw = self.ctrl['blacklist_input'].text().strip()
        if not raw:
            return []
        parts = re.split(r'[,\s]+', raw)
        exts = []
        for p in parts:
            p = p.strip()
            if p:
                if not p.startswith('.'):
                    p = '.' + p
                exts.append(p.lower())
        return exts

    # ---------- 上传内容获取 ----------
    def _get_upload_content(self, mode):
        if mode == 0:
            return ""

        selected_paths = self.parent.file_manager.get_selected_files()
        if not selected_paths:
            if mode == 1 and self.parent.current_file:
                selected_paths = [self.parent.current_file]
            elif mode == 2:
                current_dir = self.parent.file_manager.get_current_path()
                selected_paths = [current_dir] if os.path.isdir(current_dir) else []
            else:
                return ""

        blacklist = self._parse_blacklist()
        content_parts = []

        for path in selected_paths:
            if mode == 1 and os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in blacklist:
                    self.parent.controls['log_text'].append(f"⏭ 跳过黑名单文件: {os.path.basename(path)}")
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    rel_path = os.path.basename(path)
                    content_parts.append(f"文件: {rel_path}\n```python\n{content}\n```")
                except Exception as e:
                    self.parent.controls['log_text'].append(f"⚠️ 读取文件 {path} 失败: {e}")
            elif mode == 2 and os.path.isdir(path):
                files = self._collect_files_from_dir(path, blacklist)
                for file_path in files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        rel_path = os.path.relpath(file_path, path)
                        content_parts.append(f"文件: {rel_path}\n```python\n{content}\n```")
                    except Exception as e:
                        self.parent.controls['log_text'].append(f"⚠️ 读取文件 {file_path} 失败: {e}")
            else:
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in blacklist:
                        self.parent.controls['log_text'].append(f"⏭ 跳过黑名单文件: {os.path.basename(path)}")
                        continue
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        rel_path = os.path.basename(path)
                        content_parts.append(f"文件: {rel_path}\n```python\n{content}\n```")
                    except Exception as e:
                        self.parent.controls['log_text'].append(f"⚠️ 读取文件 {path} 失败: {e}")

        return "\n\n".join(content_parts) if content_parts else ""

    def _collect_files_from_dir(self, dir_path, blacklist):
        files = []
        for root, dirs, names in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', '.git']]
            for name in names:
                ext = os.path.splitext(name)[1].lower()
                if ext in blacklist:
                    continue
                if name.endswith('.py') or name.endswith('.txt') or name.endswith('.md'):
                    full = os.path.join(root, name)
                    if os.path.isfile(full):
                        files.append(full)
        return files

    # ---------- 反馈 Prompt 构建 ----------
    def _build_feedback_prompt(self):
        if not self.parent.current_file:
            self._current_feedback_prompt = ""
            return

        output_text = self.ctrl['output_text'].toPlainText().strip()
        if not output_text:
            output_text = "程序运行完成，无输出内容。"

        upload_mode = self._get_upload_mode()
        base_prompt = (
            f"以下为程序运行输出的完整结果，请根据此结果提供反馈或建议。\n"
            f"运行输出：\n{output_text}\n\n"
        )

        file_content = self._get_upload_content(upload_mode)
        if file_content:
            base_prompt += f"相关文件内容：\n{file_content}\n\n"

        base_prompt += (
            f"请按以下JSON格式返回修改后的文件列表（如果需要修改）：\n"
            f'[{{"path": "相对路径/文件名", "content": "修改后的完整代码"}}]\n'
            f"如果无需修改，可以返回空列表。\n"
            f"⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。\n"
            f"示例：'__init__.py' 应写为 '\\u005f\\u005finit\\u005f.py'。\n"
            f"请将整个JSON结构放在 ```json 代码块中返回。"
        )
        self._current_feedback_prompt = base_prompt

    def _get_upload_mode(self):
        if self.ctrl['radio_no_upload'].isChecked():
            return 0
        elif self.ctrl['radio_single_file'].isChecked():
            return 1
        else:
            return 2

    # ---------- 查看按钮 ----------
    def view_feedback_prompt(self):
        if not self._current_feedback_prompt:
            self._build_feedback_prompt()
        self.ctrl['prompt_display'].setPlainText(self._current_feedback_prompt)

    def view_build_prompt(self):
        desc = self.ctrl['desc_edit'].toPlainText().strip()
        if not desc:
            QMessageBox.warning(self.parent, "提示", "请先输入项目需求")
            return
        prompt = PromptBuilder.build_initial_prompt(desc)
        self.ctrl['prompt_display'].setPlainText(prompt)

    def view_improve_prompt(self):
        if not self.parent.current_file:
            QMessageBox.warning(self.parent, "提示", "请先在文件管理器中打开要改进的文件")
            return
        opinion = self.ctrl['desc_edit'].toPlainText().strip()
        if not opinion:
            QMessageBox.warning(self.parent, "提示", "请输入改进意见")
            return

        upload_mode = self._get_upload_mode()
        base_prompt = f"用户对以下程序提出了改进意见，请根据意见修改代码。\n用户意见：\n{opinion}\n\n"

        file_content = self._get_upload_content(upload_mode)
        if file_content:
            base_prompt += f"相关文件内容：\n{file_content}\n\n"

        base_prompt += (
            f"请按以下JSON格式返回修改后的文件列表：\n"
            f'[{{"path": "相对路径/文件名", "content": "修改后的完整文件内容"}}]\n'
            f"⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。\n"
            f"请将整个JSON结构放在 ```json 代码块中返回。"
        )
        self.ctrl['prompt_display'].setPlainText(base_prompt)

    # ---------- 发送请求 ----------
    def send_error_to_ai(self):
        if not self.parent.current_file:
            QMessageBox.warning(self.parent, "提示", "请先打开一个文件")
            return

        self._build_feedback_prompt()
        if not self._current_feedback_prompt:
            QMessageBox.warning(self.parent, "提示", "无法构建反馈请求")
            return

        self.current_request_type = 'feedback'
        self._send_general_request(self._current_feedback_prompt, "代码评审/反馈请求")

    def send_improve_request(self):
        if not self.parent.current_file:
            QMessageBox.warning(self.parent, "提示", "请先在文件管理器中打开要改进的文件")
            return
        opinion = self.ctrl['desc_edit'].toPlainText().strip()
        if not opinion:
            QMessageBox.warning(self.parent, "提示", "请输入改进意见")
            return

        upload_mode = self._get_upload_mode()
        base_prompt = f"用户对以下程序提出了改进意见，请根据意见修改代码。\n用户意见：\n{opinion}\n\n"
        file_content = self._get_upload_content(upload_mode)
        if file_content:
            base_prompt += f"相关文件内容：\n{file_content}\n\n"

        prompt = base_prompt + (
            f"请按以下JSON格式返回修改后的文件列表：\n"
            f'[{{"path": "相对路径/文件名", "content": "修改后的完整文件内容"}}]\n'
            f"⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。\n"
            f"请将整个JSON结构放在 ```json 代码块中返回。"
        )

        self.current_request_type = 'improve'
        self._send_general_request(prompt, "项目改进请求")

    def send_build_request(self):
        desc = self.ctrl['desc_edit'].toPlainText().strip()
        if not desc:
            QMessageBox.warning(self.parent, "提示", "请输入项目描述")
            return

        prompt = PromptBuilder.build_initial_prompt(desc)
        self.current_request_type = 'build'
        self._send_general_request(prompt, "项目构建请求")

    def _send_general_request(self, prompt, request_type_label):
        self.ctrl['log_text'].clear()
        self.ctrl['log_text'].append(f"📤 发送{request_type_label}...")
        if len(prompt) > 100:
            self.ctrl['log_text'].append(f"  Prompt 长度: {len(prompt)} 字符")
        else:
            self.ctrl['log_text'].append(f"  Prompt: {prompt[:80]}...")

        self.ctrl['prompt_display'].setPlainText(prompt)

        self.parent.stage = 'generating'
        self.ctrl['btn_build'].setEnabled(False)
        self.ctrl['btn_improve'].setEnabled(False)
        self.ctrl['btn_build'].setText("⏳ 处理中...")
        self.ctrl['progress_bar'].setVisible(True)
        self.ctrl['progress_bar'].setValue(10)
        self.parent.elapsed_seconds = 0
        self.parent.timer.start(1000)
        self.ctrl['status_label'].setText(f"⏳ {request_type_label}已发送，等待插件反馈...")

        self._send_to_ai(prompt, request_type_label)

    def _send_to_ai(self, message, request_type="AI请求"):
        main_win = self.parent.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.critical(self.parent, "错误", "Bridge服务未启动")
            self._reset_after_response()
            return

        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self.parent, "警告", "没有插件客户端连接")
            self._reset_after_response()
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "project_request",
            "content": message,
            "message": request_type
        }
        try:
            bridge.send_to_all_clients(payload)
            self.ctrl['log_text'].append("✅ 请求已发送，等待AI响应...")
            self.ctrl['progress_bar'].setValue(30)
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"发送失败: {str(e)}")
            self._reset_after_response()

    # ---------- 响应后处理 ----------
    def _reset_ui_state(self):
        self.ctrl['progress_bar'].setVisible(False)
        self.ctrl['progress_bar'].setValue(0)
        self.parent.timer.stop()
        self.ctrl['status_label'].setText("就绪")

    def _reset_state(self):
        self.parent.stage = 'idle'
        self.ctrl['btn_build'].setEnabled(True)
        self.ctrl['btn_build'].setText("🏗️ 构建")
        has_file = bool(self.parent.current_file and os.path.exists(self.parent.current_file))
        self.ctrl['btn_improve'].setEnabled(has_file)
        self.ctrl['progress_bar'].setVisible(False)
        self.ctrl['progress_bar'].setValue(0)
        self.parent.timer.stop()
        self.ctrl['status_label'].setText("就绪")
        self.current_request_type = ''

    def after_response(self):
        if self.current_request_type == 'build':
            self._reset_state()
        else:
            self._reset_ui_state()

    def _reset_after_response(self):
        self._reset_state()

    # ---------- 取消阻塞 ----------
    def unblock(self):
        self.parent.stage = 'idle'
        self.ctrl['btn_build'].setEnabled(True)
        self.ctrl['btn_build'].setText("🏗️ 构建")
        has_file = bool(self.parent.current_file and os.path.exists(self.parent.current_file))
        self.ctrl['btn_improve'].setEnabled(has_file)
        self.ctrl['progress_bar'].setVisible(False)
        self.ctrl['progress_bar'].setValue(0)
        self.parent.timer.stop()
        self.ctrl['status_label'].setText("就绪（已解除阻塞）")
        self.current_request_type = ''
        self.ctrl['log_text'].append("🔓 已取消阻塞，可以再次发起请求")

    def update_timer(self):
        self.parent.elapsed_seconds += 1
        self.ctrl['status_label'].setText(f"⏳ 等待AI响应... {self.parent.elapsed_seconds}s")

    def on_clear(self):
        self.ctrl['desc_edit'].clear()
        self.ctrl['prompt_display'].clear()
        self.ctrl['log_text'].clear()
        self.ctrl['output_text'].clear()
        self.ctrl['feedback_list'].clear()
        self.ctrl['feedback_content'].clear()
        self.parent.modification_manager.modification_history.clear()
        self.parent.current_file = ""
        self.ctrl['code_editor'].clear()
        self.ctrl['file_path_display'].setText("未打开文件")
        self.ctrl['btn_run'].setEnabled(False)
        self.ctrl['btn_improve'].setEnabled(False)
        self.ctrl['btn_view_improve_prompt'].setEnabled(False)
        self.ctrl['btn_apply_all'].setEnabled(False)
        self.ctrl['btn_undo_all'].setEnabled(False)
        self.ctrl['btn_apply_selected'].setEnabled(False)
        self.ctrl['btn_undo_selected'].setEnabled(False)
        self._current_feedback_prompt = ""
        self.current_request_type = ''
        self._reset_state()
        self.ctrl['status_label'].setText("已清空")