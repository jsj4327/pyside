# -*- coding: utf-8 -*-
"""
主界面使用 QTabWidget 充满窗口：
- Tab 1: 项目选择 (ProjectPickerWidget)
- Tab 2: 项目内容 (ProjectContentWidget)
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Iterable, List, Optional, Set

from PySide2.QtCore import QDir, QModelIndex, QMimeData, QUrl, Qt, Signal
from PySide2.QtGui import QDesktopServices, QGuiApplication
from PySide2.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


# =====================================================================
# 右侧：项目内容浏览器
# =====================================================================
class ProjectContentWidget(QWidget):
    path_changed = Signal(str)
    file_activated = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_path = ""
        self._show_size = False
        self._show_modified = False
        self._name_filters: List[str] = []
        self._expand_all_enabled = True
        self._pending_expand: Set[str] = set()
        self._clipboard_mime: Optional[QMimeData] = None  # 保持对 QMimeData 的强引用

        self._build_ui()
        self._connect_signals()
        self.set_drag_drop_enabled(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

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
        layout.addLayout(bar)

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
        self.tree.setItemsExpandable(True)
        self.tree.setExpandsOnDoubleClick(True)
        self._apply_visible_columns()
        layout.addWidget(self.tree, stretch=1)

        self.empty_hint = QLabel("请在「项目选择」选项卡中选择一个项目文件夹")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color:#888; padding:24px;")
        layout.addWidget(self.empty_hint)

        self.tree.hide()

    def _connect_signals(self) -> None:
        self.btn_up.clicked.connect(self._go_up)
        self.btn_refresh.clicked.connect(self.refresh)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.filter_edit.returnPressed.connect(self._on_filter_changed)
        self.tree.doubleClicked.connect(self._on_double_clicked)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

    def _apply_visible_columns(self) -> None:
        self.tree.setColumnHidden(1, not self._show_size)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, not self._show_modified)

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
        self.tree.show()

        if self._expand_all_enabled:
            self._pending_expand.clear()
            self._expand_index_recursive(root)

        self.path_changed.emit(path)
        return True

    def _expand_index_recursive(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        path = self.model.filePath(index)
        self.tree.expand(index)
        if path:
            self._pending_expand.add(os.path.normpath(path))

        rows = self.model.rowCount(index)
        for row in range(rows):
            child = self.model.index(row, 0, index)
            if child.isValid() and self.model.isDir(child):
                self._expand_index_recursive(child)

    def _on_directory_loaded(self, path: str) -> None:
        if not self._expand_all_enabled or not path:
            return
        if self._current_path:
            try:
                common = os.path.commonpath(
                    [os.path.normpath(self._current_path), os.path.normpath(path)]
                )
            except ValueError:
                return
            if os.path.normpath(common) != os.path.normpath(self._current_path):
                if os.path.normpath(path) != os.path.normpath(self._current_path):
                    return

        index = self.model.index(path)
        if not index.isValid():
            return
        self.tree.expand(index)
        rows = self.model.rowCount(index)
        for row in range(rows):
            child = self.model.index(row, 0, index)
            if child.isValid() and self.model.isDir(child):
                child_path = self.model.filePath(child)
                self.tree.expand(child)
                _ = self.model.rowCount(child)
                if child_path:
                    self._pending_expand.add(os.path.normpath(child_path))

    def set_expand_all_enabled(self, enabled: bool) -> None:
        self._expand_all_enabled = enabled

    def current_path(self) -> str:
        return self._current_path

    def set_column_visibility(
        self, show_size: bool = False, show_modified: bool = False
    ) -> None:
        self._show_size = show_size
        self._show_modified = show_modified
        self._apply_visible_columns()

    def set_name_filters(self, patterns: Iterable[str]) -> None:
        self._name_filters = [p.strip() for p in patterns if p and p.strip()]
        if self._name_filters:
            self.model.setNameFilters(self._name_filters)
        else:
            self.model.setNameFilters([])

    def set_drag_drop_enabled(self, enabled: bool) -> None:
        if enabled:
            self.tree.setDragEnabled(True)
            self.tree.setAcceptDrops(True)
            self.tree.setDropIndicatorShown(True)
            self.tree.setDefaultDropAction(Qt.CopyAction)
            self.model.setReadOnly(False)
            self.tree.setDragDropMode(QAbstractItemView.DragDrop)
        else:
            self.tree.setDragEnabled(False)
            self.tree.setAcceptDrops(False)
            self.tree.setDropIndicatorShown(False)
            self.tree.setDragDropMode(QAbstractItemView.NoDragDrop)

    def refresh(self) -> None:
        if not self._current_path:
            return
        path = self._current_path
        root = self.model.setRootPath(path)
        if not root.isValid():
            root = self.model.index(path)
        if root.isValid():
            self.tree.setRootIndex(root)
            if self._expand_all_enabled:
                self._pending_expand.clear()
                self._expand_index_recursive(root)
        self.tree.sortByColumn(0, Qt.AscendingOrder)

    def selected_paths(self) -> List[str]:
        indexes = self.tree.selectionModel().selectedRows(0)
        return [self.model.filePath(i) for i in indexes if i.isValid()]

    def _on_path_entered(self) -> None:
        text = self.path_edit.text().strip()
        if not text:
            self.path_edit.setText(self._current_path)
            return
        self.set_root_path(text, silent=False)

    def _on_filter_changed(self) -> None:
        raw = self.filter_edit.text().strip()
        if not raw:
            self.set_name_filters([])
            return
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        self.set_name_filters(parts)

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

    # -----------------------------------------------------------------
    # 剪贴板复制/粘贴核心逻辑
    # -----------------------------------------------------------------
    def _check_clipboard_has_urls(self) -> bool:
        """安全地检测系统剪贴板是否有文件/URL，防止 C++ 对象已被销毁触发异常。"""
        try:
            mime = QApplication.clipboard().mimeData()
            return mime.hasUrls() if mime else False
        except RuntimeError:
            return False

    def _on_context_menu(self, pos) -> None:
        index = self.tree.indexAt(pos)
        menu = QMenu(self)

        act_open = menu.addAction("在系统文件管理器中打开")
        act_copy_path = menu.addAction("复制绝对路径文本")
        menu.addSeparator()

        act_copy_item = menu.addAction("复制")
        act_copy_all_files = menu.addAction("复制其下所有文件")
        act_paste = menu.addAction("粘贴")

        menu.addSeparator()
        act_mkdir = menu.addAction("新建文件夹")
        act_delete = menu.addAction("删除")

        paths = self.selected_paths()
        if index.isValid() and index.column() != 0:
            index = index.sibling(index.row(), 0)
        if index.isValid() and self.model.filePath(index) not in paths:
            paths = [self.model.filePath(index)]

        has_folder = any(os.path.isdir(p) for p in paths)
        has_clipboard_files = self._check_clipboard_has_urls()

        act_open.setEnabled(bool(paths) or bool(self._current_path))
        act_copy_path.setEnabled(bool(paths))
        act_copy_item.setEnabled(bool(paths))
        act_copy_all_files.setEnabled(has_folder)
        act_paste.setEnabled(has_clipboard_files and bool(self._current_path))
        act_delete.setEnabled(bool(paths))
        act_mkdir.setEnabled(bool(self._current_path))

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
        elif action == act_paste:
            target_dir = self._current_path
            if index.isValid() and self.model.isDir(index):
                target_dir = self.model.filePath(index)
            self._paste_from_clipboard(target_dir)
        elif action == act_mkdir:
            self._mkdir()
        elif action == act_delete:
            self._delete_paths(paths)

    def _copy_items_to_clipboard(self, paths: List[str]) -> None:
        """复制选中的文件或文件夹节点到系统剪贴板。"""
        if not paths:
            return
        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)

    def _copy_all_files_to_clipboard(self, paths: List[str]) -> None:
        """递归获取选中文件夹下的所有纯文件，放入剪贴板。"""
        file_paths = []
        for p in paths:
            if os.path.isfile(p):
                file_paths.append(p)
            elif os.path.isdir(p):
                for root_dir, _, files in os.walk(p):
                    for file in files:
                        file_paths.append(os.path.join(root_dir, file))

        if not file_paths:
            QMessageBox.information(self, "提示", "所选文件夹下没有可复制的文件。")
            return

        self._clipboard_mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in file_paths]
        self._clipboard_mime.setUrls(urls)
        QApplication.clipboard().setMimeData(self._clipboard_mime)

    def _paste_from_clipboard(self, target_dir: str) -> None:
        """从剪贴板粘贴文件或文件夹到指定目录。"""
        try:
            mime_data = QApplication.clipboard().mimeData()
            if not mime_data or not mime_data.hasUrls():
                return
            urls = mime_data.urls()
        except RuntimeError:
            return

        src_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]

        errors = []
        for src in src_paths:
            if not os.path.exists(src):
                continue

            base_name = os.path.basename(src.rstrip(os.sep))
            dest = os.path.join(target_dir, base_name)
            dest = self._get_unique_dest_path(dest)

            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            except Exception as e:
                errors.append(f"{src}: {e}")

        self.refresh()
        if errors:
            QMessageBox.warning(self, "部分粘贴失败", "\n".join(errors))

    @staticmethod
    def _get_unique_dest_path(dest: str) -> str:
        """防止同名覆盖，自动计算并生成形如 xxx_copy.ext 的新文件名。"""
        if not os.path.exists(dest):
            return dest
        base, ext = os.path.splitext(dest)
        count = 1
        new_dest = f"{base}_copy{ext}"
        while os.path.exists(new_dest):
            new_dest = f"{base}_copy{count}{ext}"
            count += 1
        return new_dest

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

    def _mkdir(self) -> None:
        base = self._current_path
        if not base:
            return
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        dest = os.path.join(base, name)
        try:
            os.makedirs(dest, exist_ok=False)
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "创建失败", str(e))

    def _delete_paths(self, paths: List[str]) -> None:
        if not paths:
            return
        tip = "\n".join(paths[:8])
        if len(paths) > 8:
            tip += f"\n… 共 {len(paths)} 项"
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除以下项吗？此操作不可轻易恢复。\n\n{tip}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        errors = []
        for p in paths:
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                errors.append(f"{p}: {e}")
        self.refresh()
        if errors:
            QMessageBox.warning(self, "部分删除失败", "\n".join(errors))


# =====================================================================
# 左侧：选项目目录
# =====================================================================
class ProjectPickerWidget(QWidget):
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
        self.btn_use.setStyleSheet(
            "font-weight:bold; background:#2196F3; color:white;"
        )
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
        path = os.path.abspath(os.path.expanduser(path.strip()))
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


# =====================================================================
# 主窗口（已更新为 Tab 选项卡布局）
# =====================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("项目文件浏览器")
        self._place_window()

        # 创建 QTabWidget，并将其设置为 CentralWidget 充满主界面
        self.tabs = QTabWidget(self)

        self.picker = ProjectPickerWidget()
        self.content = ProjectContentWidget()

        # 添加两个选项卡
        self.tabs.addTab(self.picker, "📁 项目选择")
        self.tabs.addTab(self.content, "📄 项目内容")

        # 将 Tab 控件直接设置为主界面的 CentralWidget，占据整个窗口区域
        self.setCentralWidget(self.tabs)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "在「项目选择」中选择文件夹，然后设定为项目"
        )

        self.picker.project_selected.connect(self._on_project_selected)
        self.content.path_changed.connect(
            lambda p: self.statusBar().showMessage(f"项目视图: {p}")
        )
        self.content.file_activated.connect(
            lambda p: self.statusBar().showMessage(f"文件: {p}")
        )

    def _place_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.resize(1200, 720)
            return
        avail = screen.availableGeometry()
        w = int(avail.width() * 0.9)
        h = int(avail.height() * 0.9)
        x = avail.x() + (avail.width() - w) // 2
        y = avail.y() + (avail.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def _on_project_selected(self, path: str) -> None:
        if self.content.set_root_path(path):
            self.statusBar().showMessage(f"已打开项目: {path}")
            # 选择项目成功后，自动切换到“项目内容”选项卡 (索引 1)
            self.tabs.setCurrentIndex(1)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()