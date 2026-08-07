# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QGroupBox, QButtonGroup
)
from PySide2.QtCore import Qt, Signal


class InputView(QWidget):
    """AI 助手输入视图（文本框 + 预设按钮）"""
    
    sig_text_changed = Signal(str)
    sig_preset_clicked = Signal(int)  # 预设索引
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # ---- 文本框 ----
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "请输入您的 AI 请求...\n\n"
            "例如：\n"
            "  - 请帮我重构这段代码\n"
            "  - 解释一下这个函数的作用\n"
            "  - 为我生成单元测试"
        )
        self.text_edit.setMinimumHeight(120)
        self.text_edit.setMaximumHeight(200)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
                background: white;
            }
            QTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        layout.addWidget(self.text_edit)
        
        # ---- 预设按钮行 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        # 预设按钮数据 (名称, 图标)
        presets = [
            ("代码审查", "🔍"),
            ("代码优化", "⚡"),
            ("添加注释", "📝"),
            ("错误修复", "🔧"),
            ("功能解释", "📖"),
            ("生成测试", "🧪"),
        ]
        
        self.preset_buttons = []
        self.preset_button_group = QButtonGroup()
        self.preset_button_group.setExclusive(False)
        
        for i, (name, icon) in enumerate(presets):
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #e3f2fd;
                    border-color: #90caf9;
                }
                QPushButton:checked {
                    background: #2196F3;
                    color: white;
                    border-color: #1976D2;
                }
            """)
            btn.setToolTip(f"点击使用「{name}」模板构建请求")
            btn.clicked.connect(lambda checked, idx=i: self._on_preset_clicked(idx))
            
            self.preset_buttons.append(btn)
            self.preset_button_group.addButton(btn, i)
            btn_layout.addWidget(btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        self.text_edit.textChanged.connect(
            lambda: self.sig_text_changed.emit(self.text_edit.toPlainText())
        )
    
    def _on_preset_clicked(self, index: int):
        """预设按钮点击"""
        # 取消其他按钮的选中状态
        for i, btn in enumerate(self.preset_buttons):
            if i != index:
                btn.setChecked(False)
        
        self.sig_preset_clicked.emit(index)
    
    def get_text(self) -> str:
        return self.text_edit.toPlainText()
    
    def set_text(self, text: str):
        self.text_edit.setPlainText(text)
    
    def get_selected_preset(self) -> int:
        """获取当前选中的预设索引"""
        checked_id = self.preset_button_group.checkedId()
        return checked_id if checked_id != -1 else -1
    
    def clear_preset_selection(self):
        """清除所有预设选中状态"""
        for btn in self.preset_buttons:
            btn.setChecked(False)
    
    def set_preset_selection(self, index: int):
        """设置预设选中"""
        for i, btn in enumerate(self.preset_buttons):
            btn.setChecked(i == index)