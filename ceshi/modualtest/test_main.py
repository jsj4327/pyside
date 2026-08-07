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
from debug import DebugWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("组件测试 - 文件浏览器 + Bridge + AI助手 + Debug")
        self.resize(1400, 800)

        central = QWidget()
        self.setCentralWidget(central)
        
        # 主水平分割：左(浏览器+Bridge) | 右(AI助手+Debug)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # ---- 左侧：垂直排列 ----
        left_splitter = QSplitter(Qt.Vertical)
        
        self.browser = FileBrowserWidget()
        left_splitter.addWidget(self.browser)
        
        self.bridge = BridgeWidget()
        left_splitter.addWidget(self.bridge)
        
        left_splitter.setSizes([480, 220])
        main_splitter.addWidget(left_splitter)
        
        # ---- 右侧：AI助手 + Debug 垂直排列 ----
        right_splitter = QSplitter(Qt.Vertical)
        
        self.ai_assistant = AIAssistantWidget()
        right_splitter.addWidget(self.ai_assistant)
        
        self.debug_widget = DebugWidget()
        right_splitter.addWidget(self.debug_widget)
        
        # 设置右侧分割比例：AI助手占 60%，Debug 占 40%
        right_splitter.setSizes([480, 320])
        main_splitter.addWidget(right_splitter)
        
        # 设置主分割比例
        main_splitter.setSizes([500, 700])
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_splitter)
        
        # ---- 连接信号 ----
        # 文件浏览器选中文件 -> Debug 模块
        if hasattr(self.browser, 'file_selected'):
            self.browser.file_selected.connect(self.debug_widget.set_file_path)
        
        # Debug 反馈 -> AI 助手
        self.debug_widget.sig_feedback_sent.connect(self._on_debug_feedback)
        
        # Debug 执行完成 -> 状态提示
        self.debug_widget.sig_execution_done.connect(self._on_debug_execution_done)
    
    def _on_debug_feedback(self, data: dict):
        """处理 Debug 反馈，填充到 AI 输入框"""
        print(f"[MAIN] 收到 Debug 反馈，长度: {len(data.get('content', ''))}")
        if 'content' in data:
            self.ai_assistant.set_text(data['content'])
            # 可选：自动发送
            # self.ai_assistant.send()
    
    def _on_debug_execution_done(self, file_path: str):
        """Debug 执行完成回调"""
        print(f"[MAIN] Debug 执行完成: {file_path}")


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