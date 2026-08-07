# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .model.model import BridgeModel
from .view.main_view import BridgeView
from .controller.controller import BridgeController
from .bridge_server import BridgeServer


class BridgeWidget(QWidget):
    """Bridge 聚合入口 - 完全独立，无需外部传入"""
    
    status_changed = Signal(bool)
    client_connected = Signal(dict)
    client_disconnected = Signal(int)
    message_received = Signal(dict)
    
    def __init__(self, bridge_server_class=None, parent=None):
        super().__init__(parent)
        
        print("[WIDGET-DEBUG] BridgeWidget 初始化开始")
        
        # 如果没有传入 bridge_server_class，使用内部的 BridgeServer
        if bridge_server_class is None:
            bridge_server_class = BridgeServer
            print("[WIDGET-DEBUG] 使用内部 BridgeServer")
        else:
            print(f"[WIDGET-DEBUG] 使用外部 bridge_server_class: {bridge_server_class}")
        
        self.model = BridgeModel(self)
        self.view = BridgeView(self)
        self.controller = BridgeController(
            self.model, 
            self.view, 
            bridge_server_class,
            self
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.model.sig_status_changed.connect(
            lambda s: self.status_changed.emit(s == 'running')
        )
        
        print("[WIDGET-DEBUG] BridgeWidget 初始化完成")
    
    # ---------- API ----------
    def start(self):
        print("[WIDGET-DEBUG] BridgeWidget.start() 被调用")
        self.controller._on_start()
    
    def stop(self):
        print("[WIDGET-DEBUG] BridgeWidget.stop() 被调用")
        self.controller._on_stop()
    
    def set_port(self, port: int):
        print(f"[WIDGET-DEBUG] BridgeWidget.set_port({port})")
        self.view.set_port(port)
        self.model.set_port(port)
    
    def get_port(self) -> int:
        return self.view.get_port()
    
    def set_ip(self, ip: str):
        print(f"[WIDGET-DEBUG] BridgeWidget.set_ip({ip})")
        self.view.set_ip(ip)
        self.model.set_ip(ip)
    
    def get_ip(self) -> str:
        return self.view.get_ip()
    
    def is_running(self) -> bool:
        return self.model.is_running
    
    def get_clients(self) -> list:
        return self.model.get_clients_summary()
    
    def append_log(self, message: str):
        self.view.append_log(message)
    
    def clear_log(self):
        self.view.clear_log()