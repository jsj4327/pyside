"""
Prompt 新增/编辑对话框组件
"""
from PySide2.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QPlainTextEdit, QFormLayout, QComboBox
)
from PySide2.QtGui import QFont

from config import STYLE_BTN_PRIMARY, STYLE_CODE_FONT, STYLE_CODE_SIZE
from models import create_prompt


class PromptEditDialog(QDialog):
    """Prompt 新增或编辑对话框。"""

    def __init__(self, parent=None, categories=None, prompt_data=None):
        super().__init__(parent)
        self.setWindowTitle("编辑 Prompt" if prompt_data else "新增 Prompt")
        self.resize(600, 480)
        self.categories = categories or []
        self.prompt_data = prompt_data or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.input_title = QLineEdit(self.prompt_data.get("title", ""))

        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        self.combo_category.addItems(self.categories)
        if "category" in self.prompt_data:
            self.combo_category.setCurrentText(self.prompt_data["category"])

        self.input_tags = QLineEdit(self.prompt_data.get("tags", ""))
        self.input_tags.setPlaceholderText("用逗号分隔，如: Python, Qt, 架构")

        self.input_prompt = QPlainTextEdit(self.prompt_data.get("prompt", ""))
        self.input_prompt.setFont(QFont(STYLE_CODE_FONT, STYLE_CODE_SIZE))

        self.input_notes = QLineEdit(self.prompt_data.get("notes", ""))

        form.addRow("标题 (*):", self.input_title)
        form.addRow("分类:", self.combo_category)
        form.addRow("标签:", self.input_tags)
        form.addRow("Prompt 内容 (*):", self.input_prompt)
        form.addRow("备注说明:", self.input_notes)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_save.clicked.connect(self.accept)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self) -> dict:
        """获取表单填写的 Prompt 数据。"""
        return create_prompt(
            title=self.input_title.text(),
            prompt=self.input_prompt.toPlainText(),
            category=self.combo_category.currentText(),
            tags=self.input_tags.text(),
            notes=self.input_notes.text(),
            id=self.prompt_data.get("id")
        )
