# -*- coding: utf-8 -*-

import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QTabWidget, QMenuBar, QAction, QStatusBar
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QIcon

# 导入各个局部视图组件
from view.project_tree_view import ProjectTreeView
from view.runner_view import RunnerView
from view.console_view import ConsoleView
from view.source_editor_view import SourceEditorView

class MainWindow(QMainWindow):
    """全局主窗口视图：组装所有局部视图，构建多标签页的 IDE 界面"""

    open_dir_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyLauncher (企业级 MVC 架构)")
        self.resize(1200, 800)

        # 【新增】设置窗口图标 Logo
        self._set_window_icon()

        self._init_ui()
        self._init_menu()

    def _set_window_icon(self):
        """解析并设置应用图标 Logo"""
        # 获取项目根目录 (当前文件位于 view/ 下，往上一级即为根目录)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "resources", "icons", "pylancher.png")
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _init_menu(self):
        """构建顶部菜单栏"""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件(F)")
        
        open_action = QAction("打开项目目录...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_dir_requested.emit)
        file_menu.addAction(open_action)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 请打开一个 Python 项目。")

    def _init_ui(self):
        """构建核心界面布局（左右分割 + 右侧标签页）"""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter(Qt.Horizontal, self)
        main_layout.addWidget(self.main_splitter)

        # ==================== 左侧：项目文件树 ====================
        self.project_tree = ProjectTreeView(self)
        self.main_splitter.addWidget(self.project_tree)

        # ==================== 右侧：多标签页工作区 ====================
        self.right_tabs = QTabWidget(self)
        
        # 开启文档模式，去除系统主题多余渲染
        self.right_tabs.setDocumentMode(True) 
        
        # 浅色主题标签页样式
        self.right_tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #cccccc; 
                background: #ffffff; 
            }
            QTabBar::tab {
                background: #f0f0f0;
                color: #555555;
                padding: 8px 15px;
                border: none;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #000000;
                border-top: 2px solid #007acc;
            }
            QTabBar::tab:hover:!selected {
                background: #e8e8e8;
            }
        """)
        
        self.main_splitter.addWidget(self.right_tabs)

        # --- 标签页 1：运行与控制台 ---
        tab_run = QWidget()
        tab_run_layout = QVBoxLayout(tab_run)
        tab_run_layout.setContentsMargins(5, 5, 5, 5)

        self.runner_view = RunnerView(self)
        tab_run_layout.addWidget(self.runner_view)
        
        self.console_view = ConsoleView(self)
        tab_run_layout.addWidget(self.console_view)

        self.right_tabs.addTab(tab_run, "运行与控制台")

        # --- 标签页 2：源码浏览与编辑 ---
        self.editor_view = SourceEditorView(self)
        self.right_tabs.addTab(self.editor_view, "源码编辑器")

        # 设置左右初始比例
        self.main_splitter.setSizes([240, 960])