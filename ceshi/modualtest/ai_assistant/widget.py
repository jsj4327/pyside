# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .model.model import AIAssistantModel
from .view.main_view import AIAssistantView
from .controller.controller import AIAssistantController


class AIAssistantWidget(QWidget):
    """AI 助手聚合入口 - 完全独立"""
    
    request_sent = Signal(dict)
    status_changed = Signal(str)
    log_output = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        print("[AIASSISTANT-DEBUG] AIAssistantWidget 初始化开始")
        
        self.model = AIAssistantModel(self)
        self.view = AIAssistantView(self)
        self.controller = AIAssistantController(self.model, self.view, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        # 连接信号
        self.model.sig_status_changed.connect(self.status_changed.emit)
        self.model.sig_log.connect(self.log_output.emit)
        
        print("[AIASSISTANT-DEBUG] AIAssistantWidget 初始化完成")
    
    # ---------- API ----------
    def set_text(self, text: str):
        self.view.set_text(text)
    
    def get_text(self) -> str:
        return self.view.get_text()
    
    def send(self):
        self.controller._on_send_clicked()
    
    def set_file_option(self, option: int):
        self.view.set_file_option(option)
    
    def get_file_option(self) -> int:
        return self.view.get_file_option()
    
    def clear(self):
        self.controller._on_clear_clicked()
    
    def refresh_connection_status(self):
        """手动刷新连接状态"""
        self.controller._check_bridge_connection()