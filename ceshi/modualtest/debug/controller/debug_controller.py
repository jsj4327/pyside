# -*- coding:utf-8 -*-
from PySide2.QtCore import QObject, Signal
from PySide2.QtWidgets import QApplication, QWidget, QMessageBox
import os
import sys
import re

from ..core.executor import PythonExecutor
from ..core.feedback_builder import FeedbackBuilder
from ..core.template_provider import TemplateProvider


class DebugController(QObject):
    """Debug 控制器"""
    
    sig_feedback_sent = Signal(dict)
    sig_execution_done = Signal(str)
    
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
            print(f"[DEBUG-CONTROLLER] {error_msg}")
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
        print(f"[DEBUG-CONTROLLER] 执行错误: {error_msg}")
    
    def _on_feedback_clicked(self):
        output = self.view.get_output()
        if not output or len(output.strip()) < 10:
            QMessageBox.warning(self.view, "提示", "没有可反馈的内容，请先执行一个文件")
            return
        
        placeholder_text = self.view.get_placeholder_text()
        
        template_name = self.view.get_current_template()
        template_content = self.view.get_template_content(template_name) if template_name else ""
        
        file_path = self.model.current_file or ""
        file_content = self._read_file_content(file_path)
        
        feedback_text = self._build_feedback_text(
            file_path=file_path,
            file_content=file_content,
            output=output,
            placeholder=placeholder_text,
            template=template_content
        )
        
        self.sig_feedback_sent.emit({
            'type': 'debug_feedback',
            'content': feedback_text,
            'file_path': file_path,
            'placeholder': placeholder_text,
            'template': template_name
        })
        
        self.view.append_output("\n[OK] 反馈已发送到 AI 助手\n", "info")
        self.view.update_status("idle", "反馈已发送")
        self.view.clear_placeholder()
    
    def _read_file_content(self, file_path: str) -> str:
        if not file_path or not os.path.exists(file_path):
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
    
    def _replace_placeholders(self, text: str, placeholder_text: str) -> str:
        if not text:
            return text
        
        if placeholder_text:
            result = text.replace('{$1}', placeholder_text)
            result = result.replace('{ $1 }', placeholder_text)
            result = result.replace('{$ 1}', placeholder_text)
        else:
            result = text.replace('{$1}', '')
            result = result.replace('{ $1 }', '')
            result = result.replace('{$ 1}', '')
        
        return result
    
    def _build_feedback_text(self, file_path: str, file_content: str, output: str, 
                             placeholder: str = "", template: str = None) -> str:
        parts = []
        parts.append("=" * 60)
        parts.append("【调试执行反馈】")
        parts.append("=" * 60)
        parts.append("")
        
        if file_path:
            parts.append(f"文件: {os.path.basename(file_path)}")
            parts.append(f"路径: {file_path}")
            parts.append("")
        
        if file_content:
            parts.append("【文件内容】")
            parts.append("```python")
            parts.append(file_content)
            parts.append("```")
            parts.append("")
        
        parts.append("【执行输出】")
        parts.append("```")
        parts.append(output)
        parts.append("```")
        parts.append("")
        
        if template:
            parts.append("=" * 60)
            parts.append("【分析要求】")
            parts.append("=" * 60)
            
            filled_template = self._replace_placeholders(template, placeholder)
            
            if placeholder and '{$1}' not in template:
                filled_template += f"\n\n【用户补充信息】\n{placeholder}"
            
            parts.append(filled_template)
        else:
            parts.append("请分析以上输出内容")
            if placeholder:
                parts.append(f"\n【用户补充信息】\n{placeholder}")
        
        return "\n".join(parts)
    
    def _find_file_browser(self):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'browser'):
                return getattr(widget, 'browser')
            for child in widget.findChildren(QWidget):
                class_name = child.__class__.__name__
                if 'FileBrowser' in class_name or 'Browser' in class_name:
                    return child
        return None
    
    def _on_template_changed(self, template_name: str):
        self.model.set_current_template(template_name)
    
    def _on_template_edited(self, template_name: str, new_content: str):
        print(f"[DEBUG-CONTROLLER] 模板已编辑: {template_name}")