# -*- coding:utf-8 -*-
import os
import shutil
import subprocess
import sys
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView,
    QFileSystemModel, QHeaderView, QPushButton,
    QLineEdit, QLabel, QMenu, QAction, QMessageBox,
    QInputDialog
)
from PySide2.QtCore import Qt, QDir, Signal


class FileManagerWidget(QWidget):
    """文件管理器 - 支持丰富文件操作"""
    
    file_selected = Signal(str)
    directory_changed = Signal(str)
    file_deleted = Signal(str)
    file_renamed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dir = QDir.homePath()
        self.clipboard_data = None
        self.clipboard_operation = None
        self.history = []
        self.history_index = -1
        self._init_ui()
        self._bind_signals()
        self.set_root_path(QDir.homePath())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        self.btn_up = QPushButton("⬆")
        self.btn_up.setToolTip("上级目录")
        self.btn_up.setFixedWidth(35)
        
        self.btn_back = QPushButton("↩")
        self.btn_back.setToolTip("后退")
        self.btn_back.setFixedWidth(35)
        self.btn_back.setEnabled(False)
        
        self.btn_forward = QPushButton("↪")
        self.btn_forward.setToolTip("前进")
        self.btn_forward.setFixedWidth(35)
        self.btn_forward.setEnabled(False)
        
        self.btn_home = QPushButton("🏠")
        self.btn_home.setToolTip("回到主目录")
        self.btn_home.setFixedWidth(35)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("刷新")
        self.btn_refresh.setFixedWidth(35)
        
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setStyleSheet("background:#f5f5f5;border:1px solid #ddd;border-radius:3px;padding:2px 8px;")
        
        self.btn_open = QPushButton("📂")
        self.btn_open.setToolTip("在文件管理器中打开")
        self.btn_open.setFixedWidth(35)
        
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.btn_back)
        toolbar.addWidget(self.btn_forward)
        toolbar.addWidget(self.btn_home)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.path_display, 1)
        toolbar.addWidget(self.btn_open)
        layout.addLayout(toolbar)

        # 文件树
        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(self.current_dir)
        self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setRootIndex(self.tree_model.index(self.current_dir))
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        
        layout.addWidget(self.tree_view)

        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color:#666;font-size:11px;padding:2px 4px;")
        self.file_count_label = QLabel("")
        self.file_count_label.setStyleSheet("color:#666;font-size:11px;padding:2px 4px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.file_count_label)
        layout.addLayout(status_layout)

    def _bind_signals(self):
        self.btn_up.clicked.connect(self._go_up)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_home.clicked.connect(self._go_home)
        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_open.clicked.connect(self._open_in_file_manager)
        self.tree_view.doubleClicked.connect(self._on_double_click)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def set_root_path(self, path):
        if not os.path.isdir(path):
            return
        
        if not self.history or self.history[-1] != path:
            if self.history_index != -1 and self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        
        self.current_dir = path
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.path_display.setText(path)
        self._update_nav_buttons()
        self._update_file_count()
        self.directory_changed.emit(path)

    def _update_nav_buttons(self):
        self.btn_back.setEnabled(self.history_index > 0)
        self.btn_forward.setEnabled(self.history_index < len(self.history) - 1)

    def _update_file_count(self):
        try:
            items = os.listdir(self.current_dir)
            dirs = sum(1 for i in items if os.path.isdir(os.path.join(self.current_dir, i)))
            files = len(items) - dirs
            self.file_count_label.setText(f"📁 {dirs} 个目录 | 📄 {files} 个文件")
        except:
            self.file_count_label.setText("")

    def _go_up(self):
        parent = os.path.dirname(self.current_dir)
        if parent != self.current_dir and os.path.isdir(parent):
            self.set_root_path(parent)

    def _go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.set_root_path(self.history[self.history_index])

    def _go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.set_root_path(self.history[self.history_index])

    def _go_home(self):
        self.set_root_path(QDir.homePath())

    def _refresh(self):
        self.tree_model.setRootPath(self.current_dir)
        self.tree_view.setRootIndex(self.tree_model.index(self.current_dir))
        self._update_file_count()

    def _open_in_file_manager(self):
        try:
            if sys.platform == 'win32':
                os.startfile(self.current_dir)
            elif sys.platform == 'darwin':
                subprocess.run(['open', self.current_dir])
            else:
                subprocess.run(['xdg-open', self.current_dir])
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _on_double_click(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            self.set_root_path(path)
        elif os.path.isfile(path):
            self.file_selected.emit(path)

    def _on_selection_changed(self):
        count = len(self.tree_view.selectionModel().selectedRows(0))
        self.status_label.setText(f"已选中 {count} 个项目" if count > 0 else "就绪")

    def _show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        
        # 空白区域右键
        if not index.isValid():
            menu = QMenu(self)
            paste = QAction("📋 粘贴", self)
            paste.triggered.connect(self._paste)
            paste.setEnabled(self.clipboard_data is not None)
            menu.addAction(paste)
            menu.addSeparator()
            menu.addAction(QAction("📁 新建文件夹", self, triggered=self._create_new_folder))
            menu.addAction(QAction("📄 新建文件", self, triggered=self._create_new_file))
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
            return

        # 获取选中路径
        paths = []
        for idx in self.tree_view.selectionModel().selectedRows(0):
            path = self.tree_model.filePath(idx)
            if os.path.exists(path):
                paths.append(path)

        if not paths:
            return

        menu = QMenu(self)
        
        # 基本操作
        menu.addAction(QAction("📂 打开", self, triggered=lambda: self._open_selected(paths[0])))
        menu.addSeparator()
        
        # 复制粘贴操作
        menu.addAction(QAction("📋 复制", self, triggered=lambda: self._copy(paths)))
        menu.addAction(QAction("✂️ 剪切", self, triggered=lambda: self._cut(paths)))
        paste = QAction("📋 粘贴", self, triggered=self._paste)
        paste.setEnabled(self.clipboard_data is not None)
        menu.addAction(paste)
        menu.addSeparator()
        
        # 文件操作
        menu.addAction(QAction("✏️ 重命名", self, triggered=lambda: self._rename(paths[0])))
        if len(paths) == 1:
            delete_text = f"🗑 删除 '{os.path.basename(paths[0])}'"
        else:
            delete_text = f"🗑 删除选中的 {len(paths)} 个项目"
        menu.addAction(QAction(delete_text, self, triggered=lambda: self._delete(paths)))
        menu.addSeparator()
        
        # 新建
        menu.addAction(QAction("📁 新建文件夹", self, triggered=self._create_new_folder))
        menu.addAction(QAction("📄 新建文件", self, triggered=self._create_new_file))
        menu.addSeparator()
        
        # 信息
        menu.addAction(QAction("ℹ️ 属性", self, triggered=lambda: self._show_properties(paths[0])))

        menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def _open_selected(self, path):
        if os.path.isdir(path):
            self.set_root_path(path)
        else:
            self.file_selected.emit(path)

    def _copy(self, paths):
        self.clipboard_data = paths
        self.clipboard_operation = 'copy'
        self.status_label.setText(f"已复制 {len(paths)} 个项目")

    def _cut(self, paths):
        self.clipboard_data = paths
        self.clipboard_operation = 'cut'
        self.status_label.setText(f"已剪切 {len(paths)} 个项目")

    def _paste(self):
        if not self.clipboard_data:
            return
        
        dest = self.current_dir
        count = 0
        for src in self.clipboard_data:
            if not os.path.exists(src):
                continue
            base = os.path.basename(src)
            dst = os.path.join(dest, base)
            
            # 处理重名
            counter = 1
            while os.path.exists(dst):
                name, ext = os.path.splitext(base)
                dst = os.path.join(dest, f"{name}_{counter}{ext}")
                counter += 1
            
            try:
                if self.clipboard_operation == 'cut':
                    shutil.move(src, dst)
                else:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                count += 1
            except Exception as e:
                QMessageBox.warning(self, "粘贴失败", str(e))
        
        if self.clipboard_operation == 'cut':
            self.clipboard_data = None
        self._refresh()
        self.status_label.setText(f"粘贴完成: {count} 个项目")

    def _delete(self, paths):
        if len(paths) == 1:
            msg = f"确定要删除 '{os.path.basename(paths[0])}' 吗？\n此操作不可恢复！"
        else:
            msg = f"确定要删除 {len(paths)} 个项目吗？\n此操作不可恢复！"
        
        if QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.file_deleted.emit(path)
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))
        
        self._refresh()
        self.status_label.setText(f"已删除 {len(paths)} 个项目")

    def _rename(self, path):
        old = os.path.basename(path)
        new, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old)
        if not ok or not new or new == old:
            return
        
        new_path = os.path.join(os.path.dirname(path), new)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "错误", "名称已存在")
            return
        
        try:
            os.rename(path, new_path)
            self._refresh()
            self.file_renamed.emit(path, new_path)
            self.status_label.setText(f"已重命名: {new}")
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def _create_new_folder(self):
        name, ok = QInputDialog.getText(self, "新建文件夹", "名称:")
        if ok and name:
            try:
                os.makedirs(os.path.join(self.current_dir, name))
                self._refresh()
                self.status_label.setText(f"已创建文件夹: {name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def _create_new_file(self):
        name, ok = QInputDialog.getText(self, "新建文件", "名称:")
        if ok and name:
            try:
                with open(os.path.join(self.current_dir, name), 'w', encoding='utf-8') as f:
                    f.write("")
                self._refresh()
                self.status_label.setText(f"已创建文件: {name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def _show_properties(self, path):
        if os.path.isdir(path):
            size = self._get_dir_size(path)
            info = f"路径: {path}\n类型: 文件夹\n大小: {self._format_size(size)}"
        else:
            info = f"路径: {path}\n类型: 文件\n大小: {self._format_size(os.path.getsize(path))}"
        QMessageBox.information(self, "属性", info)

    def _get_dir_size(self, path):
        total = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except:
                    pass
        return total

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_current_path(self):
        return self.current_dir

    def get_selected_files(self):
        files = []
        for idx in self.tree_view.selectionModel().selectedRows(0):
            path = self.tree_model.filePath(idx)
            if os.path.isfile(path):
                files.append(path)
        return files