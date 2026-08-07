# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .model.debug_model import DebugModel
from .view.debug_view import DebugOutputView
from .controller.debug_controller import DebugController


class DebugWidget(QWidget):
    """Debug 模块入口 - 完全独立"""
    
    sig_feedback_sent = Signal(dict)   # 反馈发送给 AI
    sig_execution_done = Signal(str)   # 执行完成，参数：文件路径
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        print("[DEBUG-WIDGET] ========== DebugWidget 初始化开始 ==========")
        
        self.model = DebugModel(self)
        self.view = DebugOutputView(self)
        self.controller = DebugController(self.model, self.view, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        # 连接信号
        self.controller.sig_feedback_sent.connect(self.sig_feedback_sent.emit)
        self.controller.sig_execution_done.connect(self.sig_execution_done.emit)
        
        print("[DEBUG-WIDGET] DebugWidget 初始化完成")
    
    # ---------- API ----------
    def set_file_path(self, file_path: str):
        """设置当前要执行的文件路径"""
        self.controller.set_file_path(file_path)
    
    def get_file_path(self) -> str:
        """获取当前文件路径"""
        return self.controller.get_file_path()
    
    def run(self):
        """执行当前文件"""
        self.controller._on_run_clicked()
    
    def clear_output(self):
        """清空输出"""
        self.view.clear_output()
    
    def send_feedback(self):
        """发送反馈"""
        self.controller._on_feedback_clicked()
    
    def set_template(self, template_name: str):
        """设置当前模板"""
        self.controller.set_template(template_name)
    
    def get_output(self) -> str:
        """获取当前输出内容"""
        return self.view.get_output()