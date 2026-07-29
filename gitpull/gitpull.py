import sys
import os
import re
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeView, QFileSystemModel, QPushButton, QTextEdit,
    QLineEdit, QLabel, QGroupBox, QFileDialog, QMessageBox, QPlainTextEdit,
    QTabWidget, QTabBar
)
from PySide2.QtCore import Qt, QProcess, QSettings, QDir, QThread, Signal
from PySide2.QtGui import QTextCursor, QColor, QTextCharFormat


# ================= 异步文件读取线程 =================
class FileReaderThread(QThread):
    text_ready = Signal(str)
    finished_loading = Signal()
    error_occurred = Signal(str)
    warning_occurred = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.max_preview_size = 2 * 1024 * 1024  # 限制最大预览大小为 2MB

    def run(self):
        try:
            file_size = os.path.getsize(self.file_path)
            read_size = -1

            if file_size > self.max_preview_size:
                read_size = self.max_preview_size
                self.warning_occurred.emit(f"⚠️ 文件过大 ({file_size / 1024 / 1024:.2f} MB)，为防止卡顿，仅截取前 2MB 进行预览。")

            with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read() if read_size == -1 else f.read(read_size)
                self.text_ready.emit(content)

        except Exception as e:
            self.error_occurred.emit(f"无法读取文件内容: {str(e)}")
        finally:
            self.finished_loading.emit()


