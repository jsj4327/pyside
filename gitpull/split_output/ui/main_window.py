import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QTabWidget, QTabBar, QMessageBox, QApplication
)
from PySide2.QtCore import Qt

from config.settings_manager import SettingsManager
from core.git_manager import GitManager
from ui.panels.file_explorer_panel import FileExplorerPanel
from ui.panels.git_console_panel import GitConsolePanel
from ui.panels.file_preview_panel import FilePreviewPanel


class SimpleGitClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("轻量级 Git 图形客户端 (支持多标签与大文件预览)")

        self.settings_mgr = SettingsManager()
        self.git_mgr = GitManager(self)
        self.current_repo_path = ""

        self.setup_ui()
        self.center_and_resize()
        self._connect_signals()
        self.load_settings()

    def center_and_resize(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        width = int(screen_geometry.width() * 0.85)
        height = int(screen_geometry.height() * 0.85)
        x = int((screen_geometry.width() - width) / 2)
        y = int((screen_geometry.height() - height) / 2)
        self.setGeometry(x, y, width, height)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Right tabs (must be created before explorer panel to allow signal connection)
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabsClosable(True)
        self.right_tabs.tabCloseRequested.connect(self.on_tab_close_requested)

        self.git_console_panel = GitConsolePanel()
        self.file_preview_panel = FilePreviewPanel()
        self.file_preview_panel.btn_close_preview.clicked.connect(self.close_preview_tab)

        self.right_tabs.addTab(self.git_console_panel, "🔧 Git 操作台")
        self.right_tabs.tabBar().setTabButton(0, QTabBar.RightSide, None)
        self.right_tabs.tabBar().setTabButton(0, QTabBar.LeftSide, None)

        # Left panel (created after git_console_panel so attribute exists for connect)
        self.explorer_panel = FileExplorerPanel()
        self.explorer_panel.file_double_clicked.connect(self.on_file_double_clicked)
        self.explorer_panel.console_log_requested.connect(self.git_console_panel.log)

        splitter.addWidget(self.explorer_panel)
        splitter.addWidget(self.right_tabs)
        splitter.setSizes([int(self.width() * 0.25), int(self.width() * 0.75)])

    def _connect_signals(self):
        # Explorer
        self.explorer_panel.btn_open_folder.clicked.disconnect()
        self.explorer_panel.btn_open_folder.clicked.connect(self._open_folder_and_status)

        # Git console buttons
        self.git_console_panel.btn_status.clicked.connect(
            lambda: self.run_git_command(["status"])
        )
        self.git_console_panel.btn_add_all.clicked.connect(
            lambda: self.run_git_command(["add", "."])
        )
        self.git_console_panel.btn_commit.clicked.connect(self.git_commit)
        self.git_console_panel.btn_pull.clicked.connect(
            lambda: self.run_git_command(["pull"])
        )
        self.git_console_panel.btn_push.clicked.connect(self.git_push)

        # Git manager
        self.git_mgr.stdout_received.connect(
            lambda data: self.git_console_panel.log(data, "#d4d4d4")
        )
        self.git_mgr.stderr_received.connect(
            lambda data: self.git_console_panel.log(data, "#FF9800")
        )
        self.git_mgr.process_finished.connect(self.handle_process_finished)

    def _open_folder_and_status(self):
        self.explorer_panel.open_folder_dialog()
        if self.explorer_panel.current_repo_path:
            self.set_repo_path(self.explorer_panel.current_repo_path)
            self.run_git_command(["status"])

    def set_repo_path(self, path: str):
        self.current_repo_path = path
        self.explorer_panel.set_repo_path(path)
        self.git_mgr.set_working_directory(path)

    def on_file_double_clicked(self, index):
        if self.explorer_panel.file_model.isDir(index):
            return

        file_path = self.explorer_panel.file_model.filePath(index)
        file_name = self.explorer_panel.file_model.fileName(index)

        if self.right_tabs.indexOf(self.file_preview_panel) == -1:
            self.right_tabs.addTab(self.file_preview_panel, "👁️ 文件预览")

        self.right_tabs.setCurrentWidget(self.file_preview_panel)
        self.file_preview_panel.load_file(file_path, file_name)

    def on_tab_close_requested(self, index):
        if self.right_tabs.widget(index) == self.file_preview_panel:
            self.close_preview_tab()

    def close_preview_tab(self):
        idx = self.right_tabs.indexOf(self.file_preview_panel)
        if idx != -1:
            self.right_tabs.removeTab(idx)
        self.file_preview_panel.clear_content()
        self.right_tabs.setCurrentWidget(self.git_console_panel)

    def run_git_command(self, args: list):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        if self.git_mgr.is_running():
            QMessageBox.warning(self, "警告", "当前有 Git 命令正在执行，请稍后再试。")
            return

        self.right_tabs.setCurrentWidget(self.git_console_panel)
        self.git_console_panel.log(f"\n> git {' '.join(args)}", "#FFEB3B")
        self.git_mgr.run_command(args)

    def git_commit(self):
        msg = self.git_console_panel.get_commit_message()
        if not msg:
            QMessageBox.warning(self, "提示", "请输入 Commit 提交信息！")
            return
        self.run_git_command(["commit", "-m", msg])
        self.git_console_panel.clear_commit_message()

    def git_push(self):
        url = self.git_console_panel.get_remote_url()
        token = self.git_console_panel.get_token()
        if not url:
            self.run_git_command(["push"])
            return
        self.git_mgr.push_with_token(url, token)

    def handle_process_finished(self, exit_code: int, exit_status: int):
        if exit_code == 0:
            self.git_console_panel.log("[执行完成]", "#4CAF50")
        else:
            self.git_console_panel.log(
                f"[执行失败，退出代码: {exit_code}]", "#F44336"
            )

    def load_settings(self):
        cfg = self.settings_mgr.load()
        remote_url = cfg.get("remote_url", "")
        token = cfg.get("token", "")
        last_repo = cfg.get("last_repo_path", "")

        if remote_url:
            self.git_console_panel.set_remote_url(remote_url)
        if token:
            self.git_console_panel.set_token(token)
        if last_repo and os.path.isdir(last_repo):
            self.set_repo_path(last_repo)
            self.git_console_panel.log(
                f"已自动恢复上次的工作区: {last_repo}", "#4CAF50"
            )

    def closeEvent(self, event):
        self.settings_mgr.save(
            self.current_repo_path,
            self.git_console_panel.get_remote_url(),
            self.git_console_panel.get_token(),
        )
        super().closeEvent(event)
