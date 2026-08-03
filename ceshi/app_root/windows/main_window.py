# -*- coding:utf-8 -*-
import os
from PySide2.QtWidgets import QMainWindow, QTabWidget, QWidget, QLabel
from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon, QFont
from PySide2.QtWidgets import QApplication
from modules import get_file_browser_module_widget
from config import ICON_FILE, WINDOW_SCALE_RATIO

class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 【修复】补充了缺失的后引号
        self.setWindowTitle("通用文本文件浏览工具")
        self._set_window_icon()
        # 【修复】修正了括号
        self._resize_center_window(WINDOW_SCALE_RATIO)
        
        self._build_tab_container()
        
        # 初始化计数器
        self.bridge_connection_count = 0
        
        # 引用 bridge 实例，供子模块调用
        self.bridge_server = None
        
        self._build_status_bar()
        self.statusBar().showMessage("就绪：等待 WebSocket 服务启动...", 5000)

    def _build_status_bar(self):
        status_bar = self.statusBar()
        self.bridge_status_label = QLabel("🔴 WebSocket: 未启动")
        self.bridge_status_label.setFont(QFont("Arial", 9))
        status_bar.addPermanentWidget(self.bridge_status_label)

    def set_bridge_status(self, is_running, port=None):
        if is_running and port:
            self.bridge_status_label.setText(f"🟢 WebSocket: 运行中 (:{port}) | 连接数: 0")
            self.bridge_status_label.setStyleSheet("color: green;")
        else:
            self.bridge_status_label.setText("🔴 WebSocket: 未启动")
            self.bridge_status_label.setStyleSheet("color: red;")

    def on_plugin_connected(self):
        """插件连接回调"""
        self.bridge_connection_count += 1
        base_text = "🟢 WebSocket: 运行中 (:9002)"
        self.bridge_status_label.setText(f"{base_text} | 连接数: {self.bridge_connection_count}")
        self.statusBar().showMessage("插件已连接", 2000)

    def on_browser_message(self, data):
        """
        收到插件发回的消息（如 AI 分析结果）
        这里我们将消息转发给当前的文件浏览组件显示
        """
        if data.get('type') == 'AI_RESULT':
            result_text = data.get('text', '')
            # 获取当前 Tab 的 widget
            current_widget = self.centralWidget().currentWidget()
            # 如果是文件浏览组件，调用其显示方法
            if hasattr(current_widget, 'append_ai_result'):
                current_widget.append_ai_result(result_text)

    def _set_window_icon(self):
        if os.path.exists(ICON_FILE): self.setWindowIcon(QIcon(ICON_FILE))

    def _resize_center_window(self, scale: float):
        from PySide2.QtWidgets import QDesktopWidget
        try:
            screen = QApplication.primaryScreen()
            avail_rect = screen.availableGeometry()
        except AttributeError:
            desktop = QDesktopWidget()
            avail_rect = desktop.availableGeometry()
            
        win_w = int(avail_rect.width() * scale)
        win_h = int(avail_rect.height() * scale)
        x = avail_rect.x() + (avail_rect.width() - win_w) // 2
        y = avail_rect.y() + (avail_rect.height() - win_h) // 2
        self.setGeometry(x, y, win_w, win_h)

    def _build_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setMovable(True)
        tab_widget.setTabsClosable(False)
        
        browser_widget = get_file_browser_module_widget()
        tab_widget.addTab(browser_widget, "📂 文本浏览器")
        # 【修复】将 addWidget 改为 addTab
        tab_widget.addTab(QWidget(), "扩展面板")
        
        self.setCentralWidget(tab_widget)
