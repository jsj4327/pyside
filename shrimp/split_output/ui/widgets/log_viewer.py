# -*- coding: utf-8 -*-
from datetime import datetime
from PySide2.QtWidgets import QTextEdit


class LogViewer(QTextEdit):
    """结构化日志显示组件"""

    COLOR_MAP = {
        "INFO": "#2196F3",
        "SUCCESS": "#4CAF50",
        "WARN": "#FF9800",
        "ERROR": "#F44336",
        "CONFIG": "#9C27B0",
        "SEND": "#00BCD4",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            "font-family: 'Courier New', Courier, monospace; font-size: 11px; background-color: #fdfdfd;"
        )

    def append_log(self, category, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.COLOR_MAP.get(level, "#333")
        html = (
            f'<div style="border-bottom: 1px dashed #eee; padding-bottom: 4px; margin-bottom: 4px;">'
            f'<span style="color: #888; font-size: 10px;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: bold;">[{category}]</span> '
            f'<span style="color: #333;">{message}</span></div>'
        )
        self.append(html)
