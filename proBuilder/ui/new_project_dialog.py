#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide2.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QPlainTextEdit, QTextBrowser, QSplitter,
    QDialogButtonBox, QLabel, QMessageBox, QFileDialog
)
from PySide2.QtGui import QFont
from core.template_manager import TemplateManager

DEFAULT_BLUEPRINT = (
    "SimpleGitClient/\n"
    "├── main.py                  # 程序的唯一入口点\n"
    "├── requirements.txt         # 项目依赖管理\n"
    "└── core/                    # 核心逻辑层\n"
    "    └── git_manager.py       # 封装 git 操作"
)

class NewProjectDialog(QDialog):
    """新建项目向导对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_path = ""
        self.blueprint_text = ""
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("新建项目与架构蓝图配置")
        self.resize(900, 700)
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: SimpleGitClient")
        form_layout.addRow("项目名称:", self.name_edit)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("选择父目录...")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.choose_parent_dir)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        form_layout.addRow("父目录:", path_layout)

        main_layout.addLayout(form_layout)

        # 左右分栏：左侧输入蓝图，右侧实时预览
        splitter = QSplitter()
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>架构蓝图输入区</b>:"))
        self.blueprint_edit = QPlainTextEdit()
        self.blueprint_edit.setPlainText(DEFAULT_BLUEPRINT)
        self.blueprint_edit.setFont(QFont("Consolas", 10))
        left_layout.addWidget(self.blueprint_edit)
        
        self.analyze_btn = QPushButton("🔍 验证并分析架构")
        self.analyze_btn.clicked.connect(self.on_analyze)
        left_layout.addWidget(self.analyze_btn)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>架构分析预览空间</b>:"))
        self.analysis_browser = QTextBrowser()
        self.analysis_browser.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self.analysis_browser)
        splitter.addWidget(right_widget)

        splitter.setSizes([450, 450])
        main_layout.addWidget(splitter)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def choose_parent_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择父目录")
        if dir_path:
            self.path_edit.setText(dir_path)

    def on_analyze(self):
        text = self.blueprint_edit.toPlainText().strip()
        if not text:
            self.analysis_browser.setPlainText("错误: 蓝图内容为空！")
            return
        summary, folders, files, _ = TemplateManager.parse_blueprint(text)
        report = f"=== 架构解析成功 ===\n📁 统计目录数: {folders}\n📄 统计文件数: {files}\n\n" + summary
        self.analysis_browser.setPlainText(report)

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        parent = self.path_edit.text().strip()
        blueprint = self.blueprint_edit.toPlainText().strip()

        if not name or not parent:
            QMessageBox.warning(self, "错误", "请填写完整的项目名称和父目录！")
            return
        
        self.project_path = os.path.join(parent, name)
        if os.path.exists(self.project_path):
            QMessageBox.warning(self, "错误", "目标项目目录已存在！")
            return

        self.blueprint_text = blueprint
        self.accept()