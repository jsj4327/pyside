# -*- coding: utf-8 -*-
import sys
import os
import ctypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSplitter, QFileSystemModel, QTreeView,
                             QPushButton, QFileDialog, QLabel, QSizePolicy)
from PyQt5.QtCore import Qt, QProcess, QDir, QSettings, QProcessEnvironment

# 加载 X11 动态库，用于在 PyQt 调整大小时实时同步 xterm 子窗口大小
try:
    x11 = ctypes.CDLL("libX11.so.6")
    display = x11.XOpenDisplay(None)
except Exception:
    x11 = None
    display = None


class NativeTerminalWidget(QWidget):
    """
    使用系统等宽字体与 X11 实时尺寸同步的 xterm 内嵌终端控件
    使用双缓冲透明遮罩彻底消除重建 xterm 时的闪烁
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #1e1e1e;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 核心防闪烁遮罩层：在 xterm 销毁和重建的间隙，用纯黑（#1e1e1e）遮挡底层 X11 窗口的白屏/闪烁
        self.cover_widget = QWidget(self)
        self.cover_widget.setStyleSheet("background-color: #1e1e1e;")
        self.cover_widget.setGeometry(self.rect())
        self.cover_widget.hide()

        self.terminal_process = QProcess(self)
        
        env = QProcessEnvironment.systemEnvironment()
        env.insert("LANG", "zh_CN.UTF-8")
        env.insert("LC_ALL", "zh_CN.UTF-8")
        env.insert("LC_CTYPE", "zh_CN.UTF-8")
        self.terminal_process.setProcessEnvironment(env)
        
        self.setMinimumSize(400, 300)
        self.window_id = 0
        self.current_working_path = os.getcwd()

    def showEvent(self, event):
        super().showEvent(event)
        if self.terminal_process.state() == QProcess.NotRunning:
            self.spawn_terminal(self.current_working_path)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.cover_widget.setGeometry(self.rect())
        if x11 and display and self.window_id:
            try:
                width = self.width()
                height = self.height()
                if width > 10 and height > 10:
                    x11.XResizeWindow(display, self.window_id, width, height)
                    x11.XFlush(display)
            except Exception:
                pass

    def change_directory(self, path):
        """完美无闪烁重启终端"""
        if not os.path.exists(path):
            return
        self.current_working_path = path

        # 1. 立即显示同色遮罩，盖住旧窗口销毁到新窗口渲染之间的空白空隙
        self.cover_widget.setGeometry(self.rect())
        self.cover_widget.raise_()
        self.cover_widget.show()
        QApplication.processEvents()

        # 2. 终止旧进程
        if self.terminal_process.state() == QProcess.Running:
            self.terminal_process.kill()
            self.terminal_process.waitForFinished(30)

        # 3. 启动新进程
        self.spawn_terminal(path)

        # 4. 安全隐藏遮罩
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.cover_widget.hide)

    def spawn_terminal(self, path):
        self.window_id = int(self.winId())
        self.terminal_process.start("xterm", [
            "-into", str(self.window_id),
            "-bg", "#1e1e1e",
            "-fg", "#dcdcdc",
            "-fa", "Noto Sans Mono CJK SC:style=Regular",
            "-fs", "10",
            "-u8",
            "-sb",
            "-b", "0",
            "-e", "bash", "-c", f"cd '{path}' && exec bash"
        ])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt 文件浏览器 + 原生 xterm 终端工具")
        self.resize(1200, 750)

        self.settings = QSettings("KylinPythonTools", "ViewNTerXtermFixed")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # --- 顶部导航栏 ---
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)
        
        self.btn_open = QPushButton("📁 打开文件夹...")
        self.btn_open.setStyleSheet("padding: 5px 12px;")
        self.btn_open.clicked.connect(self.select_folder_dialog)
        nav_layout.addWidget(self.btn_open)

        self.btn_home = QPushButton("🏠 回到主目录")
        self.btn_home.setStyleSheet("padding: 5px 12px;")
        self.btn_home.clicked.connect(self.go_home_dir)
        nav_layout.addWidget(self.btn_home)

        self.btn_parent = QPushButton("⬆ 上一级目录")
        self.btn_parent.setStyleSheet("padding: 5px 12px;")
        self.btn_parent.clicked.connect(self.go_parent_dir)
        nav_layout.addWidget(self.btn_parent)

        tip_label = QLabel(" (提示: Ctrl+双击重启xterm，Alt+双击打开MATE终端)")
        tip_label.setStyleSheet("color: #888888; font-size: 11px;")
        nav_layout.addWidget(tip_label)

        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)

        # --- 左右分割布局 ---
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, stretch=1)

        # --- 左侧：文件树模型 ---
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())

        # 使用标准的 QTreeView
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setColumnWidth(0, 280)
        self.tree_view.setAlternatingRowColors(True)

        # --- 右侧：原生 xterm 终端内嵌 ---
        self.terminal = NativeTerminalWidget()

        default_path = os.getcwd()
        self.current_path = self.settings.value("last_path", default_path)
        if not os.path.exists(self.current_path):
            self.current_path = default_path

        self.apply_tree_path(self.current_path)

        self.splitter.addWidget(self.tree_view)
        self.splitter.addWidget(self.terminal)
        self.splitter.setSizes([320, 880])
        self.splitter.setHandleWidth(4)

        self.tree_view.doubleClicked.connect(self.on_tree_double_clicked)

    def apply_tree_path(self, path):
        self.current_path = path
        index = self.file_system_model.index(path)
        self.tree_view.setRootIndex(index)
        self.settings.setValue("last_path", path)

    def select_folder_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要浏览的文件夹", self.current_path)
        if dir_path:
            self.apply_tree_path(dir_path)

    def go_home_dir(self):
        home_path = QDir.homePath()
        self.apply_tree_path(home_path)

    def go_parent_dir(self):
        parent_path = os.path.dirname(self.current_path)
        if os.path.exists(parent_path):
            self.apply_tree_path(parent_path)

    def on_tree_double_clicked(self, index):
        path = self.file_system_model.filePath(index)
        if os.path.isdir(path):
            modifiers = QApplication.keyboardModifiers()
            is_ctrl = bool(modifiers & Qt.ControlModifier)
            is_alt = bool(modifiers & Qt.AltModifier)

            if is_ctrl:
                # 抵消标准双击可能造成的树状态改变，保证树不展开也不收缩
                if self.tree_view.isExpanded(index):
                    self.tree_view.collapse(index)
                else:
                    self.tree_view.setExpanded(index, False)
                # 按住 Ctrl 双击：重启右侧内嵌 xterm 并进入双击的文件夹
                self.terminal.change_directory(path)
            elif is_alt:
                # 抵消标准双击可能造成的树状态改变，保证树不展开也不收缩
                if self.tree_view.isExpanded(index):
                    self.tree_view.collapse(index)
                else:
                    self.tree_view.setExpanded(index, False)
                # 按住 Alt 双击：在双击的文件夹目录下启动 mate-terminal
                QProcess.startDetached("mate-terminal", ["--working-directory", path])
            else:
                # 普通双击：左侧控件正常进入这个文件夹
                self.apply_tree_path(path)
        elif os.path.isfile(path):
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
