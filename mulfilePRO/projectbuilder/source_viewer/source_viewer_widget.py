# -*- coding: utf-8 -*-

"""
源码浏览器主模块 (Tab3 集成组件)
添加行数状态栏 + 保存后返回文件浏览器的复选框
"""

import os
from typing import Optional
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QMessageBox, QLabel,
    QPlainTextEdit, QCheckBox
)
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor, QBrush

from .code_view_editor import CodeViewEditor
from .search_bar import SearchBar
from .symbol_parser import SymbolParser


class SourceViewerWidget(QWidget):
    """源码浏览器核心控件（适配 Tab3）"""

    # 自定义信号：请求切换到文件浏览器Tab
    switch_to_file_browser = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file_path = ""
        self._is_loading_file = False
        self._initial_line_count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 搜索栏
        self.search_bar = SearchBar()
        self.search_bar.search_triggered.connect(self.perform_search)
        layout.addWidget(self.search_bar)

        # ---- 行数状态栏 + 复选框 ----
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(5, 2, 5, 2)
        status_layout.setSpacing(10)

        self.lbl_lines = QLabel("行数: 0")
        status_layout.addWidget(self.lbl_lines)

        self.lbl_pasted_lines = QLabel("粘贴后行数: 0")
        status_layout.addWidget(self.lbl_pasted_lines)

        self.lbl_compare = QLabel("比较: -")
        self.lbl_compare.setStyleSheet("font-weight: bold; color: gray;")
        status_layout.addWidget(self.lbl_compare)

        status_layout.addStretch()

        # ---- 新增：保存后返回文件浏览器复选框 ----
        self.chk_switch_after_save = QCheckBox("保存后返回文件浏览器")
        self.chk_switch_after_save.setToolTip("勾选后，Ctrl+S 保存文件后自动切换到文件浏览器选项卡")
        status_layout.addWidget(self.chk_switch_after_save)

        layout.addLayout(status_layout)

        # ---- 主体：编辑器 + 结构树大纲 ----
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

        # 初始化行数显示
        self._update_line_status()

    # ---------- 打开文件 ----------
    def open_file(self, file_path: str):
        """加载文件到源码浏览器并构建结构树"""
        if not os.path.exists(file_path):
            return

        try:
            self._is_loading_file = True
            self.current_file_path = os.path.abspath(file_path)

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            self.current_content = content
            self.current_ext = os.path.splitext(file_path)[1]

            self.editor.setPlainText(content)
            self.file_label.setText(f" 📄 {self.current_file_path}")

            # 记录初始行数
            self._initial_line_count = self._count_lines(content)
            self._update_line_status()

            self.build_outline_tree(content, self.current_ext)
            self._is_loading_file = False

        except Exception as e:
            self._is_loading_file = False
            QMessageBox.warning(self, "错误", f"无法加载文件:\n{str(e)}")

    # ---------- 保存文件 ----------
    def save_current_file(self, content: str):
        """通过 Ctrl+S 触发的保存槽函数"""
        if not self.current_file_path:
            QMessageBox.warning(self, "提示", "当前没有打开可保存的文件！")
            return

        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.file_label.setText(f" 📄 {self.current_file_path}")
            self.current_content = content
            self._initial_line_count = self._count_lines(content)
            self._update_line_status()

            # ---- 新增：如果勾选了“保存后返回文件浏览器”，则发出信号 ----
            if self.chk_switch_after_save.isChecked():
                self.switch_to_file_browser.emit()

        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法写入文件:\n{str(e)}")

    # ---------- 内容变化处理 ----------
    def _on_text_modified(self):
        """当源码被编辑、撤销、粘贴时触发"""
        if self._is_loading_file:
            return

        content = self.editor.toPlainText()
        current_line_count = self._count_lines(content)

        # 更新文件标签的"已修改"状态
        if content != self.current_content:
            if "(已修改)" not in self.file_label.text():
                current_text = self.file_label.text().replace(" (已修改)", "")
                self.file_label.setText(f"{current_text} (已修改)")
        else:
            current_text = self.file_label.text().replace(" (已修改)", "")
            self.file_label.setText(current_text)

        # 更新行数状态栏
        self._update_line_status(current_line_count)

        # 实时更新右侧大纲树
        self.build_outline_tree(content, self.current_ext)

    # ---------- 行数状态更新 ----------
    def _update_line_status(self, current_lines=None):
        """更新行数状态栏"""
        if current_lines is None:
            content = self.editor.toPlainText()
            current_lines = self._count_lines(content)

        self.lbl_lines.setText(f"行数: {current_lines}")
        self.lbl_pasted_lines.setText(f"粘贴后行数: {current_lines}")

        # 比较当前行数与初始行数
        if self._initial_line_count > 0:
            diff = current_lines - self._initial_line_count
            if diff > 0:
                self.lbl_compare.setText("大于 ↑")
                self.lbl_compare.setStyleSheet("color: green; font-weight: bold;")
            elif diff < 0:
                self.lbl_compare.setText("小于 ↓")
                self.lbl_compare.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.lbl_compare.setText("等于 =")
                self.lbl_compare.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.lbl_compare.setText("比较: -")
            self.lbl_compare.setStyleSheet("font-weight: bold; color: gray;")

    # ---------- 辅助方法 ----------
    @staticmethod
    def _count_lines(text: str) -> int:
        """计算行数（即使末尾无换行也正确）"""
        if not text:
            return 0
        return text.count('\n') + (1 if text and not text.endswith('\n') else 0)

    # ---------- 结构树构建 ----------
    def build_outline_tree(self, content: str, ext: str):
        """填充右侧树状结构"""
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

    # ---------- 导航 ----------
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        line_num = item.data(0, Qt.UserRole)
        if line_num:
            self.editor.jump_to_line(line_num)

    # ---------- 搜索 ----------
    def perform_search(self, keyword: str):
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