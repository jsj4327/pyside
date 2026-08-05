# -*- coding:utf-8 -*-
import os
import shutil
from PySide2.QtWidgets import QMenu, QMessageBox, QAction
from PySide2.QtCore import Qt


class FileNavigatorMixin:
    """文件树导航和右键菜单（Mixin）"""

    # ---------- 导航 ----------
    def set_current_dir(self, path):
        if not os.path.isdir(path):
            return
        if not hasattr(self, 'history'):
            self.history = []
            self.history_index = -1
        if not self.history or self.history[-1] != path:
            if self.history_index != -1 and self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.update_back_button()

    def update_back_button(self):
        self.btn_back.setEnabled(self.history_index > 0)

    def on_up_clicked(self):
        current_path = self.tree_model.filePath(self.tree_view.rootIndex())
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and os.path.exists(parent_path):
            self.set_current_dir(parent_path)

    def on_back_clicked(self):
        if self.history_index > 0:
            self.history_index -= 1
            prev_path = self.history[self.history_index]
            self.tree_view.setRootIndex(self.tree_model.index(prev_path))
            self.update_back_button()

    # ---------- 右键删除 ----------
    def _show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        selected_indexes = self.tree_view.selectionModel().selectedRows(0)
        if not selected_indexes:
            selected_indexes = [index]

        paths = []
        model = self.tree_view.model()
        for idx in selected_indexes:
            path = model.filePath(idx)
            if os.path.exists(path):
                paths.append(path)

        if not paths:
            return

        menu = QMenu(self)
        if len(paths) == 1:
            name = os.path.basename(paths[0])
            delete_action = QAction(f"🗑 删除 '{name}'", self)
        else:
            delete_action = QAction(f"🗑 删除选中的 {len(paths)} 个项目", self)
        delete_action.triggered.connect(lambda: self._delete_paths(paths))
        menu.addAction(delete_action)

        menu.addSeparator()
        refresh_action = QAction("🔄 刷新", self)
        refresh_action.triggered.connect(lambda: self.tree_view.update())
        menu.addAction(refresh_action)

        menu.exec_(self.tree_view.viewport().mapToGlobal(position))

    def _delete_paths(self, paths):
        if not paths:
            return

        if len(paths) == 1:
            name = os.path.basename(paths[0])
            msg = f"确定要删除 '{name}' 吗？\n（此操作不可恢复！）"
        else:
            msg = f"确定要删除选中的 {len(paths)} 个项目吗？\n（此操作不可恢复！）"

        reply = QMessageBox.question(
            self, "确认删除", msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                success_count += 1
            except Exception as e:
                self.log_text.append(f"❌ 删除失败: {path} - {str(e)}")
                QMessageBox.warning(self, "删除失败", f"无法删除 {path}:\n{str(e)}")

        if success_count > 0:
            self.log_text.append(f"✅ 成功删除 {success_count} 个项目")
            self.tree_view.update()

        if self.current_file_path and self.current_file_path in paths:
            self.current_file_path = None
            self.file_content = ""
            self.file_path_edit.clear()
            self.btn_analyze.setEnabled(False)
            self.log_text.append("⚠️ 当前加载的文件已被删除，已重置状态")