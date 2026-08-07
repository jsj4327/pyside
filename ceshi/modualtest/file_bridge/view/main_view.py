# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .bridge_view import BridgeCoreView
from .status_view import StatusView


class BridgeView(QWidget):
    """Bridge 主视图"""
    
    sig_start = Signal()
    sig_stop = Signal()
    sig_port_changed = Signal(int)
    sig_ip_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("[VIEW-DEBUG] BridgeView 初始化开始")
        self._init_ui()
        self._connect_signals()
        print("[VIEW-DEBUG] BridgeView 初始化完成")
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.core = BridgeCoreView()
        layout.addWidget(self.core)
        
        self.status = StatusView()
        layout.addWidget(self.status)
    
    def _connect_signals(self):
        print("[VIEW-DEBUG] 连接 BridgeView 信号...")
        self.core.sig_start.connect(self.sig_start.emit)
        self.core.sig_stop.connect(self.sig_stop.emit)
        self.core.sig_port_changed.connect(self.sig_port_changed.emit)
        self.core.sig_ip_changed.connect(self.sig_ip_changed.emit)
        print("[VIEW-DEBUG] BridgeView 信号连接完成")
    
    def update_clients(self, clients: list):
        print(f"[VIEW-DEBUG] update_clients: {len(clients)} 个")
        self.core.update_clients(clients)
    
    def append_log(self, message: str, log_type: str = "info", detail: str = ""):
        """追加日志（转发给 core）"""
        self.core.append_log(message, log_type, detail)
    
    def set_port(self, port: int):
        self.core.set_port(port)
    
    def get_port(self) -> int:
        return self.core.get_port()
    
    def set_ip(self, ip: str):
        self.core.set_ip(ip)
    
    def get_ip(self) -> str:
        return self.core.get_ip()
    
    def set_running_state(self, is_running: bool):
        self.core.set_running_state(is_running)
    
    def update_status(self, status: str, port: int, client_count: int):
        self.status.update_status(status, port, client_count)
    
    def clear_log(self):
        self.core.log_text.clear()