# ================= 主窗口程序 =================
class SimpleGitClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("轻量级 Git 图形客户端 (支持多标签与大文件预览)")
        
        self.settings = QSettings("MyDevTools", "SimpleGitClient")
        self.current_repo_path = ""
        
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_process_finished)

        self.reader_thread = None

        self.setup_ui()
        self.center_and_resize()
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

        # ================= 左侧：文件浏览器 =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        workspace_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 打开文件夹")
        self.btn_open_folder.clicked.connect(self.open_folder_dialog)
        
        self.btn_check_ignore = QPushButton("🔍 检测 .gitignore")
        self.btn_check_ignore.clicked.connect(self.check_gitignore)

        self.btn_generate_ignore = QPushButton("📄 生成 .gitignore")
        self.btn_generate_ignore.setStyleSheet("background-color: #607D8B; color: white;")
        self.btn_generate_ignore.clicked.connect(self.generate_gitignore)
        
        workspace_layout.addWidget(self.btn_open_folder)
        workspace_layout.addWidget(self.btn_check_ignore)
        workspace_layout.addWidget(self.btn_generate_ignore)
        left_layout.addLayout(workspace_layout)

        self.lbl_current_path = QLabel("当前未选择文件夹")
        self.lbl_current_path.setStyleSheet("color: gray;")
        self.lbl_current_path.setWordWrap(True)
        left_layout.addWidget(self.lbl_current_path)

        self.file_model = QFileSystemModel()
        self.file_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.file_model.setRootPath("")
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)
            
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        left_layout.addWidget(self.tree_view)

        # ================= 右侧：多标签页设计 =================
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabsClosable(True) # 开启 Tab 原生关闭按钮
        self.right_tabs.tabCloseRequested.connect(self.on_tab_close_requested)

        # ---------- Tab 1: Git 操作台 ----------
        self.tab_git = QWidget()
        git_layout = QVBoxLayout(self.tab_git)
        git_layout.setContentsMargins(0, 5, 0, 0)

        commit_group = QGroupBox("📝 暂存与提交 (Commit)")
        commit_layout = QVBoxLayout()
        btn_layout_1 = QHBoxLayout()
        self.btn_status = QPushButton("查看状态 (git status)")
        self.btn_add_all = QPushButton("暂存所有 (git add .)")
        btn_layout_1.addWidget(self.btn_status)
        btn_layout_1.addWidget(self.btn_add_all)
        self.txt_commit_msg = QTextEdit()
        self.txt_commit_msg.setPlaceholderText("在此输入提交信息 (Commit message)...")
        self.txt_commit_msg.setMaximumHeight(80)
        self.btn_commit = QPushButton("✅ 提交 (git commit)")
        self.btn_commit.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        commit_layout.addLayout(btn_layout_1)
        commit_layout.addWidget(self.txt_commit_msg)
        commit_layout.addWidget(self.btn_commit)
        commit_group.setLayout(commit_layout)

        remote_group = QGroupBox("☁️ 远程同步 (Remote & Sync)")
        remote_layout = QVBoxLayout()
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("远程地址 (URL):"))
        self.input_remote_url = QLineEdit()
        self.input_remote_url.setPlaceholderText("例如: https://github.com/user/repo.git")
        url_layout.addWidget(self.input_remote_url)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("访问令牌 (Token/Key):"))
        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.Password)
        self.input_token.setPlaceholderText("输入 Personal Access Token (仅用于HTTPS)")
        key_layout.addWidget(self.input_token)
        sync_btn_layout = QHBoxLayout()
        self.btn_pull = QPushButton("⬇️ 拉取 (git pull)")
        self.btn_push = QPushButton("⬆️ 推送 (git push)")
        self.btn_push.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        sync_btn_layout.addWidget(self.btn_pull)
        sync_btn_layout.addWidget(self.btn_push)
        remote_layout.addLayout(url_layout)
        remote_layout.addLayout(key_layout)
        remote_layout.addLayout(sync_btn_layout)
        remote_group.setLayout(remote_layout)

        console_group = QGroupBox("💻 命令行执行结果 (Console)")
        console_layout = QVBoxLayout()
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        console_layout.addWidget(self.console)
        console_group.setLayout(console_layout)

        git_layout.addWidget(commit_group)
        git_layout.addWidget(remote_group)
        git_layout.addWidget(console_group, stretch=1)

        # ---------- Tab 2: 文件预览 (动态添加，默认不在 tabs 中) ----------
        self.tab_preview = QWidget()
        preview_layout = QVBoxLayout(self.tab_preview)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        preview_top_layout = QHBoxLayout()
        self.lbl_preview_info = QLabel("准备加载...")
        self.lbl_preview_info.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # 内部显式关闭按钮
        self.btn_close_preview = QPushButton("✖ 关闭预览")
        self.btn_close_preview.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        self.btn_close_preview.setFixedWidth(100)
        self.btn_close_preview.clicked.connect(self.close_preview_tab)
        
        preview_top_layout.addWidget(self.lbl_preview_info)
        preview_top_layout.addStretch()
        preview_top_layout.addWidget(self.btn_close_preview)
        
        self.preview_editor = QPlainTextEdit()
        self.preview_editor.setReadOnly(True)
        self.preview_editor.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;")
        
        preview_layout.addLayout(preview_top_layout)
        preview_layout.addWidget(self.preview_editor)

        # 初始化时只添加 Git 操作台
        self.right_tabs.addTab(self.tab_git, "🔧 Git 操作台")
        
        # 隐藏 Git 操作台的关闭按钮 (防止误关核心界面)
        self.right_tabs.tabBar().setTabButton(0, QTabBar.RightSide, None)
        self.right_tabs.tabBar().setTabButton(0, QTabBar.LeftSide, None)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.right_tabs)
        splitter.setSizes([int(self.width() * 0.25), int(self.width() * 0.75)])

        self.btn_status.clicked.connect(lambda: self.run_git_command(["status"]))
        self.btn_add_all.clicked.connect(lambda: self.run_git_command(["add", "."]))
        self.btn_commit.clicked.connect(self.git_commit)
        self.btn_pull.clicked.connect(self.git_pull)
        self.btn_push.clicked.connect(self.git_push)

    # ================= 动态 Tab 与预览逻辑 =================
    def on_file_double_clicked(self, index):
        if self.file_model.isDir(index):
            return
            
        file_path = self.file_model.filePath(index)
        file_name = self.file_model.fileName(index)
        
        # 如果预览 Tab 当前不在 TabWidget 中，则动态添加
        if self.right_tabs.indexOf(self.tab_preview) == -1:
            self.right_tabs.addTab(self.tab_preview, "👁️ 文件预览")
            
        self.right_tabs.setCurrentWidget(self.tab_preview)
        self.lbl_preview_info.setText(f"正在加载: {file_name} ...")
        self.lbl_preview_info.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.preview_editor.clear()

        self.reader_thread = FileReaderThread(file_path)
        self.reader_thread.text_ready.connect(self.preview_editor.setPlainText)
        self.reader_thread.warning_occurred.connect(self.show_preview_warning)
        self.reader_thread.error_occurred.connect(self.show_preview_error)
        self.reader_thread.finished_loading.connect(lambda: self.finish_preview_loading(file_name))
        self.reader_thread.start()

    def on_tab_close_requested(self, index):
        """处理点击 Tab 栏上的 'X' 按钮事件"""
        if self.right_tabs.widget(index) == self.tab_preview:
            self.close_preview_tab()

    def close_preview_tab(self):
        """统一的关闭预览 Tab 逻辑"""
        idx = self.right_tabs.indexOf(self.tab_preview)
        if idx != -1:
            self.right_tabs.removeTab(idx)
            
        self.preview_editor.clear() # 释放文本内存
        self.right_tabs.setCurrentWidget(self.tab_git) # 自动切回 Git 操作台

    def show_preview_warning(self, msg):
        self.lbl_preview_info.setText(msg)
        self.lbl_preview_info.setStyleSheet("color: #FF5722; font-weight: bold;")

    def show_preview_error(self, msg):
        self.lbl_preview_info.setText(msg)
        self.lbl_preview_info.setStyleSheet("color: #F44336; font-weight: bold;")

    def finish_preview_loading(self, file_name):
        if "正在加载" in self.lbl_preview_info.text():
            self.lbl_preview_info.setText(f"预览: {file_name}")
            self.lbl_preview_info.setStyleSheet("color: #4CAF50; font-weight: bold;")

    # ================= 持久化与 Git 逻辑保持不变 =================
    def load_settings(self):
        last_repo = self.settings.value("last_repo_path", "")
        remote_url = self.settings.value("remote_url", "")
        token = self.settings.value("token", "")

        if remote_url:
            self.input_remote_url.setText(remote_url)
        if token:
            self.input_token.setText(token)

        if last_repo and os.path.isdir(last_repo):
            self.set_repo_path(last_repo)
            self.log_to_console(f"已自动恢复上次的工作区: {last_repo}", "#4CAF50")

    def closeEvent(self, event):
        self.settings.setValue("last_repo_path", self.current_repo_path)
        self.settings.setValue("remote_url", self.input_remote_url.text().strip())
        self.settings.setValue("token", self.input_token.text().strip())
        super().closeEvent(event)

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择 Git 仓库文件夹", self.current_repo_path)
        if folder_path:
            self.set_repo_path(folder_path)
            self.run_git_command(["status"])

    def set_repo_path(self, path):
        self.current_repo_path = path
        self.lbl_current_path.setText(f"当前目录: {path}")
        self.tree_view.setRootIndex(self.file_model.setRootPath(path))
        self.process.setWorkingDirectory(path)

    def check_gitignore(self):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        gitignore_path = os.path.join(self.current_repo_path, ".gitignore")
        if os.path.exists(gitignore_path):
            self.log_to_console("[检测] 当前目录下已存在 .gitignore 文件。", "#00BCD4")
            QMessageBox.information(self, "检测结果", f"✅ 发现 .gitignore 文件。\n路径: {gitignore_path}")
        else:
            self.log_to_console("[检测] 当前目录下未找到 .gitignore 文件。", "#FF9800")
            QMessageBox.warning(self, "检测结果", "❌ 当前目录下不存在 .gitignore 文件！\n建议点击右侧按钮生成。")

    def generate_gitignore(self):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        gitignore_path = os.path.join(self.current_repo_path, ".gitignore")
        if os.path.exists(gitignore_path):
            reply = QMessageBox.question(self, "文件已存在", 
                                         "当前目录下已存在 .gitignore 文件。是否要覆盖重写它？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        default_ignore_content = """# Python\n__pycache__/\n*.py[cod]\n*$py.class\n\n# 虚拟环境\n.venv/\nvenv/\nenv/\nENV/\n\n# 环境变量\n.env\n\n# 操作系统\n.DS_Store\nThumbs.db\n\n# IDE / 编辑器\n.vscode/\n.idea/\n*.swp\n*.swo\n\n# Qt / PySide / PyQt 构建文件\nui_*.py\n*_rc.py\n*.qmlc\n*.jsc\n"""
        try:
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(default_ignore_content)
            self.log_to_console(f"[成功] 已在根目录生成 .gitignore 文件", "#4CAF50")
            QMessageBox.information(self, "成功", "已成功生成适用于 Python/Qt 的 .gitignore 文件！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成 .gitignore 文件失败：\n{str(e)}")

    def run_git_command(self, args):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        if self.process.state() == QProcess.Running:
            QMessageBox.warning(self, "警告", "当前有 Git 命令正在执行，请稍后再试。")
            return
            
        self.right_tabs.setCurrentWidget(self.tab_git) # 执行命令自动切回 Git 操作台
        
        cmd = "git"
        self.log_to_console(f"\n> {cmd} {' '.join(args)}", "#FFEB3B")
        self.process.start(cmd, args)

    def git_commit(self):
        msg = self.txt_commit_msg.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "提示", "请输入 Commit 提交信息！")
            return
        self.run_git_command(["commit", "-m", msg])
        self.txt_commit_msg.clear()

    def git_pull(self):
        self.run_git_command(["pull"])

    def git_push(self):
        url = self.input_remote_url.text().strip()
        token = self.input_token.text().strip()
        if not url:
            self.run_git_command(["push"])
            return
        push_url = url
        if token and url.startswith("https://"):
            push_url = re.sub(r"https://", f"https://oauth2:{token}@", url)
        self.run_git_command(["push", push_url])

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.log_to_console(data.strip(), "#d4d4d4")

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.log_to_console(data.strip(), "#FF9800")

    def handle_process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.log_to_console(f"[执行完成]", "#4CAF50")
        else:
            self.log_to_console(f"[执行失败，退出代码: {exit_code}]", "#F44336")

    def log_to_console(self, text, hex_color):
        if not text:
            return
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)
        format = QTextCharFormat()
        format.setForeground(QColor(hex_color))
        cursor.setCharFormat(format)
        cursor.insertText(text + "\n")
        self.console.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = SimpleGitClient()
    window.show()
    sys.exit(app.exec_())
