# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusView(QWidget):
    """AI 助手状态栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#666;font-size:11px;")
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color:#888;font-size:11px;")
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.info_label)
    
    def update_status(self, status: str, info: str = ""):
        if status == "sending":
            self.status_label.setText("📤 发送中...")
            self.status_label.setStyleSheet("color:#FF9800;font-size:11px;font-weight:bold;")
        elif status == "sent":
            self.status_label.setText("✅ 已发送")
            self.status_label.setStyleSheet("color:#4CAF50;font-size:11px;font-weight:bold;")
        elif status == "error":
            self.status_label.setText("❌ 发送失败")
            self.status_label.setStyleSheet("color:#f44336;font-size:11px;font-weight:bold;")
        else:
            self.status_label.setText("就绪")
            self.status_label.setStyleSheet("color:#666;font-size:11px;")
        
        self.info_label.setText(info)