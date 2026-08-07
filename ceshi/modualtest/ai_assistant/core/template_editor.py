# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter, QWidget, QGroupBox
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont


class TemplateEditorDialog(QDialog):
    """模板编辑器对话框"""
    
    sig_template_updated = Signal()
    
    def __init__(self, template_manager, parent=None):
        super().__init__(parent)
        self._template_manager = template_manager
        self._current_template = None
        self._init_ui()
        self._load_templates()
    
    def _init_ui(self):
        self.setWindowTitle("📝 模板编辑器")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # ---- 主布局（左右分栏） ----
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：模板列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("📋 模板列表"))
        
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self._on_template_selected)
        self.template_list.setMinimumWidth(200)
        self.template_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #e3f2fd;
                color: #1976D2;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        left_layout.addWidget(self.template_list)
        
        # 自定义模板按钮
        custom_btn_layout = QHBoxLayout()
        
        self.btn_new_custom = QPushButton("➕ 新建自定义")
        self.btn_new_custom.clicked.connect(self._on_new_custom)
        custom_btn_layout.addWidget(self.btn_new_custom)
        
        self.btn_delete_custom = QPushButton("🗑️ 删除自定义")
        self.btn_delete_custom.clicked.connect(self._on_delete_custom)
        custom_btn_layout.addWidget(self.btn_delete_custom)
        
        custom_btn_layout.addStretch()
        left_layout.addLayout(custom_btn_layout)
        
        splitter.addWidget(left_widget)
        
        # 右侧：模板编辑区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 模板信息
        info_layout = QHBoxLayout()
        self.template_name_label = QLabel("未选择模板")
        self.template_name_label.setStyleSheet("font-weight:bold;font-size:14px;")
        info_layout.addWidget(self.template_name_label)
        
        self.template_type_label = QLabel("")
        self.template_type_label.setStyleSheet("color:#888;font-size:12px;")
        info_layout.addWidget(self.template_type_label)
        info_layout.addStretch()
        right_layout.addLayout(info_layout)
        
        # 编辑区域
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此编辑模板内容...")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 13px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        right_layout.addWidget(self.text_edit)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 保存")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 6px 20px;
                border-radius: 4px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #43A047;
            }
        """)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_reset = QPushButton("↩️ 重置")
        self.btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.btn_reset)
        
        btn_layout.addStretch()
        
        self.btn_close = QPushButton("✖ 关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([250, 550])
        
        layout.addWidget(splitter)
    
    def _load_templates(self):
        """加载模板列表"""
        self.template_list.clear()
        
        templates = self._template_manager.get_all_templates()
        
        # 系统模板（带标记）
        system_names = self._template_manager.get_system_templates().keys()
        custom_names = self._template_manager.get_custom_templates().keys()
        
        # 先显示系统模板
        for name in system_names:
            item = QListWidgetItem(f"📦 {self._template_manager.get_template_display_name(name)}")
            item.setData(Qt.UserRole, name)
            item.setData(Qt.UserRole + 1, "system")
            self.template_list.addItem(item)
        
        # 如果有自定义模板，添加分隔符
        if custom_names:
            # 添加一个分隔符
            sep_item = QListWidgetItem("────────── 自定义 ──────────")
            sep_item.setFlags(Qt.NoItemFlags)
            self.template_list.addItem(sep_item)
            
            for name in custom_names:
                item = QListWidgetItem(f"✏️ {self._template_manager.get_template_display_name(name)}")
                item.setData(Qt.UserRole, name)
                item.setData(Qt.UserRole + 1, "custom")
                self.template_list.addItem(item)
    
    def _on_template_selected(self, item: QListWidgetItem):
        """模板被选中"""
        name = item.data(Qt.UserRole)
        template_type = item.data(Qt.UserRole + 1)
        
        if not name:
            return
        
        self._current_template = name
        self._current_template_type = template_type
        
        # 显示模板信息
        display_name = self._template_manager.get_template_display_name(name)
        self.template_name_label.setText(display_name)
        
        type_text = "系统模板" if template_type == "system" else "自定义模板"
        self.template_type_label.setText(f"({type_text})")
        
        # 加载模板内容
        content = self._template_manager.get_template(name)
        if content:
            self.text_edit.setPlainText(content)
        
        # 自定义模板可以编辑和删除
        is_custom = template_type == "custom"
        self.btn_delete_custom.setEnabled(is_custom)
        self.btn_save.setEnabled(True)
        self.text_edit.setReadOnly(not is_custom)
        
        if not is_custom:
            self.text_edit.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: monospace;
                    font-size: 13px;
                    background: #f5f5f5;
                    color: #666;
                    line-height: 1.6;
                }
            """)
        else:
            self.text_edit.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: monospace;
                    font-size: 13px;
                    background: white;
                    line-height: 1.6;
                }
                QTextEdit:focus {
                    border-color: #2196F3;
                }
            """)
    
    def _on_new_custom(self):
        """新建自定义模板"""
        # 获取模板名称
        from PySide2.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "新建模板", 
            "请输入模板名称（英文或数字）:",
            text="my_template"
        )
        
        if not ok or not name:
            return
        
        # 检查是否已存在
        if name in self._template_manager.get_all_templates():
            QMessageBox.warning(self, "提示", f"模板 '{name}' 已存在，请使用其他名称")
            return
        
        # 创建模板
        default_content = f"""【任务】{name.replace('_', ' ').title()}

【项目背景】
{{context}}

【核心需求】
请根据当前项目情况，设计合理的方案：

1. 请在此添加具体需求
2. 请在此添加具体要求
3. 请在此添加具体内容

【要求】
- 结合实际项目需求
- 给出具体可执行的方案
- 按上述结构清晰输出
"""
        
        if self._template_manager.save_template(name, default_content, is_custom=True):
            QMessageBox.information(self, "成功", f"模板 '{name}' 创建成功")
            self._load_templates()
            
            # 选中新建的模板
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.data(Qt.UserRole) == name:
                    self.template_list.setCurrentItem(item)
                    self._on_template_selected(item)
                    break
        else:
            QMessageBox.warning(self, "错误", "创建模板失败")
    
    def _on_delete_custom(self):
        """删除自定义模板"""
        if not self._current_template or self._current_template_type != "custom":
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{self._template_manager.get_template_display_name(self._current_template)}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self._template_manager.delete_custom_template(self._current_template):
                QMessageBox.information(self, "成功", "模板已删除")
                self._load_templates()
                self.text_edit.clear()
                self.template_name_label.setText("未选择模板")
                self.template_type_label.setText("")
                self._current_template = None
                self.btn_delete_custom.setEnabled(False)
                self.btn_save.setEnabled(False)
            else:
                QMessageBox.warning(self, "错误", "删除模板失败")
    
    def _on_save(self):
        """保存模板"""
        if not self._current_template:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        
        if self._current_template_type != "custom":
            QMessageBox.warning(self, "提示", "系统模板不能修改，请另存为自定义模板")
            return
        
        content = self.text_edit.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "模板内容不能为空")
            return
        
        if self._template_manager.save_template(self._current_template, content, is_custom=True):
            QMessageBox.information(self, "成功", "模板已保存")
            self.sig_template_updated.emit()
        else:
            QMessageBox.warning(self, "错误", "保存模板失败")
    
    def _on_reset(self):
        """重置模板内容"""
        if not self._current_template:
            return
        
        if self._current_template_type != "custom":
            return
        
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置模板内容吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重新加载
            content = self._template_manager.get_template(self._current_template)
            if content:
                self.text_edit.setPlainText(content)