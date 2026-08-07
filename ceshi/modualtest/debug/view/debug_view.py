# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QComboBox, QLabel, QGroupBox,
    QMessageBox, QApplication, QLineEdit, QMenu, QAction,
    QDialog, QDialogButtonBox
)
from PySide2.QtCore import Qt, Signal, QPoint, QSettings
from PySide2.QtGui import QFont, QTextCursor
import os


class TemplateEditDialog(QDialog):
    """模板编辑对话框"""
    
    def __init__(self, template_name: str, template_content: str, parent=None):
        super().__init__(parent)
        self.template_name = template_name
        self.template_content = template_content
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle(f"编辑模板: {self.template_name}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        label = QLabel(f"模板: {self.template_name}")
        label.setStyleSheet("font-weight:bold;font-size:14px;")
        layout.addWidget(label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.template_content)
        self.text_edit.setFont(QFont("Consolas", 12))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.text_edit)
        
        hint = QLabel("提示: 使用 {$1} 作为占位符，用户输入将替换此位置")
        hint.setStyleSheet("color:#888;font-size:11px;")
        layout.addWidget(hint)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_content(self) -> str:
        return self.text_edit.toPlainText()


class FeedbackPreviewDialog(QDialog):
    """反馈预览对话框 - 可编辑"""
    
    def __init__(self, feedback_text: str, parent=None):
        super().__init__(parent)
        self.feedback_text = feedback_text
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("反馈内容预览（可编辑修改）")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("以下是即将发送的反馈内容，您可以编辑修改：")
        label.setStyleSheet("font-weight:bold;font-size:13px;")
        layout.addWidget(label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.feedback_text)
        self.text_edit.setReadOnly(False)
        self.text_edit.setFont(QFont("Consolas", 11))
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background: #ffffff;
                color: #2c2c2c;
                font-family: Consolas, monospace;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.text_edit)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_copy = QPushButton("复制内容")
        btn_copy.clicked.connect(self._on_copy)
        btn_copy.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        button_layout.addWidget(btn_copy)
        
        btn_send = QPushButton("确认发送")
        btn_send.clicked.connect(self._on_send)
        btn_send.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                background: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #43A047;
            }
        """)
        button_layout.addWidget(btn_send)
        
        btn_close = QPushButton("取消")
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
    
    def _on_copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "提示", "反馈内容已复制到剪贴板")
    
    def _on_send(self):
        """确认发送 - 使用编辑后的内容"""
        self.feedback_text = self.text_edit.toPlainText()
        self.accept()
    
    def get_edited_content(self) -> str:
        """获取编辑后的内容"""
        return self.feedback_text


class DebugOutputView(QWidget):
    """调试输出视图"""
    
    sig_run_clicked = Signal()
    sig_feedback_clicked = Signal()
    sig_preview_clicked = Signal()
    sig_template_changed = Signal(str)
    sig_clear_clicked = Signal()
    sig_template_edited = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._templates = {}
        self._template_dir = self._get_template_dir()
        self._settings = QSettings("DebugModule", "Placeholder")
        self._init_ui()
        self._connect_signals()
        self._setup_context_menu()
        self._load_placeholder_history()
        self._load_attach_mode()
    
    def _get_template_dir(self) -> str:
        """获取模板目录路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        debug_dir = os.path.dirname(os.path.dirname(current_dir))
        template_dir = os.path.join(debug_dir, "core", "templates")
        
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
            self._create_default_templates(template_dir)
        
        return template_dir
    
    def _create_default_templates(self, template_dir: str):
        """创建默认模板文件"""
        defaults = {
            "debug_default.txt": """请分析以下 Python 代码的执行结果：

{$1}

请分析输出结果并提供建议。""",

            "debug_error.txt": """请分析以下 Python 代码的错误：

{$1}

请分析错误原因并提供修复建议。""",

            "debug_performance.txt": """请分析以下 Python 代码的性能问题：

{$1}

请分析性能瓶颈并提供优化建议。""",

            "debug_general.txt": """请分析以下 Python 代码的执行结果：

{$1}

请根据以上信息进行分析并提供建议。"""
        }
        
        for filename, content in defaults.items():
            filepath = os.path.join(template_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def _load_templates_from_dir(self):
        """从模板目录加载所有 txt 文件"""
        self._templates = {}
        
        if not os.path.exists(self._template_dir):
            return
        
        for filename in os.listdir(self._template_dir):
            if filename.endswith('.txt'):
                name = filename[:-4]
                filepath = os.path.join(self._template_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self._templates[name] = content
                except Exception as e:
                    print(f"[DEBUG-VIEW] 加载模板失败 {filename}: {e}")
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        main_group = QGroupBox("调试输出")
        main_layout = QVBoxLayout(main_group)
        main_layout.setSpacing(6)
        
        # ---- 第一行：控制栏 ----
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        self.btn_run = QPushButton("执行")
        self.btn_run.setFixedHeight(30)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 4px 16px;
                border-radius: 4px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #43A047;
            }
            QPushButton:disabled {
                background: #a5d6a7;
            }
        """)
        control_layout.addWidget(self.btn_run)
        
        # ---- 模板下拉框 ----
        self.template_combo = QComboBox()
        self.template_combo.setFixedHeight(30)
        self.template_combo.setMinimumWidth(150)
        self.template_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
                color: #2c2c2c;
            }
            QComboBox:hover {
                border-color: #90caf9;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #2c3e50;
                selection-color: #ffffff;
                color: #2c2c2c;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                min-height: 25px;
                color: #2c2c2c;
                background: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #e3f2fd;
                color: #2c2c2c;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #2c3e50;
                color: #ffffff;
            }
        """)
        control_layout.addWidget(self.template_combo)
        
        self.btn_feedback = QPushButton("反馈")
        self.btn_feedback.setFixedHeight(30)
        self.btn_feedback.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                font-weight: bold;
                padding: 4px 16px;
                border-radius: 4px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #F57C00;
            }
            QPushButton:disabled {
                background: #ffcc80;
            }
        """)
        control_layout.addWidget(self.btn_feedback)
        
        # ---- 预览按钮 ----
        self.btn_preview = QPushButton("预览")
        self.btn_preview.setFixedHeight(30)
        self.btn_preview.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border-radius: 4px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """)
        control_layout.addWidget(self.btn_preview)
        
        self.btn_clear = QPushButton("清空")
        self.btn_clear.setFixedHeight(30)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                color: #333;
                padding: 4px 12px;
                border-radius: 4px;
                border: 1px solid #ccc;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #d5d5d5;
            }
        """)
        control_layout.addWidget(self.btn_clear)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#666;font-size:12px;")
        control_layout.addWidget(self.status_label)
        
        main_layout.addLayout(control_layout)
        
        # ---- 第二行：文件信息 + 占位符输入 + 附加内容下拉 ----
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        
        self.file_label = QLabel("文件: 未选择")
        self.file_label.setStyleSheet("color:#2c2c2c;font-size:11px;font-weight:bold;")
        self.file_label.setMinimumWidth(150)
        info_layout.addWidget(self.file_label)
        
        # 占位符输入框
        self.placeholder_input = QLineEdit()
        self.placeholder_input.setFixedHeight(26)
        self.placeholder_input.setMaximumWidth(200)
        self.placeholder_input.setPlaceholderText("输入内容替换 {$1}")
        self.placeholder_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 2px 8px;
                background: white;
                font-size: 12px;
                font-family: Consolas, monospace;
                color: #2c2c2c;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        info_layout.addWidget(self.placeholder_input)
        
        # ---- 附加内容下拉框 ----
        self.attach_combo = QComboBox()
        self.attach_combo.setFixedHeight(26)
        self.attach_combo.setMinimumWidth(140)
        self.attach_combo.addItem("不附加文件", "none")
        self.attach_combo.addItem("附加选中文件", "file")
        self.attach_combo.addItem("附加当前文件夹", "folder")
        self.attach_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 2px 8px;
                background: white;
                color: #2c2c2c;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #90caf9;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                selection-background-color: #2c3e50;
                selection-color: #ffffff;
                color: #2c2c2c;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                min-height: 25px;
                color: #2c2c2c;
                background: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #e3f2fd;
                color: #2c2c2c;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #2c3e50;
                color: #ffffff;
            }
        """)
        info_layout.addWidget(self.attach_combo)
        
        info_layout.addStretch()
        
        self.exit_code_label = QLabel("")
        self.exit_code_label.setStyleSheet("color:#2c2c2c;font-size:11px;")
        info_layout.addWidget(self.exit_code_label)
        
        main_layout.addLayout(info_layout)
        
        # ---- 第三行：输出区域 ----
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setFont(QFont("Consolas", 10))
        self.output_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, monospace;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        self.output_edit.setMinimumHeight(200)
        self.output_edit.setPlainText("")
        main_layout.addWidget(self.output_edit)
        
        layout.addWidget(main_group)
        
        # 加载模板
        self._load_templates_from_dir()
        self._update_template_combo()
    
    def _load_placeholder_history(self):
        """加载占位符历史记录"""
        history = self._settings.value("history", "")
        if history:
            self.placeholder_input.setText(history)
    
    def _save_placeholder_history(self):
        """保存占位符历史记录"""
        text = self.placeholder_input.text()
        if text:
            self._settings.setValue("history", text)
            self._settings.sync()
    
    def _load_attach_mode(self):
        """加载附加模式历史记录"""
        mode = self._settings.value("attach_mode", "none")
        index = self.attach_combo.findData(mode)
        if index >= 0:
            self.attach_combo.setCurrentIndex(index)
    
    def _save_attach_mode(self):
        """保存附加模式"""
        mode = self.attach_combo.currentData()
        self._settings.setValue("attach_mode", mode)
        self._settings.sync()
    
    def _update_template_combo(self):
        """更新下拉框"""
        self.template_combo.clear()
        
        sorted_names = sorted(self._templates.keys())
        
        for name in sorted_names:
            display = name.replace("_", " ").title()
            self.template_combo.addItem(display, name)
        
        if self.template_combo.count() > 0:
            self.template_combo.setCurrentIndex(0)
    
    def _setup_context_menu(self):
        """设置输出区域的右键菜单"""
        self.output_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output_edit.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)
        
        edit_action = QAction("编辑模板", self)
        edit_action.triggered.connect(self._on_edit_template)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        clear_action = QAction("清空输出", self)
        clear_action.triggered.connect(self._on_clear_clicked)
        menu.addAction(clear_action)
        
        menu.exec_(self.output_edit.mapToGlobal(pos))
    
    def _on_edit_template(self):
        """编辑当前选中的模板"""
        current_name = self.template_combo.currentData()
        if not current_name:
            QMessageBox.warning(self, "提示", "没有可编辑的模板")
            return
        
        content = self._templates.get(current_name, "")
        
        dialog = TemplateEditDialog(current_name, content, self)
        if dialog.exec_() == QDialog.Accepted:
            new_content = dialog.get_content()
            if new_content:
                filepath = os.path.join(self._template_dir, f"{current_name}.txt")
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self._templates[current_name] = new_content
                    self.sig_template_edited.emit(current_name, new_content)
                    QMessageBox.information(self, "成功", f"模板 '{current_name}' 已保存")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"保存模板失败: {e}")
    
    def _connect_signals(self):
        self.btn_run.clicked.connect(self.sig_run_clicked)
        self.btn_feedback.clicked.connect(self.sig_feedback_clicked)
        self.btn_preview.clicked.connect(self.sig_preview_clicked)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        self.placeholder_input.textChanged.connect(self._save_placeholder_history)
        self.attach_combo.currentIndexChanged.connect(self._save_attach_mode)
    
    def _on_clear_clicked(self):
        self.output_edit.clear()
        self.exit_code_label.setText("")
        self.sig_clear_clicked.emit()
    
    def _on_template_changed(self, text: str):
        if text:
            name = self.template_combo.currentData()
            if name:
                self.sig_template_changed.emit(name)
    
    def get_current_template(self) -> str:
        return self.template_combo.currentData()
    
    def get_placeholder_text(self) -> str:
        """获取用户输入的占位符内容 - 原样返回"""
        return self.placeholder_input.text()
    
    def get_attach_mode(self) -> str:
        return self.attach_combo.currentData()
    
    def append_output(self, text: str, output_type: str = "out"):
        if output_type == "out":
            color = "#4CAF50"
        elif output_type == "err":
            color = "#f44336"
        elif output_type == "warn":
            color = "#FF9800"
        elif output_type == "info":
            color = "#2196F3"
        else:
            color = "#d4d4d4"
        
        escaped_text = self._escape_html(text)
        colored_text = f'<span style="color:{color}">{escaped_text}</span>'
        self.output_edit.append(colored_text)
        
        cursor = self.output_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_edit.setTextCursor(cursor)
    
    def _escape_html(self, text: str) -> str:
        replacements = [
            ('&', '&amp;'),
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#39;'),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text
    
    def append_separator(self):
        self.output_edit.append("-" * 60)
    
    def clear_output(self):
        self.output_edit.clear()
        self.exit_code_label.setText("")
    
    def get_output(self) -> str:
        return self.output_edit.toPlainText()
    
    def get_full_output(self) -> str:
        """获取完整的执行输出"""
        return self.output_edit.toPlainText()
    
    def update_status(self, status: str, info: str = ""):
        if status == "running":
            self.status_label.setText("运行中...")
            self.status_label.setStyleSheet("color:#FF9800;font-size:12px;font-weight:bold;")
            self.btn_run.setEnabled(False)
            self.btn_feedback.setEnabled(False)
            self.btn_preview.setEnabled(False)
        elif status == "done":
            self.status_label.setText("完成")
            self.status_label.setStyleSheet("color:#4CAF50;font-size:12px;font-weight:bold;")
            self.btn_run.setEnabled(True)
            self.btn_feedback.setEnabled(True)
            self.btn_preview.setEnabled(True)
        elif status == "error":
            self.status_label.setText("执行失败")
            self.status_label.setStyleSheet("color:#f44336;font-size:12px;font-weight:bold;")
            self.btn_run.setEnabled(True)
            self.btn_feedback.setEnabled(True)
            self.btn_preview.setEnabled(True)
        else:
            self.status_label.setText(info if info else "就绪")
            self.status_label.setStyleSheet("color:#666;font-size:12px;")
            self.btn_run.setEnabled(True)
            self.btn_feedback.setEnabled(True)
            self.btn_preview.setEnabled(True)
    
    def set_file_info(self, file_path: str):
        if file_path:
            filename = os.path.basename(file_path)
            self.file_label.setText(f"文件: {filename}")
            self.file_label.setToolTip(file_path)
            self.file_label.setStyleSheet("color:#2c2c2c;font-size:11px;font-weight:bold;")
        else:
            self.file_label.setText("文件: 未选择")
            self.file_label.setToolTip("")
            self.file_label.setStyleSheet("color:#999;font-size:11px;")
    
    def set_exit_info(self, exit_code: int, duration: float):
        if exit_code == 0:
            color = "#4CAF50"
            icon = "[OK]"
        else:
            color = "#f44336"
            icon = "[X]"
        self.exit_code_label.setText(
            f'{icon} 退出码: {exit_code}  |  耗时: {duration:.2f}s'
        )
        self.exit_code_label.setStyleSheet(f"color:{color};font-size:11px;")
    
    def set_run_enabled(self, enabled: bool):
        self.btn_run.setEnabled(enabled)
    
    def get_template_content(self, name: str) -> str:
        """获取模板内容"""
        return self._templates.get(name, "")
    
    def refresh_templates(self):
        """刷新模板列表"""
        self._load_templates_from_dir()
        self._update_template_combo()