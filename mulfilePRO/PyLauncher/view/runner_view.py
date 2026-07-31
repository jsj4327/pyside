import os
import sys
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QFileDialog, QGroupBox
)
from PySide2.QtCore import Signal


class RunnerView(QWidget):
    """运行入口视图：配置 Python 解释器、脚本路径、参数并一键启动程序"""

    run_requested = Signal(dict)  # 发送运行参数字典

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        group_box = QGroupBox("程序运行配置", self)
        form_layout = QFormLayout(group_box)
        form_layout.setSpacing(10)

        # 1. Python 解释器路径
        self.txt_interpreter = QLineEdit(self)
        self.txt_interpreter.setText(sys.executable)
        btn_browse_interp = QPushButton("浏览...", self)
        btn_browse_interp.clicked.connect(self._browse_interpreter)
        
        layout_interp = QHBoxLayout()
        layout_interp.addWidget(self.txt_interpreter)
        layout_interp.addWidget(btn_browse_interp)
        form_layout.addRow("Python 解释器:", layout_interp)

        # 2. 脚本路径（支持单击文件树自动填充）
        self.txt_script_path = QLineEdit(self)
        self.txt_script_path.setPlaceholderText("点击左侧 .py 文件自动填充，或手动选择")
        btn_browse_script = QPushButton("浏览...", self)
        btn_browse_script.clicked.connect(self._browse_script)

        layout_script = QHBoxLayout()
        layout_script.addWidget(self.txt_script_path)
        layout_script.addWidget(btn_browse_script)
        form_layout.addRow("运行脚本路径:", layout_script)

        # 3. 命令行参数
        self.txt_args = QLineEdit(self)
        self.txt_args.setPlaceholderText("例如: --port 8080 --debug (选填)")
        form_layout.addRow("命令行参数:", self.txt_args)

        # 4. 工作目录
        self.txt_work_dir = QLineEdit(self)
        btn_browse_workdir = QPushButton("浏览...", self)
        btn_browse_workdir.clicked.connect(self._browse_workdir)

        layout_workdir = QHBoxLayout()
        layout_workdir.addWidget(self.txt_work_dir)
        layout_workdir.addWidget(btn_browse_workdir)
        form_layout.addRow("工作目录 (CWD):", layout_workdir)

        layout.addWidget(group_box)

        # 一键启动按钮（无终端弹窗，支持多开）
        self.btn_run = QPushButton("🚀 一键启动程序 (支持多进程多开)", self)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0062a3;
            }
            QPushButton:pressed {
                background-color: #004d80;
            }
        """)
        self.btn_run.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.btn_run)

        layout.addStretch()

    def set_script_path(self, path: str):
        """外部（文件树单击）设置脚本路径，并同步更新默认工作目录"""
        self.txt_script_path.setText(path)
        if path and os.path.exists(path):
            work_dir = os.path.dirname(os.path.abspath(path))
            self.txt_work_dir.setText(work_dir)

    def get_config(self) -> dict:
        """获取当前界面的所有运行配置"""
        return {
            "interpreter": self.txt_interpreter.text().strip() or sys.executable,
            "script_path": self.txt_script_path.text().strip(),
            "args": self.txt_args.text().strip(),
            "work_dir": self.txt_work_dir.text().strip()
        }

    def set_config(self, config: dict):
        """恢复保存的运行配置"""
        if "interpreter" in config and config["interpreter"]:
            self.txt_interpreter.setText(config["interpreter"])
        if "script_path" in config:
            self.txt_script_path.setText(config["script_path"])
        if "args" in config:
            self.txt_args.setText(config["args"])
        if "work_dir" in config:
            self.txt_work_dir.setText(config["work_dir"])

    def _browse_interpreter(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 Python 解释器", "/usr/bin", "Executables (*)")
        if file_path:
            self.txt_interpreter.setText(file_path)

    def _browse_script(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 Python 脚本", "", "Python Files (*.py)")
        if file_path:
            self.set_script_path(file_path)

    def _browse_workdir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if dir_path:
            self.txt_work_dir.setText(dir_path)

    def _on_run_clicked(self):
        self.run_requested.emit(self.get_config())