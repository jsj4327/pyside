from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLineEdit, QLabel, QGroupBox, QMessageBox
)

from ui.widgets.console_widget import ConsoleWidget


class GitConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)

        # Commit group
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
        self.btn_commit.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        commit_layout.addLayout(btn_layout_1)
        commit_layout.addWidget(self.txt_commit_msg)
        commit_layout.addWidget(self.btn_commit)
        commit_group.setLayout(commit_layout)

        # Remote group
        remote_group = QGroupBox("☁️ 远程同步 (Remote & Sync)")
        remote_layout = QVBoxLayout()
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("远程地址 (URL):"))
        self.input_remote_url = QLineEdit()
        self.input_remote_url.setPlaceholderText(
            "例如: https://github.com/user/repo.git"
        )
        url_layout.addWidget(self.input_remote_url)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("访问令牌 (Token/Key):"))
        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.Password)
        self.input_token.setPlaceholderText(
            "输入 Personal Access Token (仅用于HTTPS)"
        )
        key_layout.addWidget(self.input_token)
        sync_btn_layout = QHBoxLayout()
        self.btn_pull = QPushButton("⬇️ 拉取 (git pull)")
        self.btn_push = QPushButton("⬆️ 推送 (git push)")
        self.btn_push.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold;"
        )
        sync_btn_layout.addWidget(self.btn_pull)
        sync_btn_layout.addWidget(self.btn_push)
        remote_layout.addLayout(url_layout)
        remote_layout.addLayout(key_layout)
        remote_layout.addLayout(sync_btn_layout)
        remote_group.setLayout(remote_layout)

        # Console group
        console_group = QGroupBox("💻 命令行执行结果 (Console)")
        console_layout = QVBoxLayout()
        self.console = ConsoleWidget()
        console_layout.addWidget(self.console)
        console_group.setLayout(console_layout)

        layout.addWidget(commit_group)
        layout.addWidget(remote_group)
        layout.addWidget(console_group, stretch=1)

    def get_commit_message(self) -> str:
        return self.txt_commit_msg.toPlainText().strip()

    def clear_commit_message(self):
        self.txt_commit_msg.clear()

    def get_remote_url(self) -> str:
        return self.input_remote_url.text().strip()

    def get_token(self) -> str:
        return self.input_token.text().strip()

    def set_remote_url(self, url: str):
        self.input_remote_url.setText(url)

    def set_token(self, token: str):
        self.input_token.setText(token)

    def log(self, text: str, hex_color: str):
        self.console.log(text, hex_color)
