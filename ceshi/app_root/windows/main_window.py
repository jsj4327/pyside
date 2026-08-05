# -*- coding:utf-8 -*-
import os
import subprocess
import sys
from PySide2.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QLabel,
    QMessageBox
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon, QFont
from PySide2.QtWidgets import QApplication
from modules import get_file_browser_module_widget
from modules.token_manager import TokenManagerWidget
from modules.ai_splitter import AISplitterWidget, AIRecordWidget
from modules.source_viewer import SourceViewerWidget
from config import ICON_FILE, WINDOW_SCALE_RATIO


class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("通用文本文件浏览工具")
        self._set_window_icon()
        self._resize_center_window(WINDOW_SCALE_RATIO)

        self._build_tab_container()

        self.bridge_connection_count = 0
        self.bridge_server = None

        self._build_status_bar()
        self._update_bridge_status(False, 0)

    def _build_status_bar(self):
        status_bar = self.statusBar()
        self.bridge_status_label = QLabel("🔴 WebSocket: 未启动")
        self.bridge_status_label.setFont(QFont("Arial", 9))
        status_bar.addPermanentWidget(self.bridge_status_label)

    # ---------- 统一更新状态栏 ----------
    def _update_bridge_status(self, is_running, count):
        self.bridge_connection_count = count
        if is_running and self.bridge_server and self.bridge_server.is_listening():
            self.bridge_status_label.setText(f"🟢 WebSocket: 运行中 (:9002) | 连接数: {count}")
            self.bridge_status_label.setStyleSheet("color: green;")
        else:
            self.bridge_status_label.setText("🔴 WebSocket: 未启动")
            self.bridge_status_label.setStyleSheet("color: red;")

    # ---------- 向后兼容的 set_bridge_status ----------
    def set_bridge_status(self, is_running, port=None, count=0):
        self._update_bridge_status(is_running, count)

    # ---------- 插件连接回调 ----------
    def on_plugin_connected(self, count):
        """连接建立时更新连接数"""
        self._update_bridge_status(True, count)
        self.statusBar().showMessage(f"插件已连接，当前连接数: {count}", 2000)

    # ---------- 插件断开回调 ----------
    def on_plugin_disconnected(self, count):
        """连接断开时更新连接数"""
        self._update_bridge_status(True, count)  # 服务仍在运行
        self.statusBar().showMessage(f"插件断开，当前连接数: {count}", 2000)

    # ---------- 收到插件消息 ----------
    def on_browser_message(self, data):
        if data.get('type') != 'AI_RESULT':
            return
        result_text = data.get('text', '')
        if not result_text:
            return

        current_widget = self.centralWidget().currentWidget()
        if hasattr(current_widget, 'append_ai_result'):
            current_widget.append_ai_result(result_text)

        if hasattr(self, 'ai_record_widget'):
            self.ai_record_widget.check_and_add(result_text)

        if hasattr(self, 'source_viewer'):
            self.source_viewer.handle_ai_response(result_text)

    # ---------- 窗口设置 ----------
    def _set_window_icon(self):
        if os.path.exists(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))

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

    # ---------- Tab 构建 ----------
    def _build_tab_container(self):
        tab_widget = QTabWidget()
        tab_widget.setMovable(True)
        tab_widget.setTabsClosable(False)

        browser_widget = get_file_browser_module_widget()
        tab_widget.addTab(browser_widget, "📂 文本浏览器")

        token_widget = TokenManagerWidget()
        tab_widget.addTab(token_widget, "📊 Token管理")

        self.ai_splitter = AISplitterWidget()
        self.ai_splitter.open_current_path_signal.connect(self._on_open_current_path)
        self.ai_splitter.preview_file_signal.connect(self._on_preview_file)
        self.ai_splitter.directory_changed.connect(self._on_ai_splitter_directory_changed)
        tab_widget.addTab(self.ai_splitter, "🔀 AI拆分器")

        self.ai_record_widget = AIRecordWidget()
        tab_widget.addTab(self.ai_record_widget, "📜 响应记录")

        self.source_viewer = SourceViewerWidget()
        tab_widget.addTab(self.source_viewer, "📄 源码预览")

        self.setCentralWidget(tab_widget)

        if hasattr(self, 'ai_splitter') and hasattr(self, 'source_viewer'):
            current_path = self.ai_splitter.get_current_path()
            if current_path and os.path.isdir(current_path):
                self.source_viewer.set_root_path(current_path)

    # ---------- 槽函数 ----------
    def _on_open_current_path(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", f"路径不存在: {path}")
            return
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件管理器: {str(e)}")

    def _on_preview_file(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件不存在: {file_path}")
            return
        self.centralWidget().setCurrentIndex(4)
        self.source_viewer.load_file(file_path)

    def _on_ai_splitter_directory_changed(self, path):
        if hasattr(self, 'source_viewer'):
            self.source_viewer.set_root_path(path)