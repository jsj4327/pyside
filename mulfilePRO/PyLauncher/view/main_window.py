import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QTabWidget, QAction, QStatusBar, QApplication
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QIcon, QCloseEvent

from view.project_tree_view import ProjectTreeView
from view.runner_view import RunnerView
from view.console_view import ConsoleView
from view.source_editor_view import SourceEditorView

class MainWindow(QMainWindow):
    """全局主窗口视图"""

    open_dir_requested = Signal()
    window_closing = Signal()  # 窗口关闭信号，通知 Controller 持久化状态

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyLauncher (企业级 MVC 架构)")

        self._init_window_size()
        self._set_window_icon()
        self._init_ui()
        self._init_menu()

    def _init_window_size(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.85)
        height = int(screen.height() * 0.85)
        self.resize(width, height)

        x = int(screen.x() + (screen.width() - width) / 2)
        y = int(screen.y() + (screen.height() - height) / 2)
        self.move(x, y)

    def _set_window_icon(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "resources", "icons", "pylancher.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _init_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件(F)")
        
        open_action = QAction("打开项目目录...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_dir_requested.emit)
        file_menu.addAction(open_action)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 请打开一个 Python 项目。")

    def show_status_message(self, message, timeout=3000):
        self.status_bar.showMessage(message, timeout)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter(Qt.Horizontal, self)
        main_layout.addWidget(self.main_splitter)

        self.project_tree = ProjectTreeView(self)
        self.main_splitter.addWidget(self.project_tree)

        self.right_tabs = QTabWidget(self)
        self.right_tabs.setDocumentMode(True) 
        
        self.right_tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #ccc;
                background: #fff;
            }
            QTabBar::tab {
                background: #f0f0f0;
                color: #333;
                padding: 8px 15px;
                border: none;
            }
            QTabBar::tab:selected {
                background: #fff;
                color: #000;
                border-top: 2px solid #007acc;
            }
            QTabBar::tab:hover:!selected {
                background: #e5e5e5;
            }
        """)
        
        self.main_splitter.addWidget(self.right_tabs)

        tab_run = QWidget()
        tab_run_layout = QVBoxLayout(tab_run)
        tab_run_layout.setContentsMargins(5, 5, 5, 5)

        self.runner_view = RunnerView(self)
        tab_run_layout.addWidget(self.runner_view)
        
        self.console_view = ConsoleView(self)
        tab_run_layout.addWidget(self.console_view)

        self.right_tabs.addTab(tab_run, "运行与控制台")

        self.editor_view = SourceEditorView(self)
        self.right_tabs.addTab(self.editor_view, "源码编辑器")

        self.main_splitter.setSizes([280, 920])

    def closeEvent(self, event: QCloseEvent):
        """拦截窗口关闭事件，触发表单与控件持久化"""
        self.window_closing.emit()
        super().closeEvent(event)