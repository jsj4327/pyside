# -*- coding:utf-8 -*-
import os
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QFileSystemModel,
    QHeaderView, QMenu, QAction, QInputDialog, QApplication,
    QShortcut, QAbstractItemView
)
from PySide2.QtCore import Qt, QDir, Signal
from PySide2.QtGui import QKeySequence


class TreeView(QWidget):
    """文件浏览器树视图"""

    sig_navigate_to = Signal(str)
    sig_file_double_clicked = Signal(str)
    sig_file_selected = Signal(str)
    sig_file_delete = Signal(str)
    sig_file_rename = Signal(str, str)
    sig_folder_create = Signal(str)
    sig_file_create = Signal(str)
    sig_copy = Signal(list)
    sig_cut = Signal(list)
    sig_paste = Signal()
    sig_show_properties = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clipboard_has_content = False
        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(QDir.homePath())
        self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setRootIndex(self.tree_model.index(QDir.homePath()))
        self.tree_view.setColumnWidth(0, 250)
        self.tree_view.setColumnWidth(1, 80)
        self.tree_view.setColumnWidth(2, 80)
        self.tree_view.setColumnWidth(3, 150)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.tree_view.setStyleSheet("""
            QTreeView {
                alternate-background-color: #f5f5f5;
                background-color: white;
                selection-background-color: #cce5ff;
                selection-color: #000000;
                outline: 0;
                show-decoration-selected: 0;
            }
            QTreeView::item {
                padding: 2px;
                border: none;
                margin: 0px;
            }
            QTreeView::item:selected {
                background-color: #cce5ff;
                color: #000000;
                border: none;
                margin: 0px;
            }
            QTreeView::item:hover {
                background-color: #e8f0fe;
            }
        """)

        layout.addWidget(self.tree_view)

    def _connect_signals(self):
        self.tree_view.doubleClicked.connect(self._on_double_clicked)
        self.tree_view.clicked.connect(self._on_clicked)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_shortcuts(self):
        shortcut = QShortcut(QKeySequence("Ctrl+C"), self.tree_view)
        shortcut.activated.connect(lambda: self._trigger_copy())

        shortcut = QShortcut(QKeySequence("Ctrl+X"), self.tree_view)
        shortcut.activated.connect(lambda: self._trigger_cut())

        shortcut = QShortcut(QKeySequence("Ctrl+V"), self.tree_view)
        shortcut.activated.connect(self.sig_paste.emit)

        shortcut = QShortcut(QKeySequence("Delete"), self.tree_view)
        shortcut.activated.connect(lambda: self._trigger_delete())

        shortcut = QShortcut(QKeySequence("F2"), self.tree_view)
        shortcut.activated.connect(lambda: self._trigger_rename())

    def _trigger_copy(self):
        paths = self.get_selected_paths()
        if paths:
            self.sig_copy.emit(paths)

    def _trigger_cut(self):
        paths = self.get_selected_paths()
        if paths:
            self.sig_cut.emit(paths)

    def _trigger_delete(self):
        paths = self.get_selected_paths()
        if paths:
            self.sig_file_delete.emit(paths)

    def _trigger_rename(self):
        paths = self.get_selected_paths()
        if len(paths) == 1:
            self._show_rename_dialog(paths[0])

    def _on_double_clicked(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            self.sig_navigate_to.emit(path)
        elif os.path.isfile(path):
            self.sig_file_double_clicked.emit(path)

    def _on_clicked(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isfile(path):
            self.sig_file_selected.emit(path)

    # ---------- 展开/收缩 ----------
    def expand_all(self):
        root_index = self.tree_view.rootIndex()
        if root_index.isValid():
            self._expand_recursive(root_index)

    def _expand_recursive(self, index):
        self.tree_view.expand(index)
        for row in range(self.tree_model.rowCount(index)):
            child = self.tree_model.index(row, 0, index)
            if self.tree_model.hasChildren(child):
                self._expand_recursive(child)

    def collapse_all(self):
        root_index = self.tree_view.rootIndex()
        if root_index.isValid():
            self._collapse_recursive(root_index)

    def _collapse_recursive(self, index):
        for row in range(self.tree_model.rowCount(index)):
            child = self.tree_model.index(row, 0, index)
            if self.tree_model.hasChildren(child):
                self._collapse_recursive(child)
        if index != self.tree_view.rootIndex():
            self.tree_view.collapse(index)

    # ---------- 更新 ----------
    def update_path(self, path):
        if os.path.isdir(path):
            index = self.tree_model.index(path)
            self.tree_view.setRootIndex(index)
            self.tree_view.setCurrentIndex(index)

    def update_clipboard_status(self, has_content):
        self._clipboard_has_content = has_content

    def get_selected_paths(self):
        paths = []
        for idx in self.tree_view.selectionModel().selectedIndexes():
            if idx.column() == 0:
                path = self.tree_model.filePath(idx)
                if os.path.exists(path):
                    paths.append(path)
        return paths

    # ---------- 右键菜单 ----------
    def _show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        selected_paths = self.get_selected_paths()

        if not selected_paths:
            menu = QMenu(self)
            menu.addAction(QAction("◉ 新建文件夹", self, triggered=lambda: self.sig_folder_create.emit("")))
            menu.addAction(QAction("◎ 新建文件", self, triggered=lambda: self.sig_file_create.emit("")))
            action_paste = QAction("↙ 粘贴", self)
            action_paste.setEnabled(self._clipboard_has_content)
            action_paste.triggered.connect(self.sig_paste.emit)
            menu.addAction(action_paste)
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
            return

        menu = QMenu(self)

        # 新建
        menu.addAction(QAction("◉ 新建文件夹", self, triggered=lambda: self.sig_folder_create.emit("")))
        menu.addAction(QAction("◎ 新建文件", self, triggered=lambda: self.sig_file_create.emit("")))
        menu.addSeparator()

        # 复制路径（单文件）
        if len(selected_paths) == 1:
            menu.addAction(QAction("📋 复制路径", self, triggered=lambda: self._copy_path(selected_paths[0])))
        menu.addSeparator()

        # 复制/剪切/粘贴
        count = len(selected_paths)
        menu.addAction(QAction(f"⊕ 复制 {count} 个项目", self, triggered=lambda: self.sig_copy.emit(selected_paths)))
        menu.addAction(QAction(f"⊖ 剪切 {count} 个项目", self, triggered=lambda: self.sig_cut.emit(selected_paths)))
        action_paste = QAction("↙ 粘贴", self)
        action_paste.setEnabled(self._clipboard_has_content)
        action_paste.triggered.connect(self.sig_paste.emit)
        menu.addAction(action_paste)
        menu.addSeparator()

        # 重命名（单文件）
        if len(selected_paths) == 1:
            menu.addAction(QAction("✎ 重命名", self, triggered=lambda: self._show_rename_dialog(selected_paths[0])))
        else:
            action_rename = QAction("✎ 重命名", self)
            action_rename.setEnabled(False)
            menu.addAction(action_rename)

        # 删除
        menu.addAction(QAction(f"✕ 删除 {count} 个项目", self, triggered=lambda: self.sig_file_delete.emit(selected_paths)))
        menu.addSeparator()

        # 属性
        if len(selected_paths) == 1:
            menu.addAction(QAction("ℹ 属性", self, triggered=lambda: self.sig_show_properties.emit(selected_paths[0])))

        menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def _copy_path(self, path):
        QApplication.clipboard().setText(path)

    def _show_rename_dialog(self, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.sig_file_rename.emit(path, new_name)