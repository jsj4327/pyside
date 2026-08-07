# -*- coding:utf-8 -*-
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide2.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter
from PySide2.QtGui import QFont
from PySide2.QtCore import Qt

from file_browser import FileBrowserWidget
from file_bridge import BridgeWidget
from ai_assistant import AIAssistantWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("组件测试 - 文件浏览器 + Bridge + AI助手")
        self.resize(1400, 800)

        central = QWidget()
        self.setCentralWidget(central)
        
        # 主水平分割：左(浏览器+Bridge) | 右(AI助手)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # ---- 左侧：垂直排列 ----
        left_splitter = QSplitter(Qt.Vertical)
        
        self.browser = FileBrowserWidget()
        left_splitter.addWidget(self.browser)
        
        self.bridge = BridgeWidget()
        left_splitter.addWidget(self.bridge)
        
        left_splitter.setSizes([480, 220])
        main_splitter.addWidget(left_splitter)
        
        # ---- 右侧：AI助手 ----
        self.ai_assistant = AIAssistantWidget()
        main_splitter.addWidget(self.ai_assistant)
        
        main_splitter.setSizes([500, 600])
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_splitter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont()
    for name in ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei"]:
        if QFont(name).exactMatch():
            font = QFont(name, 9)
            break
    app.setFont(font)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())