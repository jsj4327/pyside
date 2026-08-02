# -*- coding: utf-8 -*-

"""
源码浏览器主模块 (Tab3 集成组件)
"""

import os
from typing import Optional
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QMessageBox, QLabel
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor, QBrush

from .code_view_editor import CodeViewEditor
from .search_bar import SearchBar
from .symbol_parser import SymbolParser


class SourceViewerWidget(QWidget):
    """源码浏览器核心控件（适配 Tab3）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file_path = ""
        self._is_loading_file = False  # 防止初次加载文件时触发已修改状态
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部搜索栏
        self.search_bar = SearchBar()
        self.search_bar.search_triggered.connect(self.perform_search)
        layout.addWidget(self.search_bar)

        # 主体左右分割器（左侧代码，右侧大纲树）
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧容器（编辑器）
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.file_label = QLabel(" 📄 未打开文件")
        self.file_label.setStyleSheet("background: #f1f3f4; padding: 5px; font-weight: bold; border-bottom: 1px solid #ddd;")
        left_layout.addWidget(self.file_label)

        self.editor = CodeViewEditor()
        self.editor.saved.connect(self.save_current_file)
        self.editor.textChanged.connect(self._on_text_modified)
        
        left_layout.addWidget(self.editor)
        self.splitter.addWidget(left_container)

        # 右侧容器（结构树大纲）
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        outline_label = QLabel(" 🌳 结构大纲 (类与方法)")
        outline_label.setStyleSheet("background: #f1f3f4; padding: 5px; font-weight: bold; border-bottom: 1px solid #ddd;")
        right_layout.addWidget(outline_label)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        right_layout.addWidget(self.tree_widget)

        self.splitter.addWidget(right_container)
        self.splitter.setSizes([600, 200])

        layout.addWidget(self.splitter, 1)

        self.current_content = ""
        self.current_ext = ".py"

    def open_file(self, file_path: str):
        """加载文件到源码浏览器并构建结构树"""
        if not os.path.exists(file_path):
            return

        try:
            self._is_loading_file = True  # 加锁，避免触发修改状态
            self.current_file_path = os.path.abspath(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            self.current_content = content
            self.current_ext = os.path.splitext(file_path)[1]

            self.editor.setPlainText(content)
            self.file_label.setText(f" 📄 {self.current_file_path}")

            self.build_outline_tree(content, self.current_ext)
            self._is_loading_file = False  # 解锁

        except Exception as e:
            self._is_loading_file = False
            QMessageBox.warning(self, "错误", f"无法加载文件:\n{str(e)}")

    def save_current_file(self, content: str):
        """通过 Ctrl+S 触发的保存槽函数"""
        if not self.current_file_path:
            QMessageBox.warning(self, "提示", "当前没有打开可保存的文件！")
            return
            
        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            # 保存后更新提示，去掉已修改
            self.file_label.setText(f" 📄 {self.current_file_path}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法写入文件:\n{str(e)}")

    def _on_text_modified(self):
        """当源码被编辑、撤销时触发"""
        if self._is_loading_file:
            return

        content = self.editor.toPlainText()
        
        # 只要内容和初始加载的不一样，就在标签后加上 (已修改)
        if content != self.current_content:
            if "(已修改)" not in self.file_label.text():
                current_text = self.file_label.text().replace(" (已修改)", "")
                self.file_label.setText(f"{current_text} (已修改)")
        else:
            current_text = self.file_label.text().replace(" (已修改)", "")
            self.file_label.setText(current_text)

        # 实时更新右侧大纲树
        self.build_outline_tree(content, self.current_ext)

    def build_outline_tree(self, content: str, ext: str):
        """填充右侧树状结构：C为红色，F为蓝色"""
        self.tree_widget.clear()
        symbols = SymbolParser.parse_symbols(content, ext)

        root_item = self.tree_widget.invisibleRootItem()
        current_class_item = None

        for sym_type, name, line_num in symbols:
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, line_num)

            if sym_type == 'class':
                item.setText(0, f"[C] {name} (行 {line_num})")
                item.setForeground(0, QBrush(QColor("#D32F2F")))
                root_item.addChild(item)
                current_class_item = item
            elif sym_type == 'method':
                item.setText(0, f"[F] {name} (行 {line_num})")
                item.setForeground(0, QBrush(QColor("#1976D2")))
                
                if current_class_item:
                    current_class_item.addChild(item)
                else:
                    root_item.addChild(item)

        self.tree_widget.expandAll()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击右侧树节点跳转到对应行"""
        line_num = item.data(0, Qt.UserRole)
        if line_num:
            self.editor.jump_to_line(line_num)

    def perform_search(self, keyword: str):
        """根据关键字搜索并跳转到匹配行"""
        if not keyword:
            return
        document = self.editor.document()
        cursor = self.editor.textCursor()
        
        found_cursor = document.find(keyword, cursor)
        if not found_cursor.isNull():
            self.editor.setTextCursor(found_cursor)
            self.editor.centerCursor()
        else:
            start_cursor = document.find(keyword, 0)
            if not start_cursor.isNull():
                self.editor.setTextCursor(start_cursor)
                self.editor.centerCursor()
            else:
                QMessageBox.information(self, "提示", f"未找到关键字: {keyword}")