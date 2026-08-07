# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal
from PySide2.QtWidgets import QMessageBox, QDialog
import os
import sys

from ..core.executor import PythonExecutor
from ..core.feedback_builder import FeedbackBuilder
from ..core.template_provider import TemplateProvider


class DebugController(QObject):
    """Debug 控制器"""

    sig_feedback_sent = Signal(dict)
    sig_execution_done = Signal(str)
    sig_log_message = Signal(str, str)  # 日志信号

    def __init__(self, model, view, parent=None):
        super().__init__(parent)
        self.model = model
        self.view = view
        self.executor = PythonExecutor(self)
        self.feedback_builder = FeedbackBuilder(self)
        self.template_provider = TemplateProvider(self)

        self._connect_signals()
        self._initialize_view()

    def _connect_signals(self):
        self.view.sig_run_clicked.connect(self._on_run_clicked)
        self.view.sig_feedback_clicked.connect(self._on_feedback_clicked)
        self.view.sig_preview_clicked.connect(self._on_preview_clicked)
        self.view.sig_template_changed.connect(self._on_template_changed)
        self.view.sig_template_edited.connect(self._on_template_edited)

        self.executor.sig_started.connect(self._on_execution_started)
        self.executor.sig_output_received.connect(self._on_output_received)
        self.executor.sig_finished.connect(self._on_execution_finished)
        self.executor.sig_error.connect(self._on_execution_error)

    def _initialize_view(self):
        self.view.refresh_templates()
        if self.model.current_file:
            self.view.set_file_info(self.model.current_file)
        self.view.update_status("idle", "就绪")

    def set_file_path(self, file_path: str):
        self.model.set_current_file(file_path)
        self.view.set_file_info(file_path)

    def get_file_path(self) -> str:
        return self.model.current_file

    def set_template(self, template_name: str):
        self.model.set_current_template(template_name)

    # ==================== 执行相关 ====================

    def _on_run_clicked(self):
        file_path = self.model.current_file

        if not file_path:
            QMessageBox.warning(self.view, "提示", "请先选择一个 Python 文件")
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(self.view, "提示", f"文件不存在: {file_path}")
            return

        if not file_path.endswith('.py'):
            QMessageBox.warning(self.view, "提示", "请选择一个 Python (.py) 文件")
            return

        if not os.access(file_path, os.R_OK):
            QMessageBox.warning(self.view, "提示", f"文件不可读: {file_path}")
            return

        try:
            self.view.clear_output()
            self.view.append_output(f"> {sys.executable} {file_path}\n", "info")
            self.view.append_separator()
            self.executor.run(file_path)
        except Exception as e:
            error_msg = f"执行异常: {str(e)}"
            self.view.append_output(f"[X] {error_msg}\n", "err")
            self.view.update_status("error", error_msg)

    def _on_execution_started(self, file_path: str):
        self.model.set_running(True)
        filename = os.path.basename(file_path)
        self.view.update_status("running", f"正在执行: {filename}")

    def _on_output_received(self, text: str, output_type: str):
        if text:
            self.view.append_output(text, output_type)

    def _on_execution_finished(self, exit_code: int, duration: float):
        self.model.set_running(False)
        self.view.append_separator()

        if exit_code == 0:
            self.view.append_output(f"[OK] 进程退出，返回码: {exit_code}\n", "out")
            self.view.update_status("done", "执行完成")
        else:
            self.view.append_output(f"[X] 进程退出，返回码: {exit_code}\n", "err")
            self.view.update_status("error", "执行失败")

        self.view.set_exit_info(exit_code, duration)
        self.sig_execution_done.emit(self.model.current_file)

    def _on_execution_error(self, error_msg: str):
        self.model.set_running(False)
        self.view.append_output(f"[X] {error_msg}\n", "err")
        self.view.update_status("error", error_msg)
        self.view.set_run_enabled(True)

    # ==================== 预览功能 ====================

    def _on_preview_clicked(self):
        """预览反馈内容 - 只加载模板，不加载执行输出和附加内容"""
        # 1. 获取用户输入
        user_input = self.view.get_placeholder_text()

        if not user_input:
            QMessageBox.warning(
                self.view,
                "占位符为空",
                "请在占位符输入框中输入内容后再预览。\n\n"
                "提示：输入的内容将替换模板中的 {$1} 位置。"
            )
            return

        # 2. 获取模板内容
        template_name = self.view.get_current_template()
        template_content = self.view.get_template_content(template_name) if template_name else ""

        if not template_content:
            QMessageBox.warning(self.view, "模板错误", "模板内容为空，请检查模板文件。")
            return

        # 3. 检查模板中是否有 {$1}
        if '{$1}' not in template_content:
            QMessageBox.warning(
                self.view,
                "模板错误",
                f"模板 '{template_name}' 中没有找到 {{$1}} 占位符，请添加后再预览。\n\n"
                "提示：在模板中使用 {{$1}} 表示用户输入内容插入的位置。"
            )
            return

        # 4. 打开预览对话框 - 只传递模板和用户输入
        from ..view.debug_view import FeedbackPreviewDialog
        dialog = FeedbackPreviewDialog(template_name, template_content, user_input, self.view)
        dialog.exec_()

    # ==================== 反馈功能 ====================

    def _on_feedback_clicked(self):
        """反馈按钮点击处理"""
        # 检查1: 模板中是否有 {$1}
        template_name = self.view.get_current_template()
        template_content = self.view.get_template_content(template_name) if template_name else ""

        if not template_content:
            QMessageBox.warning(self.view, "模板错误", "模板内容为空，请检查模板文件。")
            return

        if '{$1}' not in template_content:
            QMessageBox.warning(
                self.view,
                "模板错误",
                f"模板 '{template_name}' 中没有找到 {{$1}} 占位符，请添加后再发送。\n\n"
                "提示：在模板中使用 {{$1}} 表示用户输入内容插入的位置。"
            )
            return

        # 检查2: 执行输出是否为空
        full_output = self.view.get_full_output()
        if not full_output or len(full_output.strip()) < 10:
            QMessageBox.warning(self.view, "提示", "请先执行文件获取输出内容。")
            return

        # 获取用户输入（允许为空）
        user_input = self.view.get_placeholder_text()

        # 获取附加模式
        attach_mode = self.view.get_attach_mode()
        file_path = self.model.current_file or ""

        # 获取附加内容
        attached_content = self._get_attached_content(file_path, attach_mode)

        # 构建反馈内容
        feedback_text = self._build_feedback_text(
            template_content=template_content,
            user_input=user_input,
            full_output=full_output,
            file_path=file_path,
            attached_content=attached_content,
            attach_mode=attach_mode
        )

        # 发射信号（保留后期使用）
        self.sig_feedback_sent.emit({
            'type': 'debug_feedback',
            'content': feedback_text,
            'file_path': file_path,
            'template': template_name,
            'user_input': user_input,
            'full_output': full_output,
            'attach_mode': attach_mode,
            'attached_content': attached_content
        })

        # 发送日志（不显示UI提示）
        self.sig_log_message.emit("DEBUG_FEEDBACK", feedback_text)

        # 占位符输入框不清空，保留

    def _build_feedback_text(self, template_content: str, user_input: str, full_output: str,
                             file_path: str, attached_content: str, attach_mode: str) -> str:
        """构建反馈文本"""
        parts = []

        # 1. 文件信息
        if file_path:
            parts.append(f"文件: {os.path.basename(file_path)}")
            parts.append(f"路径: {file_path}")
            parts.append("")

        # 2. 执行输出
        parts.append("执行输出:")
        parts.append(full_output)
        parts.append("")

        # 3. 附加内容（位置后续确定，先放在执行输出后面）
        if attach_mode != "none" and attached_content:
            parts.append("=" * 40)
            parts.append("【附加内容】")
            parts.append("=" * 40)
            parts.append(attached_content)
            parts.append("")

        # 4. 模板（替换 {$1} 为用户输入）
        filled_template = template_content.replace('{$1}', user_input if user_input else "")
        parts.append(filled_template)

        return "\n".join(parts)

    def _get_attached_content(self, file_path: str, attach_mode: str) -> str:
        """根据附加模式获取附加内容"""
        if attach_mode == "none":
            return ""

        if attach_mode == "file":
            if file_path and os.path.exists(file_path):
                return self._read_file_content(file_path)
            return ""

        if attach_mode == "folder":
            if not file_path:
                return ""
            folder_path = os.path.dirname(file_path)
            if not os.path.exists(folder_path):
                return ""

            parts = []
            parts.append(f"文件夹内容: {folder_path}")
            parts.append("")

            py_files = [f for f in os.listdir(folder_path) if f.endswith('.py')]

            if not py_files:
                parts.append("(文件夹中没有 Python 文件)")
                return "\n".join(parts)

            for py_file in sorted(py_files):
                py_path = os.path.join(folder_path, py_file)
                content = self._read_file_content(py_path)
                if content:
                    parts.append(f"--- {py_file} ---")
                    parts.append(content)
                    parts.append("")

            return "\n".join(parts)

        return ""

    def _read_file_content(self, file_path: str) -> str:
        if not file_path or not os.path.exists(file_path):
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""

    def _on_template_changed(self, template_name: str):
        self.model.set_current_template(template_name)

    def _on_template_edited(self, template_name: str, new_content: str):
        print(f"[DEBUG-CONTROLLER] 模板已编辑: {template_name}")