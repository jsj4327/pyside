# -*- coding: utf-8 -*-
"""
核心UI组件模块：
- FileColorDelegate: 自定义 Delegate，用于根据文件大小渲染绿/红背景色
- ProjectPickerWidget: 项目选择器 Widget
- ProjectContentWidget: 项目内容浏览器及架构文本生成器 Widget
"""
from __future__ import annotations

import os
import shutil
from typing import List, Optional

from PySide2.QtCore import QDir, QModelIndex, QMimeData, QUrl, Qt, Signal
from PySide2.QtGui import QBrush, QColor, QDesktopServices, QFont
from PySide2.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class FileColorDelegate(QStyledItemDelegate):
    """自定义绘制 Delegate，支持按文件是否为空标记背景色（空文件绿，非空文件红）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.check_enabled = False

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        if not self.check_enabled or not index.isValid():
            return

        model = index.model()
        if isinstance(model, QFileSystemModel):
            file_path = model.filePath(index)
            if os.path.isfile(file_path):
                try:
                    size = os.path.getsize(file_path)
                    if size == 0:
                        option.backgroundBrush = QBrush(QColor("#e8f5e9"))
                    else:
                        option.backgroundBrush = QBrush(QColor("#ffebee"))
                except OSError:
                    pass


class ProjectPickerWidget(QWidget):
    """左侧：选项目目录组件"""

    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        self.btn_up = QPushButton("上一级")
        self.btn_up.setFixedHeight(28)
        self.path_edit = QLineEdit()
        self.path_edit.setClearButtonEnabled(True)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setFixedHeight(28)
        bar.addWidget(self.btn_up)
        bar.addWidget(self.path_edit, 1)
        bar.addWidget(self.btn_refresh)
        layout.addLayout(bar)

        self.btn_use = QPushButton("将当前文件夹设为项目 →")
        self.btn_use.setFixedHeight(32)
        self.btn_use.setStyleSheet("font-weight:bold; background:#2196F3; color:white;")
        layout.addWidget(self.btn_use)

        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        for c in range(1, 4):
            self.tree.setColumnHidden(c, True)
        layout.addWidget(self.tree, 1)

        self.btn_up.clicked.connect(self._go_up)
        self.btn_refresh.clicked.connect(self._refresh)
        self.path_edit.returnPressed.connect(self._on_enter)
        self.btn_use.clicked.connect(self._emit_project)
        self.tree.doubleClicked.connect(self._on_double)

        self.set_path(os.getcwd())

    def set_path(self, path: str) -> bool:
        path = os.path.abspath(os.path.expanduser(path.strip())) if hasattr(os, "expanduser") else os.path.abspath(path.strip())
        if not os.path.isdir(path):
            QMessageBox.warning(self, "路径无效", f"不是有效目录：\n{path}")
            self.path_edit.setText(self._path)
            return False
        idx = self.model.setRootPath(path)
        if not idx.isValid():
            idx = self.model.index(path)
        self.tree.setRootIndex(idx)
        self._path = path
        self.path_edit.setText(path)
        parent = os.path.dirname(path.rstrip(os.sep))
        self.btn_up.setEnabled(bool(parent) and parent != path)
        return True

    def _on_enter(self) -> None:
        self.set_path(self.path_edit.text())

    def _go_up(self) -> None:
        parent = os.path.dirname(self._path.rstrip(os.sep))
        if parent and parent != self._path:
            self.set_path(parent)

    def _refresh(self) -> None:
        self.set_path(self._path)

    def _on_double(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        path = self.model.filePath(index)
        if self.model.isDir(index):
            self.set_path(path)

    def _emit_project(self) -> None:
        indexes = self.tree.selectionModel().selectedRows(0)
        if indexes:
            path = self.model.filePath(indexes[0])
            if os.path.isdir(path):
                self.project_selected.emit(path)
                return
        if self._path:
            self.project_selected.emit(self._path)


class ProjectContentWidget(QWidget):
    """项目内容浏览器组件"""

    path_changed = Signal(str)
    file_activated = Signal(str)
    request_batch_copy = Signal(str)  # 发送请求将目标路径传送至分批复制界面

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_path = ""
        self._clipboard_mime: Optional[QMimeData] = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.btn_up = QPushButton("上一级")
        self.btn_up.setFixedHeight(28)
        self.btn_up.setEnabled(False)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("当前路径，回车跳转…")
        self.path_edit.setClearButtonEnabled(True)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setFixedHeight(28)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("过滤 如 *.py;*.json;*.txt")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setFixedWidth(200)

        bar.addWidget(self.btn_up)
        bar.addWidget(self.path_edit, stretch=1)
        bar.addWidget(self.btn_refresh)
        bar.addWidget(QLabel("过滤:"))
        bar.addWidget(self.filter_edit)
        main_layout.addLayout(bar)

        self.splitter = QSplitter(Qt.Horizontal)

        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.model.setNameFilterDisables(False)
        self.model.directoryLoaded.connect(self._on_directory_loaded)

        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setAnimated(False)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.setColumnWidth(0, 280)

        self.delegate = FileColorDelegate(self.tree)
        self.tree.setItemDelegate(self.delegate)

        self.splitter.addWidget(self.tree)

        self.text_view = QPlainTextEdit(self)
        self.text_view.setReadOnly(True)
        self.text_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.text_view.setFont(font)
        self.text_view.setPlaceholderText("项目的架构树图与所有文件绝对路径将在此处生成…")
        self.text_view.hide()

        self.splitter.addWidget(self.text_view)
        main_layout.addWidget(self.splitter, stretch=1)

        bot_bar = QHBoxLayout()
        self.btn_check_empty = QPushButton("🔍 检测空白文件并标记颜色")
        self.btn_check_empty.setFixedHeight(30)

        self.btn_show_architecture = QPushButton("📋 生成/显示项目架构文本")
        self.btn_show_architecture.setFixedHeight(30)

        bot_bar.addWidget(self.btn_check_empty)
        bot_bar.addWidget(self.btn_show_architecture)
        main_layout.addLayout(bot_bar)

        self.empty_hint = QLabel("请在「项目选择」选项卡中选择一个项目文件夹")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color:#888; padding:24px;")
        main_layout.addWidget(self.empty_hint)

        self.splitter.hide()

    def _connect_signals(self) -> None:
        self.btn_up.clicked.connect(self._go_up)
        self.btn_refresh.clicked.connect(self.refresh)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.filter_edit.returnPressed.connect(self._on_filter_changed)
        self.tree.doubleClicked.connect(self._on_double_clicked)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.btn_check_empty.clicked.connect(self._check_empty_files)
        self.btn_show_architecture.clicked.connect(self._on_show_architecture_clicked)

    def set_root_path(self, path: str, silent: bool = False) -> bool:
        if not path:
            if not silent:
                QMessageBox.warning(self, "路径无效", "路径不能为空。")
            return False

        path = os.path.abspath(os.path.expanduser(str(path).strip()))
        if not os.path.isdir(path) or not os.access(path, os.R_OK):
            if not silent:
                QMessageBox.warning(self, "路径无效", f"不是可读目录：\n{path}")
            self.path_edit.setText(self._current_path)
            return False

        root = self.model.setRootPath(path)
        if not root.isValid():
            root = self.model.index(path)
        if not root.isValid():
            if not silent:
                QMessageBox.warning(self, "路径无效", f"无法打开：\n{path}")
            self.path_edit.setText(self._current_path)
            return False

        self.tree.setRootIndex(root)
        self._current_path = path
        self.path_edit.setText(path)
        self._update_up_button()
        self.empty_hint.hide()
        self.splitter.show()
        self.text_view.hide()
        self.tree.expandAll()

        self.path_changed.emit(path)
        return True

    def _on_directory_loaded(self, path: str) -> None:
        self.tree.expandAll()

    def refresh(self) -> None:
        if not self._current_path:
            return
        self.set_root_path(self._current_path, silent=True)

    def _on_show_architecture_clicked(self) -> None:
        if not self._current_path:
            return
        self._update_architecture_text()
        self.text_view.show()
        self.splitter.setSizes([500, 400])

    def _update_architecture_text(self) -> None:
        if not self._current_path or not os.path.isdir(self._current_path):
            self.text_view.clear()
            return

        lines = [f"项目根目录: {self._current_path}\n", "=" * 60, "【目录结构树】"]

        def _build_tree(dir_path: str, prefix: str = ""):
            try:
                entries = sorted(os.listdir(dir_path))
            except OSError:
                return
            entries = [e for e in entries if not e.startswith(".")]
            count = len(entries)
            for idx, name in enumerate(entries):
                is_last = idx == count - 1
                connector = "└── " if is_last else "├── "
                full_path = os.path.join(dir_path, name)
                lines.append(f"{prefix}{connector}{name}")
                if os.path.isdir(full_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _build_tree(full_path, new_prefix)

        _build_tree(self._current_path)

        lines.append("\n" + "=" * 60)
        lines.append("【所有文件绝对路径列表】")

        for root_dir, _, files in os.walk(self._current_path):
            for file in sorted(files):
                lines.append(os.path.join(root_dir, file))

        self.text_view.setPlainText("\n".join(lines))

    def _check_empty_files(self) -> None:
        self.delegate.check_enabled = True
        self.tree.viewport().update()
        QMessageBox.information(
            self,
            "检测完成",
            "已开启文件检测标记：\n- 淡绿背景：0 字节空白文件\n- 淡红背景：非空文件",
        )

    def selected_paths(self) -> List[str]:
        indexes = self.tree.selectionModel().selectedRows(0)
        return [self.model.filePath(i) for i in indexes if i.isValid()]

    def _on_context_menu(self, pos) -> None:
        index = self.tree.indexAt(pos)
        menu = QMenu(self)

        act_open = menu.addAction("在系统文件管理器中打开")
        act_copy_path = menu.addAction("复制绝对路径文本")
        menu.addSeparator()

        act_copy_item = menu.addAction("复制")
        act_copy_all_files = menu.addAction("复制其下所有文件")
        act_copy_non_empty = menu.addAction("复制所有非空文件")
        act_batch_copy = menu.addAction("⚡ 发送到分批复制选项卡")  # 新右键项

        paths = self.selected_paths()
        if index.isValid() and index.column() != 0:
            index = index.sibling(index.row(), 0)
        if index.isValid() and self.model.filePath(index) not in paths:
            paths = [self.model.filePath(index)]

        has_folder = any(os.path.isdir(p) for p in paths)

        act_open.setEnabled(bool(paths) or bool(self._current_path))
        act_copy_path.setEnabled(bool(paths))
        act_copy_item.setEnabled(bool(paths))
        act_copy_all_files.setEnabled(has_folder)
        act_copy_non_empty.setEnabled(bool(paths))
        act_batch_copy.setEnabled(bool(paths))

        action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
        if action is None:
            return

        if action == act_open:
            self._open_in_file_manager(paths)
        elif action == act_copy_path:
            self._copy_paths_text(paths)
        elif action == act_copy_item:
            self._copy_items_to_clipboard(paths)
        elif action == act_copy_all_files:
            self._copy_all_files_to_clipboard(paths)
        elif action == act_copy_non_empty:
            self._copy_non_empty_files(paths)
        elif action == act_batch_copy:
            target_path = paths[0] if paths else self._current_path
            if os.path.isfile(target_path):
                target_path = os.path.dirname(target_path)
            self.request_batch_copy.emit(target_path)

    def _copy_non_empty_files(self, paths: List[str]) -> None:
        non_empty_paths = []
        for p in paths:
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                non_empty_paths.append(p)
            elif os.path.isdir(p):
                for root_dir, _, files in os.walk(p):
                    for file in files:
                        fp = os.path.join(root_dir, file)
                        if os.path.getsize(fp) > 0:
                            non_empty_paths.append(fp)

        if not non_empty_paths:
            QMessageBox.information(self, "提示", "未查找到任何非空文件。")
            return

        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in non_empty_paths]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)
        QMessageBox.information(self, "已复制", f"已复制 {len(non_empty_paths)} 个非空文件。")

    def _copy_items_to_clipboard(self, paths: List[str]) -> None:
        if not paths:
            return
        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)

    def _copy_all_files_to_clipboard(self, paths: List[str]) -> None:
        file_paths = []
        for p in paths:
            if os.path.isfile(p):
                file_paths.append(p)
            elif os.path.isdir(p):
                for root_dir, _, files in os.walk(p):
                    for file in files:
                        file_paths.append(os.path.join(root_dir, file))

        if not file_paths:
            QMessageBox.information(self, "提示", "没有可复制的文件。")
            return

        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)

    def _open_in_file_manager(self, paths: List[str]) -> None:
        target = paths[0] if paths else self._current_path
        if not target:
            return
        if os.path.isfile(target):
            target = os.path.dirname(target)
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    def _copy_paths_text(self, paths: List[str]) -> None:
        if not paths:
            return
        QApplication.clipboard().setText("\n".join(paths))

    def _on_path_entered(self) -> None:
        text = self.path_edit.text().strip()
        if text:
            self.set_root_path(text)

    def _on_filter_changed(self) -> None:
        raw = self.filter_edit.text().strip()
        if not raw:
            self.model.setNameFilters([])
            return
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        self.model.setNameFilters(parts)

    def _go_up(self) -> None:
        if not self._current_path:
            return
        parent = os.path.dirname(self._current_path.rstrip(os.sep))
        if parent and parent != self._current_path:
            self.set_root_path(parent, silent=True)

    def _update_up_button(self) -> None:
        if not self._current_path:
            self.btn_up.setEnabled(False)
            return
        parent = os.path.dirname(self._current_path.rstrip(os.sep))
        self.btn_up.setEnabled(bool(parent) and parent != self._current_path)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        if index.column() != 0:
            index = index.sibling(index.row(), 0)
        path = self.model.filePath(index)
        if self.model.isDir(index):
            self.set_root_path(path, silent=True)
        else:
            self.file_activated.emit(path)