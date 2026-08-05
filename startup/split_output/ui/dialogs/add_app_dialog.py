import os
from PySide2.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QMessageBox
)
from PySide2.QtGui import QFont

from ui.widgets.drop_zone import DropZone
from utils.path_utils import get_relative_path
from config.constants import DEFAULT_CATEGORIES

class AddAppDialog(QDialog):
    """添加应用对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新程序")
        self.setFixedSize(420, 730)
        self.result_data = None

        self.setStyleSheet("""
            QDialog { background-color: #2A2A3E; }
            QLabel { color: #D0D0D0; background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("添加新 Python 程序")
        title.setFont(QFont("Noto Sans CJK SC", 14, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; margin-bottom: 4px;")
        layout.addWidget(title)

        lbl_name = QLabel("程序名称（可自定义）")
        lbl_name.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_name)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("拖入py文件将自动填充名称，也可以手动修改")
        self.name_edit.setFixedHeight(38)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px 10px;
                color: white;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; }
        """)
        layout.addWidget(self.name_edit)

        lbl_exe = QLabel("① 拖入 .py 文件")
        lbl_exe.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_exe)
        self.drop_exe = DropZone("将 Python 脚本拖放到此处", accept_mode="exe")
        self.drop_exe.pathDropped.connect(self._on_py_file_drop)
        layout.addWidget(self.drop_exe)

        lbl_icon = QLabel("② 拖入图标文件 (.png / .svg / .ico)")
        lbl_icon.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_icon)
        self.drop_icon = DropZone("将图标拖放到此处（可选）", accept_mode="image")
        layout.addWidget(self.drop_icon)

        lbl_cat = QLabel("③ 选择或输入分类")
        lbl_cat.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_cat)

        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.lineEdit().setPlaceholderText("选择或输入新分类...")
        self.cat_combo.addItems(DEFAULT_CATEGORIES)
        self.cat_combo.setFixedHeight(38)
        self.cat_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px 10px;
                color: white;
            }
            QComboBox:focus { border: 1px solid #3B82F6; }
            QComboBox QAbstractItemView {
                background-color: #2A2A3E;
                color: white;
                selection-background-color: #3B82F6;
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
            }
        """)
        layout.addWidget(self.cat_combo)

        lbl_desc = QLabel("④ 中文说明（可选，最多2行）")
        lbl_desc.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_desc)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("输入程序的中文说明...\n支持换行，最多显示2行")
        self.desc_edit.setFixedHeight(60)
        self.desc_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 8px 12px;
                color: #E0E0E0;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #3B82F6;
                background-color: rgba(255,255,255,0.12);
            }
        """)
        layout.addWidget(self.desc_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.08); color: #A0A0A0; border-radius: 6px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); color: #E0E0E0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确定添加")
        confirm_btn.setFixedSize(100, 36)
        confirm_btn.setStyleSheet("""
            QPushButton { background-color: #3B82F6; color: white; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_py_file_drop(self, file_path):
        filename = os.path.splitext(os.path.basename(file_path))[0]
        self.name_edit.setText(filename)

    def _on_confirm(self):
        exe_path = self.drop_exe.current_path
        icon_path = self.drop_icon.current_path

        app_name = self.name_edit.text().strip()
        category_text = self.cat_combo.currentText().strip()
        if not category_text:
            category_text = "未分类"

        description = self.desc_edit.toPlainText().strip()

        if not exe_path:
            QMessageBox.warning(self, "提示", "请先拖入一个 Python 脚本文件 (.py)")
            return
        if not app_name:
            QMessageBox.warning(self, "提示", "请填写程序名称！")
            return

        relative_exe_path = get_relative_path(exe_path)
        relative_icon_path = get_relative_path(icon_path) if icon_path else None

        self.result_data = {
            "name": app_name,
            "icon": relative_icon_path,
            "exe_path": relative_exe_path,
            "category": category_text,
            "description": description
        }
        self.accept()
