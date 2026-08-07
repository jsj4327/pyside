# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusView(QWidget):
    """Bridge 状态栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        
        self.status_label = QLabel("🔴 未启动")
        self.status_label.setStyleSheet("color:#666;font-size:11px;font-weight:bold;")
        
        self.info_label = QLabel("端口: 9002")
        self.info_label.setStyleSheet("color:#666;font-size:11px;")
        
        self.client_label = QLabel("连接数: 0")
        self.client_label.setStyleSheet("color:#666;font-size:11px;")
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.info_label)
        layout.addWidget(self.client_label)
    
    def update_status(self, status: str, port: int, client_count: int):
        """更新状态栏"""
        if status == "running":
            self.status_label.setText("🟢 运行中")
            self.status_label.setStyleSheet("color:green;font-size:11px;font-weight:bold;")
        elif status == "stopped":
            self.status_label.setText("🔴 已停止")
            self.status_label.setStyleSheet("color:red;font-size:11px;font-weight:bold;")
        elif status == "error":
            self.status_label.setText("🔴 错误")
            self.status_label.setStyleSheet("color:red;font-size:11px;font-weight:bold;")
        else:
            self.status_label.setText("⚪ 未启动")
            self.status_label.setStyleSheet("color:#666;font-size:11px;font-weight:bold;")
        
        self.info_label.setText(f"端口: {port}")
        self.client_label.setText(f"连接数: {client_count}")