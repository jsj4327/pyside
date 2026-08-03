# file_browser/operations.py
import os
import shutil
import subprocess
import sys
from PySide2.QtWidgets import QMessageBox, QInputDialog, QApplication
from PySide2.QtCore import Qt, QFileInfo


class FileOperations:
    def __init__(self, parent):
        self.parent = parent
        self.ui = parent.ui

    def create_folder(self, parent_path):
        name, ok = QInputDialog.getText(self.parent, "新建文件夹", "请输入文件夹名称:")
        if ok and name:
            name = name.strip().replace('\\', '/')
            new_path = os.path.join(parent_path, name)
            try:
                os.makedirs(new_path, exist_ok=True)
                self.parent.folder_created.emit(new_path)
                self.parent.refresh()
            except Exception as e:
                QMessageBox.warning(self.parent, "错误", f"创建文件夹失败:\n{str(e)}")

    def create_file(self, parent_path):
        name, ok = QInputDialog.getText(self.parent, "新建文件", "请输入文件名:")
        if ok and name:
            name = name.strip().replace('\\', '/')
            new_path = os.path.join(parent_path, name)
            dir_name = os.path.dirname(new_path)
            try:
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.parent.refresh()
            except Exception as e:
                QMessageBox.warning(self.parent, "错误", f"创建文件失败:\n{str(e)}")

    def delete_selected_items(self):
        selected_items = self.ui.tree.selectedItems()
        if not selected_items:
            return

        paths_to_delete = []
        for item in selected_items:
            p = item.data(0, Qt.UserRole + 1)
            if p and os.path.exists(p):
                paths_to_delete.append(p)

        if not paths_to_delete:
            return

        if len(paths_to_delete) == 1:
            name = os.path.basename(paths_to_delete[0])
            msg = f"确定要删除 '{name}' 吗？"
        else:
            msg = f"确定要删除选中的 {len(paths_to_delete)} 个项目吗？"

        reply = QMessageBox.question(self.parent, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success_count = 0
            for path in paths_to_delete:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    success_count += 1
                except Exception as e:
                    print(f"删除失败 {path}: {e}")
            self.parent.refresh()
            self.ui.status_label.setText(f"🗑 成功删除了 {success_count} 个项目")

    def rename_item(self, item, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self.parent, "重命名", "请输入新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try:
                os.rename(path, new_path)
                self.parent.refresh()
            except Exception as e:
                QMessageBox.warning(self.parent, "错误", f"重命名失败:\n{str(e)}")

    def copy_path(self, path):
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        self.ui.status_label.setText(f"📋 已复制: {path}")

    def open_in_file_manager(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            QMessageBox.warning(self.parent, "错误", f"无法打开文件管理器:\n{str(e)}")

    def show_properties(self, path):
        info = QFileInfo(path)
        is_dir = info.isDir()
        size = info.size() if info.isFile() else 0
        msg = f"<b>路径:</b> {path}<br><b>类型:</b> {'文件夹' if is_dir else '文件'}<br><b>大小:</b> {size} B"
        QMessageBox.information(self.parent, "属性", msg)