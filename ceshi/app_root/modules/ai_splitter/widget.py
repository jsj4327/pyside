# -*- coding:utf-8 -*-
import os
import json
from PySide2.QtCore import Qt, QDir, Signal, QEvent
from PySide2.QtWidgets import QWidget

from .ui_builder import build_ui
from .file_navigator import FileNavigatorMixin
from .ai_handler import AIHandlerMixin


class AISplitterWidget(QWidget, FileNavigatorMixin, AIHandlerMixin):
    # 信号
    open_current_path_signal = Signal(str)
    preview_file_signal = Signal(str)
    directory_changed = Signal(str)  # 新增：目录变化信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file_path = None
        self.file_content = ""
        self.target_dir = ""
        self.max_tokens = 8000

        self.stage = 'idle'
        self.plan_data = None

        self._chunks = []
        self._target_dir = ""
        self._response_chunks = []
        self.current_chunk_index = 0

        # 构建 UI
        build_ui(self)

        # 绑定信号
        self._bind_signals()

        # 初始化导航
        self.set_current_dir(QDir.homePath())

    def _bind_signals(self):
        self.btn_browse.clicked.connect(self.on_browse)
        self.btn_target_dir.clicked.connect(self.on_target_dir)
        self.btn_analyze.clicked.connect(self.on_analyze)
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_up.clicked.connect(self.on_up_clicked)
        self.btn_back.clicked.connect(self.on_back_clicked)
        self.spin_max_tokens.valueChanged.connect(self.on_max_tokens_changed)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

        # 打开目录按钮
        self.btn_open_dir.clicked.connect(self._on_open_dir_clicked)
        # 双击树节点（预览文件）
        self.tree_view.doubleClicked.connect(self._on_tree_double_click)

        # ---- 启用源文件输入框的拖放 ----
        self.file_path_edit.setAcceptDrops(True)
        self.file_path_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        """处理源文件输入框的拖放事件"""
        if obj == self.file_path_edit:
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    urls = event.mimeData().urls()
                    if urls and urls[0].isLocalFile():
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Drop:
                if event.mimeData().hasUrls():
                    urls = event.mimeData().urls()
                    if urls and urls[0].isLocalFile():
                        file_path = urls[0].toLocalFile()
                        from core import FileAnalyzer
                        if FileAnalyzer.is_text_file(file_path):
                            self.load_file(file_path)
                            event.acceptProposedAction()
                            return True
                        else:
                            self.log_text.append(f"⚠️ 拖放的文件不是文本文件: {os.path.basename(file_path)}")
        return super().eventFilter(obj, event)

    def _on_open_dir_clicked(self):
        path = self.get_current_path()
        if os.path.exists(path):
            self.open_current_path_signal.emit(path)

    def get_current_path(self):
        return self.tree_model.filePath(self.tree_view.rootIndex())

    def _on_tree_double_click(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            self.set_current_dir(path)
        elif os.path.isfile(path):
            from core import FileAnalyzer
            if FileAnalyzer.is_text_file(path):
                self.preview_file_signal.emit(path)
            else:
                self.log_text.append(f"⚠️ 非文本文件，无法预览: {os.path.basename(path)}")

    # ----- 文件加载（公共） -----
    def load_file(self, file_path):
        from core import FileAnalyzer
        try:
            self.file_content = FileAnalyzer.read_text_file(file_path)
            self.current_file_path = file_path
            self.file_path_edit.setText(file_path)
            self.log_text.append(f"已加载文件: {os.path.basename(file_path)} (字符数: {len(self.file_content)})")
            default_target = os.path.join(os.path.dirname(file_path), "split_output")
            self.target_dir_edit.setText(default_target)
            self.btn_analyze.setEnabled(True)
            self.stage = 'idle'
            self.plan_data = None
        except Exception as e:
            from PySide2.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"读取文件失败: {str(e)}")
            self.log_text.append(f"❌ 读取失败: {str(e)}")

    def on_browse(self):
        from PySide2.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要拆分的文件", "", "所有文件 (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def on_target_dir(self):
        from PySide2.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标目录", self.target_dir_edit.text() or QDir.homePath())
        if dir_path:
            self.target_dir_edit.setText(dir_path)

    def on_clear(self):
        self.log_text.clear()
        self.log_text.append("日志已清空")
        self.stage = 'idle'
        self.plan_data = None

    def on_max_tokens_changed(self, value):
        self.max_tokens = value

    # ---------- set_current_dir（发射目录变化信号） ----------
    def set_current_dir(self, path):
        if not os.path.isdir(path):
            return
        if not hasattr(self, 'history'):
            self.history = []
            self.history_index = -1
        if not self.history or self.history[-1] != path:
            if self.history_index != -1 and self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.update_back_button()
        # 发射目录变化信号（用于同步源码预览）
        self.directory_changed.emit(path)

    def update_back_button(self):
        self.btn_back.setEnabled(self.history_index > 0)

    def on_up_clicked(self):
        current_path = self.tree_model.filePath(self.tree_view.rootIndex())
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and os.path.exists(parent_path):
            self.set_current_dir(parent_path)

    def on_back_clicked(self):
        if self.history_index > 0:
            self.history_index -= 1
            prev_path = self.history[self.history_index]
            self.tree_view.setRootIndex(self.tree_model.index(prev_path))
            self.update_back_button()

    # ---------- AI 分析主流程 ----------
    def on_analyze(self):
        from PySide2.QtWidgets import QMessageBox
        if not self.file_content:
            QMessageBox.warning(self, "提示", "请先选择源文件")
            return
        target_dir = self.target_dir_edit.text().strip()
        if not target_dir:
            QMessageBox.warning(self, "提示", "请设置目标目录")
            return
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建目标目录失败: {str(e)}")
                return

        total_tokens = self.estimate_tokens(self.file_content)
        max_allowed = self.spin_max_tokens.value()
        self.log_text.append(f"文件 Token 数: {total_tokens}, 最大允许: {max_allowed}")
        if total_tokens > max_allowed:
            self.log_text.append("❌ 文件过大，无法生成整体重构方案，请增大最大Token限制或手动拆分文件")
            QMessageBox.warning(self, "提示", f"文件 Token 数 ({total_tokens}) 超出限制 ({max_allowed})，请增大限制或手动拆分文件。")
            return

        self.log_text.append("📤 请求重构方案...")
        self.stage = 'plan_requested'
        self.btn_analyze.setEnabled(False)
        self._request_plan()

    def _request_plan(self):
        prompt = (
            f"请分析以下文件内容，并给出一个重构方案。\n"
            f"文件内容：\n```\n{self.file_content}\n```\n"
            f"请按以下JSON格式返回重构方案（只返回JSON）：\n"
            f'{{"type": "plan", "plan_description": "方案描述", "file_structure": [{{"path": "相对路径/文件名", "description": "文件作用"}}]}}\n'
            f"⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。\n"
            f"示例：'__init__.py' 应写为 '\\u005f\\u005finit\\u005f.py'；'_internal' 应写为 '\\u005finternal'。\n"
            f"请将整个JSON结构放在 ```json 代码块中返回。"
        )
        self._send_to_ai(prompt)

    def _request_data(self):
        self.log_text.append("📤 请求生成重构文件...")
        self.stage = 'data_requested'
        self._response_chunks = []
        self.current_chunk_index = 0

        max_tokens = self.spin_max_tokens.value()
        lines = self.file_content.splitlines(keepends=True)
        chunks = []
        current_chunk = ""
        current_tokens = 0
        for line in lines:
            line_tokens = self.estimate_tokens(line)
            if current_tokens + line_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
                current_tokens = line_tokens
            else:
                current_chunk += line
                current_tokens += line_tokens
        if current_chunk:
            chunks.append(current_chunk)

        self._chunks = chunks
        if len(chunks) > 1:
            self.log_text.append(f"🔹 文件较大，拆分为 {len(chunks)} 批发送...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(chunks))
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setVisible(False)

        self._target_dir = self.target_dir_edit.text().strip()
        self._send_chunk()

    def _send_chunk(self):
        if self.current_chunk_index >= len(self._chunks):
            self.progress_bar.setVisible(False)
            self._merge_and_save()
            return

        chunk = self._chunks[self.current_chunk_index]
        plan_json = json.dumps(self.plan_data, ensure_ascii=False, indent=2)
        prompt = (
            f"根据以下重构方案，生成对应的文件内容。\n"
            f"方案：{plan_json}\n"
            f"请针对以下文件内容部分（第 {self.current_chunk_index+1}/{len(self._chunks)} 部分），生成该部分对应的文件列表。\n"
            f"文件内容部分：\n```\n{chunk}\n```\n"
            f"请按以下JSON格式返回（只返回JSON）：\n"
            f'{{"type": "files", "files": [{{"path": "相对路径/文件名", "content": "文件内容"}}]}}\n'
            f"⚠️ 重要：为了确保JSON数据在网页端正确传输，请将JSON字符串中所有下划线 '_' 字符替换为 Unicode 转义序列 '\\u005f'。\n"
            f"示例：'__init__.py' 应写为 '\\u005f\\u005finit\\u005f.py'；'_internal' 应写为 '\\u005finternal'。\n"
            f"请将整个JSON结构放在 ```json 代码块中返回。"
        )

        self._send_to_ai(prompt)
        self.log_text.append(f"📤 发送第 {self.current_chunk_index+1}/{len(self._chunks)} 批...")
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(self.current_chunk_index + 1)

    def _send_to_ai(self, message):
        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            from PySide2.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", "Bridge 服务未启动")
            return
        bridge = main_win.bridge_server
        if not bridge.clients:
            from PySide2.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "ai_request",
            "content": message,
            "message": "AI 拆分助手请求"
        }
        bridge.send_to_all_clients(payload)

    # ----- AI 响应处理（由 AIHandlerMixin 提供，但为了完整包含在此） -----
    def append_ai_result(self, result_text):
        if not result_text:
            return

        if self.stage == 'plan_requested':
            self._handle_plan_response(result_text)
        elif self.stage == 'data_requested':
            self._handle_data_response(result_text)
        else:
            self.log_text.append("⚠️ 未处于等待状态，忽略响应")

    def _handle_plan_response(self, text):
        from .ai_handler import AIHandlerMixin
        data = AIHandlerMixin._extract_json_from_response(self, text)
        if data and isinstance(data, dict) and data.get('type') == 'plan':
            self.plan_data = data
            self.log_text.append("✅ 重构方案解析成功")
            desc = data.get('plan_description', '')
            structure = data.get('file_structure', [])
            self.log_text.append(f"  方案描述: {desc}")
            self.log_text.append(f"  预计生成 {len(structure)} 个文件")
            self.stage = 'plan_received'
            self._request_data()
        else:
            self.log_text.append("⚠️ 未能提取有效的方案JSON，请检查AI响应格式")
            self._reset_analyze_button()

    def _handle_data_response(self, text):
        from .ai_handler import AIHandlerMixin
        data = AIHandlerMixin._extract_json_from_response(self, text)
        if data and isinstance(data, dict) and data.get('type') == 'files':
            files = data.get('files', [])
            if files:
                self._response_chunks.extend(files)
                self.log_text.append(f"✅ 收到第 {self.current_chunk_index+1} 批文件列表，共 {len(files)} 个文件")
            else:
                self.log_text.append("⚠️ 返回的文件列表为空")
        else:
            self.log_text.append("⚠️ 未能提取有效的文件数据JSON，请检查AI响应格式")

        self.current_chunk_index += 1
        if self.current_chunk_index < len(self._chunks):
            self._send_chunk()
        else:
            self.progress_bar.setVisible(False)
            self._merge_and_save()

    def _merge_and_save(self):
        if not self._response_chunks:
            self.log_text.append("⚠️ 没有收到任何有效的文件数据")
            self._reset_analyze_button()
            return

        file_map = {}
        for item in self._response_chunks:
            if isinstance(item, dict) and 'path' in item and 'content' in item:
                # 替换路径和内容中的 \u005f 为 _
                path = item['path'].replace('\\u005f', '_')
                content = item['content'].replace('\\u005f', '_')
                file_map[path] = content
        if not file_map:
            self.log_text.append("⚠️ 没有有效的文件条目")
            self._reset_analyze_button()
            return

        target_dir = self._target_dir
        if not target_dir:
            target_dir = self.target_dir_edit.text().strip()
        if not target_dir:
            self.log_text.append("⚠️ 目标目录未设置")
            self._reset_analyze_button()
            return

        success = 0
        for rel_path, content in file_map.items():
            full_path = os.path.join(target_dir, rel_path)
            dir_name = os.path.dirname(full_path)
            try:
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                success += 1
                self.log_text.append(f"✅ 创建文件: {rel_path}")
            except Exception as e:
                self.log_text.append(f"❌ 创建文件 {rel_path} 失败: {e}")

        self.log_text.append(f"🎉 拆分完成！共创建 {success} 个文件，保存于 {target_dir}")
        from PySide2.QtWidgets import QMessageBox
        QMessageBox.information(self, "完成", f"成功拆分并保存 {success} 个文件到目标目录。")
        self.stage = 'data_received'
        self._reset_analyze_button()

    def _reset_analyze_button(self):
        self.btn_analyze.setEnabled(True)

    def estimate_tokens(self, text):
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text, disallowed_special=()))
        except:
            pass
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)