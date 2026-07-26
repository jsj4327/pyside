#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QFileSystemModel
from PySide2.QtCore import Qt, QDir, Signal
from PySide2.QtGui import QColor, QIcon

class FileTreeWidget(QWidget):
    """项目文件树及实时修改监控面板"""
    file_double_clicked = Signal(str)  # 信号：双击打开文件路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_root = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶栏按钮
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>项目文件浏览</b>"))
        
        self.btn_export = QPushButton("导出AI结构")
        header_layout.addWidget(self.btn_export)
        
        self.btn_open_folder = QPushButton("打开目录")
        header_layout.addWidget(self.btn_open_folder)
        
        layout.addLayout(header_layout)

        # QTreeView 文件模型
        self.tree_view = QTreeView()
        self.tree_model = QFileSystemModel()
        self.tree_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.doubleClicked.connect(self.on_tree_double_click)
        layout.addWidget(self.tree_view)

        # 修改状态监控树
        layout.addWidget(QLabel("<b>实时修改监控 (5分钟内/15分钟内)</b>:"))
        self.mod_tree = QTreeWidget()
        self.mod_tree.setHeaderLabels(["文件 / 状态"])
        self.mod_tree.itemDoubleClicked.connect(self.on_mod_tree_double_click)
        layout.addWidget(self.mod_tree)

    def set_root_path(self, path: str):
        self.project_root = path
        self.tree_model.setRootPath(path)
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.tree_view.setColumnWidth(0, 150)
        self.refresh_modification_tree()

    def on_tree_double_click(self, index):
        file_path = self.tree_model.filePath(index)
        if os.path.isfile(file_path):
            self.file_double_clicked.emit(file_path)

    def on_mod_tree_double_click(self, item, column):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.isfile(file_path):
            self.file_double_clicked.emit(file_path)

    def refresh_modification_tree(self):
        """扫描项目文件修改时间，分级显示热度"""
        if not self.project_root or not os.path.isdir(self.project_root):
            return

        self.mod_tree.clear()
        root_name = os.path.basename(self.project_root)
        root_item = QTreeWidgetItem([root_name])
        self.mod_tree.addTopLevelItem(root_item)

        now = datetime.now()

        def scan_dir(current_dir, parent_item):
            try:
                entries = sorted(os.listdir(current_dir))
            except Exception:
                return

            for entry in entries:
                if entry.startswith('.'):
                    continue
                full_path = os.path.join(current_dir, entry)
                if os.path.isdir(full_path):
                    dir_item = QTreeWidgetItem([entry + "/"])
                    parent_item.addChild(dir_item)
                    scan_dir(full_path, dir_item)
                elif os.path.isfile(full_path):
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                        delta_min = (now - mtime).total_seconds() / 60.0
                    except Exception:
                        delta_min = 9999

                    if delta_min <= 5:
                        display_text = f"{entry} (⚡ 5分钟内)"
                        color = QColor("#D32F2F")  # 红
                    elif delta_min <= 15:
                        display_text = f"{entry} (🕒 15分钟内)"
                        color = QColor("#1976D2")  # 蓝
                    else:
                        display_text = f"{entry} (常规)"
                        color = QColor("#388E3C")  # 绿

                    file_item = QTreeWidgetItem([display_text])
                    file_item.setData(0, Qt.UserRole, full_path)
                    file_item.setForeground(0, color)
                    parent_item.addChild(file_item)

        scan_dir(self.project_root, root_item)
        self.mod_tree.expandAll()