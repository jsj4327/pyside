from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeView, QFileSystemModel, QFileDialog, QMessageBox
)
from PySide2.QtCore import QDir, Signal

from core.gitignore_generator import (
    check_gitignore_exists, get_gitignore_path, generate_gitignore
)


class FileExplorerPanel(QWidget):
    file_double_clicked = Signal(object)  # QModelIndex
    console_log_requested = Signal(str, str)  # text, color

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_repo_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        workspace_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 打开文件夹")
        self.btn_open_folder.clicked.connect(self.open_folder_dialog)

        self.btn_check_ignore = QPushButton("🔍 检测 .gitignore")
        self.btn_check_ignore.clicked.connect(self.check_gitignore)

        self.btn_generate_ignore = QPushButton("📄 生成 .gitignore")
        self.btn_generate_ignore.setStyleSheet("background-color: #607D8B; color: white;")
        self.btn_generate_ignore.clicked.connect(self.generate_gitignore_action)

        workspace_layout.addWidget(self.btn_open_folder)
        workspace_layout.addWidget(self.btn_check_ignore)
        workspace_layout.addWidget(self.btn_generate_ignore)
        layout.addLayout(workspace_layout)

        # Path label
        self.lbl_current_path = QLabel("当前未选择文件夹")
        self.lbl_current_path.setStyleSheet("color: gray;")
        self.lbl_current_path.setWordWrap(True)
        layout.addWidget(self.lbl_current_path)

        # Tree view
        self.file_model = QFileSystemModel()
        self.file_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.file_model.setRootPath("")

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)
        self.tree_view.doubleClicked.connect(self.file_double_clicked.emit)
        layout.addWidget(self.tree_view)

    def set_repo_path(self, path: str):
        self.current_repo_path = path
        self.lbl_current_path.setText(f"当前目录: {path}")
        self.tree_view.setRootIndex(self.file_model.setRootPath(path))

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择 Git 仓库文件夹", self.current_repo_path
        )
        if folder_path:
            self.set_repo_path(folder_path)

    def check_gitignore(self):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        if check_gitignore_exists(self.current_repo_path):
            path = get_gitignore_path(self.current_repo_path)
            self.console_log_requested.emit(
                "[检测] 当前目录下已存在 .gitignore 文件。", "#00BCD4"
            )
            QMessageBox.information(
                self, "检测结果", f"✅ 发现 .gitignore 文件。\n路径: {path}"
            )
        else:
            self.console_log_requested.emit(
                "[检测] 当前目录下未找到 .gitignore 文件。", "#FF9800"
            )
            QMessageBox.warning(
                self, "检测结果",
                "❌ 当前目录下不存在 .gitignore 文件！\n建议点击右侧按钮生成。"
            )

    def generate_gitignore_action(self):
        if not self.current_repo_path:
            QMessageBox.warning(self, "警告", "请先打开一个 Git 仓库文件夹！")
            return
        gitignore_path = get_gitignore_path(self.current_repo_path)
        import os
        if os.path.exists(gitignore_path):
            reply = QMessageBox.question(
                self, "文件已存在",
                "当前目录下已存在 .gitignore 文件。是否要覆盖重写它？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        success, msg = generate_gitignore(self.current_repo_path)
        if success:
            self.console_log_requested.emit(
                "[成功] 已在根目录生成 .gitignore 文件", "#4CAF50"
            )
            QMessageBox.information(self, "成功", msg)
        else:
            QMessageBox.critical(self, "错误", msg)
