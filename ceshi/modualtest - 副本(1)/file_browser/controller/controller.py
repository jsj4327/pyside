# -*- coding:utf-8 -*-
import os
import shutil
from PySide2.QtWidgets import QMessageBox, QInputDialog
from PySide2.QtCore import QObject

from ..common.utils import format_size


class FileBrowserController(QObject):
    """文件浏览器控制器"""

    def __init__(self, model, view, parent=None):
        super().__init__(parent)
        self.model = model
        self.view = view
        self._connect_signals()
        self._initialize_view()

    def _connect_signals(self):
        # View → Controller
        self.view.sig_navigate_up.connect(self._on_navigate_up)
        self.view.sig_navigate_back.connect(self._on_navigate_back)
        self.view.sig_navigate_forward.connect(self._on_navigate_forward)
        self.view.sig_navigate_home.connect(self._on_navigate_home)
        self.view.sig_navigate_to.connect(self._on_navigate_to)
        self.view.sig_refresh.connect(self._on_refresh)
        self.view.sig_file_double_clicked.connect(self._on_file_open)
        self.view.sig_file_delete.connect(self._on_file_delete)
        self.view.sig_file_rename.connect(self._on_file_rename)
        self.view.sig_folder_create.connect(self._on_folder_create)
        self.view.sig_file_create.connect(self._on_file_create)
        self.view.sig_copy.connect(self._on_copy)
        self.view.sig_cut.connect(self._on_cut)
        self.view.sig_paste.connect(self._on_paste)
        self.view.sig_show_properties.connect(self._on_show_properties)
        self.view.sig_open_in_file_manager.connect(self._on_open_in_file_manager)

        # Model → Controller
        self.model.sig_directory_changed.connect(self._on_directory_changed)
        self.model.sig_error.connect(self._on_error)
        self.model.sig_clipboard_changed.connect(self.view.update_clipboard_status)

    def _initialize_view(self):
        self._on_directory_changed(self.model.current_path)
        self.view.update_clipboard_status(self.model.has_clipboard_content())

    # ---------- 导航 ----------
    def _on_navigate_up(self):
        self.model.go_up()

    def _on_navigate_back(self):
        self.model.go_back()

    def _on_navigate_forward(self):
        self.model.go_forward()

    def _on_navigate_home(self):
        self.model.go_home()

    def _on_navigate_to(self, path):
        self.model.set_current_path(path)

    def _on_refresh(self):
        self._refresh_view()

    def _on_file_open(self, path):
        """文件打开（由外部处理）"""
        pass

    # ---------- 批量删除（含详细确认对话框） ----------
    def _on_file_delete(self, paths):
        """批量删除文件/文件夹，显示完整路径"""
        if isinstance(paths, str):
            paths = [paths]
        if not paths:
            self.view.update_status("没有可删除的项目")
            return

        # 过滤有效路径
        valid_paths = [p for p in paths if os.path.exists(p)]
        if not valid_paths:
            self.view.update_status("没有可删除的项目（文件不存在）")
            return

        # ---- 构建详细的确认对话框 ----
        if len(valid_paths) == 1:
            path = valid_paths[0]
            name = os.path.basename(path)
            is_dir = os.path.isdir(path)
            type_text = "文件夹" if is_dir else "文件"
            
            msg = f"确定要删除此 {type_text} 吗？\n"
            msg += f"\n名称: {name}"
            msg += f"\n路径: {path}"
            msg += f"\n\n此操作不可恢复！"
        else:
            # 多个项目
            dir_count = sum(1 for p in valid_paths if os.path.isdir(p))
            file_count = len(valid_paths) - dir_count
            
            msg = f"确定要删除以下 {len(valid_paths)} 个项目吗？\n"
            msg += f"\n  文件夹: {dir_count} 个"
            msg += f"\n  文件: {file_count} 个"
            msg += f"\n\n【详细列表】"
            
            for p in valid_paths[:10]:  # 最多显示10个
                name = os.path.basename(p)
                is_dir = os.path.isdir(p)
                type_label = "[文件夹]" if is_dir else "[文件]"
                msg += f"\n  {type_label} {name}"
                msg += f"\n      {p}"
            
            if len(valid_paths) > 10:
                msg += f"\n  ... 等共 {len(valid_paths)} 个项目"
            
            msg += f"\n\n此操作不可恢复！"

        reply = QMessageBox.question(
            self.view, 
            "确认删除", 
            msg,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            self.view.update_status("已取消删除")
            return

        # 执行删除
        success = 0
        failed = []
        for path in valid_paths:
            if self.model.delete_file(path):
                success += 1
            else:
                failed.append(path)

        self._refresh_view()
        
        # 显示删除结果
        if failed:
            self.view.update_status(f"已删除 {success} 个项目，{len(failed)} 个失败")
            fail_msg = "以下项目删除失败：\n"
            for f in failed[:5]:
                fail_msg += f"\n  {f}"
            if len(failed) > 5:
                fail_msg += f"\n  ... 等共 {len(failed)} 个"
            QMessageBox.warning(self.view, "删除部分失败", fail_msg)
        else:
            self.view.update_status(f"已删除 {success} 个项目")
            QMessageBox.information(self.view, "删除完成", f"成功删除 {success} 个项目")

    # ---------- 重命名 ----------
    def _on_file_rename(self, old_path, new_name):
        if self.model.rename_file(old_path, new_name):
            self._refresh_view()
            self.view.update_status(f"已重命名: {os.path.basename(old_path)} → {new_name}")

    # ---------- 新建 ----------
    def _on_folder_create(self, name):
        if not name:
            name, ok = QInputDialog.getText(self.view, "新建文件夹", "名称:")
            if not ok or not name:
                return
        if self.model.create_folder(name):
            self._refresh_view()
            self.view.update_status(f"已创建文件夹: {name}")

    def _on_file_create(self, name):
        if not name:
            name, ok = QInputDialog.getText(self.view, "新建文件", "名称:")
            if not ok or not name:
                return
        if self.model.create_file(name):
            self._refresh_view()
            self.view.update_status(f"已创建文件: {name}")

    # ---------- 剪贴板 ----------
    def _on_copy(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        valid_paths = [p for p in paths if os.path.exists(p)]
        if valid_paths:
            self.model.set_clipboard(valid_paths, 'copy')
            self.view.update_status(f"已复制 {len(valid_paths)} 个项目")

    def _on_cut(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        valid_paths = [p for p in paths if os.path.exists(p)]
        if valid_paths:
            self.model.set_clipboard(valid_paths, 'cut')
            self.view.update_status(f"已剪切 {len(valid_paths)} 个项目")

    def _on_paste(self):
        paths, operation = self.model.get_clipboard()
        if not paths:
            self.view.update_status("剪贴板为空")
            return

        dest = self.model.current_path
        success_count = 0
        failed = []

        # 构建确认消息
        if len(paths) == 1:
            name = os.path.basename(paths[0])
            msg = f"确定要将 '{name}' 粘贴到以下目录吗？\n\n目标: {dest}"
        else:
            names = '\n  '.join(os.path.basename(p) for p in paths[:5])
            if len(paths) > 5:
                names += f"\n  ... 等共 {len(paths)} 个项目"
            msg = f"确定要将以下 {len(paths)} 个项目粘贴到目标目录吗？\n\n目标: {dest}\n\n文件:\n  {names}"

        reply = QMessageBox.question(self.view, "确认粘贴", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            self.view.update_status("已取消粘贴")
            return

        # 执行粘贴
        for src in paths:
            if not os.path.exists(src):
                failed.append(f"{os.path.basename(src)}: 源文件不存在")
                continue

            base = os.path.basename(src)
            dst = os.path.join(dest, base)
            # 处理重名
            counter = 1
            name, ext = os.path.splitext(base)
            while os.path.exists(dst):
                dst = os.path.join(dest, f"{name}_{counter}{ext}")
                counter += 1
            try:
                if operation == 'cut':
                    shutil.move(src, dst)
                else:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                success_count += 1
            except Exception as e:
                failed.append(f"{os.path.basename(src)}: {str(e)}")

        # 只有剪切操作后才清空剪贴板
        if operation == 'cut':
            self.model.clear_clipboard()
        else:
            # 复制操作保留剪贴板内容，确保状态正确
            self.model.sig_clipboard_changed.emit(True)

        self._refresh_view()
        if failed:
            self.view.update_status(f"粘贴完成: {success_count} 个成功，{len(failed)} 个失败")
            QMessageBox.warning(self.view, "粘贴部分失败", "\n".join(failed[:5]))
        else:
            self.view.update_status(f"粘贴完成: {success_count} 个项目")

    # ---------- 属性 ----------
    def _on_show_properties(self, path):
        """显示文件/文件夹属性"""
        if isinstance(path, list):
            if not path:
                return
            if len(path) > 1:
                self._show_multi_properties(path)
                return
            path = path[0]

        if not os.path.exists(path):
            QMessageBox.warning(self.view, "错误", f"文件不存在: {path}")
            return

        if os.path.isdir(path):
            size = self.model.get_dir_size(path)
            info = f"路径: {path}\n类型: 文件夹\n大小: {format_size(size)}"
        else:
            info = f"路径: {path}\n类型: 文件\n大小: {format_size(os.path.getsize(path))}"
        QMessageBox.information(self.view, "属性", info)

    def _show_multi_properties(self, paths):
        """显示多个文件的属性摘要"""
        total_size = 0
        file_count = 0
        dir_count = 0
        exist_count = 0
        for p in paths:
            if not os.path.exists(p):
                continue
            exist_count += 1
            if os.path.isdir(p):
                dir_count += 1
                total_size += self.model.get_dir_size(p)
            else:
                file_count += 1
                total_size += os.path.getsize(p)

        if exist_count == 0:
            QMessageBox.warning(self.view, "错误", "所有项目都不存在")
            return

        info = f"选中 {exist_count} 个项目 (共 {len(paths)} 个)\n"
        info += f"  文件夹: {dir_count} 个\n"
        info += f"  文件: {file_count} 个\n"
        info += f"  总大小: {format_size(total_size)}"
        QMessageBox.information(self.view, "属性 (多个项目)", info)

    # ---------- 在文件管理器中打开 ----------
    def _on_open_in_file_manager(self, path):
        import subprocess
        import sys
        try:
            if not os.path.exists(path):
                QMessageBox.warning(self.view, "错误", f"路径不存在: {path}")
                return
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            QMessageBox.warning(self.view, "错误", str(e))

    # ---------- Model 事件 ----------
    def _on_directory_changed(self, path):
        self._refresh_view()
        self.view.update_nav_buttons(self.model.can_go_back, self.model.can_go_forward)

    def _on_error(self, message):
        QMessageBox.warning(self.view, "错误", message)

    # ---------- 辅助方法 ----------
    def _refresh_view(self):
        path = self.model.current_path
        self.view.update_path(path)
        dirs = files = 0
        try:
            if os.path.exists(path):
                for item in os.listdir(path):
                    if os.path.isdir(os.path.join(path, item)):
                        dirs += 1
                    else:
                        files += 1
        except Exception:
            pass
        self.view.update_file_count(dirs, files)
        self.view.update_status(f"当前目录: {path}")