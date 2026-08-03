# file_browser/widget.py
import os
from datetime import datetime
from PySide2.QtWidgets import (
    QWidget, QMessageBox, QTreeWidgetItem, QStyle
)
from PySide2.QtCore import Qt, Signal, QTimer
from PySide2.QtGui import QIcon, QFont

from .ui_builder import FileBrowserUI
from .operations import FileOperations
from .handlers import EventHandlers
from .utils import format_size


class FileBrowser(QWidget):
    path_changed = Signal(str)
    file_selected = Signal(str)
    file_double_clicked = Signal(str)
    folder_created = Signal(str)
    batch_copy_requested = Signal(str)
    code_merge_requested = Signal(str)

    def __init__(self, root_path=None, parent=None):
        super().__init__(parent)

        self.root_path = root_path or os.path.expanduser("~")
        self.current_path = self.root_path
        self.exclude_patterns = []
        self.show_hidden = False
        self.count_lines = True
        self.auto_expand = True
        self._loading = False
        self._drag_enabled = False

        self.ui = FileBrowserUI(self)
        self.ops = FileOperations(self)
        self.handlers = EventHandlers(self)

        self._connect_signals()

        # 加载根目录
        if os.path.exists(self.root_path):
            self.load_directory(self.root_path)
        else:
            self.root_path = os.path.expanduser("~")
            if os.path.exists(self.root_path):
                self.load_directory(self.root_path)

    def _connect_signals(self):
        ui = self.ui
        h = self.handlers

        ui.btn_up.clicked.connect(self._go_up)
        ui.path_edit.returnPressed.connect(self._on_path_entered)
        ui.btn_refresh.clicked.connect(self.refresh)
        ui.btn_open_dir.clicked.connect(self._open_current_directory)
        ui.btn_generate_from_text.clicked.connect(h.show_text_architecture_dialog)
        ui.btn_export_tree.clicked.connect(h.export_directory_tree)
        ui.btn_count_lines.toggled.connect(self._on_count_lines_toggled)
        ui.filter_edit.textChanged.connect(self._on_filter_changed)
        ui.btn_hidden.toggled.connect(self._on_hidden_toggled)
        ui.chk_auto_expand.toggled.connect(self._on_auto_expand_toggled)

        ui.btn_batch_copy.clicked.connect(
            lambda: self.batch_copy_requested.emit(self.current_path)
        )
        ui.btn_code_merge.clicked.connect(
            lambda: self.code_merge_requested.emit(self.current_path)
        )

        ui.btn_run.clicked.connect(h.on_run_clicked)
        ui.btn_clear_output.clicked.connect(ui.output_text.clear)

        # 树的事件
        ui.tree.itemDoubleClicked.connect(h.on_item_double_clicked)
        ui.tree.itemClicked.connect(h.on_item_clicked)
        ui.tree.itemExpanded.connect(self._on_item_expanded)  # 展开时加载子项
        ui.tree.installEventFilter(self)

        ui.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        ui.tree.customContextMenuRequested.connect(h.show_context_menu)

    def eventFilter(self, obj, event):
        return self.handlers.event_filter(obj, event)

    def _on_auto_expand_toggled(self, checked):
        self.auto_expand = checked

    # ---------- 核心方法 ----------
    def set_root_path(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            self.root_path = path
            self.load_directory(path)
            return True
        return False

    def load_directory(self, path):
        """加载目录并构建树（懒加载子目录）"""
        if self._loading:
            return

        if not os.path.exists(path) or not os.path.isdir(path):
            self.ui.status_label.setText(f"❌ 路径无效: {path}")
            return

        self.current_path = os.path.abspath(path)
        self.ui.path_edit.setText(self.current_path)
        self.ui.status_label.setText(f"⏳ 加载中: {self.current_path}")

        self.ui.tree.clear()
        self._build_tree_items(self.current_path, None)

        if self.auto_expand:
            # 延迟展开所有节点
            QTimer.singleShot(200, self.ui.tree.expandAll)

        self.ui.status_label.setText(f"✅ 已加载: {self.current_path}")
        self.path_changed.emit(self.current_path)

    def _build_tree_items(self, dir_path, parent_item):
        """递归构建树节点（仅加载当前层）"""
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            return

        for name in entries:
            if not self.show_hidden and name.startswith('.'):
                continue

            # 检查排除模式
            excluded = False
            for pattern in self.exclude_patterns:
                if pattern in name or (pattern.startswith('*') and name.endswith(pattern[1:])):
                    excluded = True
                    break
            if excluded:
                continue

            full_path = os.path.join(dir_path, name)
            try:
                is_dir = os.path.isdir(full_path)
                is_file = os.path.isfile(full_path)
                if not is_dir and not is_file:
                    continue

                item = QTreeWidgetItem()
                item.setText(0, name)
                item.setData(0, Qt.UserRole + 1, full_path)

                if is_dir:
                    item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                    item.setData(0, Qt.UserRole, "dir")
                    item.setText(1, "-")
                    item.setText(2, "-")
                    # 添加占位子项以实现展开箭头
                    placeholder = QTreeWidgetItem()
                    placeholder.setText(0, "加载中...")
                    placeholder.setData(0, Qt.UserRole + 1, "")
                    item.addChild(placeholder)
                else:
                    item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
                    item.setData(0, Qt.UserRole, "file")

                    # 行数统计
                    lines = -1
                    if self.count_lines:
                        try:
                            # 只统计文本文件且大小小于2MB
                            size = os.path.getsize(full_path)
                            if size < 2 * 1024 * 1024:
                                lines = self._count_file_lines(full_path)
                        except:
                            pass
                    if lines >= 0:
                        item.setText(1, f"{lines:,}")
                    else:
                        item.setText(1, "-")

                    size = os.path.getsize(full_path)
                    item.setText(2, format_size(size))

                # 修改时间
                mtime = os.path.getmtime(full_path)
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                item.setText(3, mtime_str)

                if parent_item is None:
                    self.ui.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

            except (OSError, PermissionError):
                continue

    def _on_item_expanded(self, item):
        """当树节点展开时，加载其子目录内容（懒加载）"""
        path = item.data(0, Qt.UserRole + 1)
        if not path or not os.path.isdir(path):
            return

        # 检查是否已经加载过（第一个子项是否为占位项）
        if item.childCount() > 0 and item.child(0).text(0) == "加载中...":
            # 移除占位项
            item.takeChild(0)
            # 加载真实内容
            self._build_tree_items(path, item)

    def _count_file_lines(self, file_path):
        """统计文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return -1

    def refresh(self):
        if self.current_path:
            self.load_directory(self.current_path)

    def get_current_path(self):
        return self.current_path

    def get_selected_path(self):
        current = self.ui.tree.currentItem()
        return current.data(0, Qt.UserRole + 1) if current else None

    # ---------- 内部槽函数 ----------
    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path and os.path.exists(parent):
            self.load_directory(parent)

    def _open_current_directory(self):
        self.ops.open_in_file_manager(self.current_path)

    def _on_path_entered(self):
        path = self.ui.path_edit.text().strip()
        if path:
            if path.startswith('~'):
                path = os.path.expanduser(path)
            if os.path.exists(path) and os.path.isdir(path):
                self.load_directory(path)
            else:
                self.ui.path_edit.setText(self.current_path)
                QMessageBox.warning(self, "路径无效", f"路径不存在或不是目录:\n{path}")

    def _on_filter_changed(self, text):
        # 过滤规则更新，重新加载
        text = text.strip()
        if text:
            patterns = []
            for sep in ['，', ',', ' ']:
                text = text.replace(sep, ',')
            for p in text.split(','):
                p = p.strip()
                if p:
                    patterns.append(p)
            self.exclude_patterns = patterns
            self.ui.status_label.setText(f"🚫 排除: {', '.join(patterns)}")
        else:
            self.exclude_patterns = []
            self.ui.status_label.setText("✅ 显示所有文件")

        if self.current_path:
            self.load_directory(self.current_path)

    def _on_hidden_toggled(self, checked):
        self.show_hidden = checked
        self.refresh()

    def _on_count_lines_toggled(self, checked):
        self.count_lines = checked
        self.refresh()

    def set_drag_enabled(self, enabled):
        self._drag_enabled = enabled
        self.ui.tree.setDragEnabled(enabled)
        self.ui.tree.setAcceptDrops(enabled)

    def dragEnterEvent(self, event):
        if self._drag_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._drag_enabled:
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    path = os.path.dirname(path)
                if os.path.isdir(path):
                    self.load_directory(path)
                    break
        event.acceptProposedAction()