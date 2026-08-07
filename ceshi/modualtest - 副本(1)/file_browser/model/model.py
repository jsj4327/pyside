# -*- coding:utf-8 -*-
import os
import shutil
from PySide2.QtCore import QObject, Signal, QDir
from PySide2.QtWidgets import QFileSystemModel
from dataclasses import dataclass
from typing import List, Optional
from ..common.utils import format_size


@dataclass
class FileInfo:
    """文件信息数据类"""
    name: str
    path: str
    is_dir: bool
    size: int = 0
    mtime: float = 0.0
    extension: str = ""

    def __post_init__(self):
        if not self.extension:
            self.extension = os.path.splitext(self.name)[1].lower()


class FileBrowserModel(QObject):
    """文件浏览器数据模型（数据+状态+操作）"""
    
    # 信号
    sig_directory_changed = Signal(str)      # 当前目录变化
    sig_file_deleted = Signal(str)           # 文件被删除
    sig_file_renamed = Signal(str, str)      # 文件重命名
    sig_error = Signal(str)                  # 操作错误
    sig_clipboard_changed = Signal(bool)     # 剪贴板内容变化 (是否有内容)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Qt 内置文件系统模型
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.homePath())
        
        # 应用状态
        self._current_path = QDir.homePath()
        self._history = []
        self._history_index = -1
        self._clipboard_paths = None
        self._clipboard_operation = None
        self._selected_paths = []
    
    # ---------- 状态访问 ----------
    @property
    def current_path(self):
        return self._current_path
    
    @property
    def history(self):
        return self._history.copy()
    
    @property
    def history_index(self):
        return self._history_index
    
    @property
    def can_go_back(self):
        return self._history_index > 0
    
    @property
    def can_go_forward(self):
        return self._history_index < len(self._history) - 1
    
    @property
    def selected_paths(self):
        return self._selected_paths.copy()
    
    def get_clipboard(self):
        return self._clipboard_paths, self._clipboard_operation
    
    def has_clipboard_content(self):
        """检查剪贴板是否有内容"""
        return self._clipboard_paths is not None and len(self._clipboard_paths) > 0
    
    def set_clipboard(self, paths, operation):
        self._clipboard_paths = paths
        self._clipboard_operation = operation
        self.sig_clipboard_changed.emit(self.has_clipboard_content())
    
    def clear_clipboard(self):
        self._clipboard_paths = None
        self._clipboard_operation = None
        self.sig_clipboard_changed.emit(False)
    
    # ---------- 导航 ----------
    def set_current_path(self, path):
        if not os.path.isdir(path):
            return False
        # 如果与当前路径相同，不操作
        if os.path.abspath(path) == os.path.abspath(self._current_path):
            return True
        
        # 更新历史
        if not self._history or self._history[-1] != path:
            # 如果在历史中间，截断
            if self._history_index != -1 and self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
            self._history.append(path)
            self._history_index = len(self._history) - 1
        
        self._current_path = path
        self.sig_directory_changed.emit(path)
        return True
    
    def go_up(self):
        parent = os.path.dirname(self._current_path)
        if parent != self._current_path and os.path.isdir(parent):
            return self.set_current_path(parent)
        return False
    
    def go_back(self):
        if self.can_go_back:
            self._history_index -= 1
            self._current_path = self._history[self._history_index]
            self.sig_directory_changed.emit(self._current_path)
            return True
        return False
    
    def go_forward(self):
        if self.can_go_forward:
            self._history_index += 1
            self._current_path = self._history[self._history_index]
            self.sig_directory_changed.emit(self._current_path)
            return True
        return False
    
    def go_home(self):
        return self.set_current_path(QDir.homePath())
    
    # ---------- 数据获取 ----------
    def list_directory(self, path=None) -> List[FileInfo]:
        """获取目录下的文件和文件夹列表"""
        if path is None:
            path = self._current_path
        if not os.path.isdir(path):
            return []
        
        items = []
        try:
            for name in os.listdir(path):
                full_path = os.path.join(path, name)
                is_dir = os.path.isdir(full_path)
                size = 0 if is_dir else os.path.getsize(full_path)
                items.append(FileInfo(
                    name=name,
                    path=full_path,
                    is_dir=is_dir,
                    size=size,
                    mtime=os.path.getmtime(full_path)
                ))
            # 排序：目录优先，然后按名称
            items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        except Exception as e:
            self.sig_error.emit(f"读取目录失败: {str(e)}")
        return items
    
    def get_file_info(self, path) -> Optional[FileInfo]:
        """获取单个文件信息"""
        if not os.path.exists(path):
            return None
        is_dir = os.path.isdir(path)
        return FileInfo(
            name=os.path.basename(path),
            path=path,
            is_dir=is_dir,
            size=0 if is_dir else os.path.getsize(path),
            mtime=os.path.getmtime(path)
        )
    
    # ---------- 文件操作 ----------
    def delete_file(self, path):
        """删除文件或文件夹，返回是否成功"""
        # 确保路径是绝对路径且规范化
        path = os.path.normpath(os.path.abspath(path))
        
        if not os.path.exists(path):
            self.sig_error.emit(f"文件不存在: {path}")
            return False
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.sig_file_deleted.emit(path)
            return True
        except Exception as e:
            self.sig_error.emit(f"删除失败: {str(e)}")
            return False
    
    def rename_file(self, old_path, new_name):
        """重命名文件或文件夹"""
        # 规范化路径
        old_path = os.path.normpath(os.path.abspath(old_path))
        
        if not os.path.exists(old_path):
            self.sig_error.emit(f"文件不存在: {old_path}")
            return False
        
        dir_path = os.path.dirname(old_path)
        new_path = os.path.join(dir_path, new_name)
        if os.path.exists(new_path):
            self.sig_error.emit("名称已存在")
            return False
        try:
            os.rename(old_path, new_path)
            self.sig_file_renamed.emit(old_path, new_path)
            return True
        except Exception as e:
            self.sig_error.emit(f"重命名失败: {str(e)}")
            return False
    
    def create_folder(self, name):
        """在当前目录创建文件夹"""
        if not name or not name.strip():
            self.sig_error.emit("名称不能为空")
            return False
        path = os.path.join(self._current_path, name.strip())
        try:
            os.makedirs(path)
            return True
        except FileExistsError:
            self.sig_error.emit(f"文件夹已存在: {name}")
            return False
        except Exception as e:
            self.sig_error.emit(f"创建文件夹失败: {str(e)}")
            return False
    
    def create_file(self, name):
        """在当前目录创建文件"""
        if not name or not name.strip():
            self.sig_error.emit("名称不能为空")
            return False
        path = os.path.join(self._current_path, name.strip())
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("")
            return True
        except Exception as e:
            self.sig_error.emit(f"创建文件失败: {str(e)}")
            return False
    
    def get_dir_size(self, path):
        """计算目录大小（包含子目录）"""
        if not os.path.exists(path):
            return 0
        if not os.path.isdir(path):
            return os.path.getsize(path)
        
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except:
                        pass
        except Exception:
            pass
        return total
    
    # ---------- 批量操作 ----------
    def delete_files(self, paths):
        """批量删除文件/文件夹，返回 (成功列表, 失败列表)"""
        success_list = []
        failed_list = []
        for path in paths:
            if self.delete_file(path):
                success_list.append(path)
            else:
                failed_list.append(path)
        return success_list, failed_list
    
    def copy_files(self, src_paths, dest_dir):
        """批量复制文件到目标目录，返回 (成功列表, 失败列表)"""
        success_list = []
        failed_list = []
        for src in src_paths:
            src = os.path.normpath(os.path.abspath(src))
            if not os.path.exists(src):
                failed_list.append(f"{src}: 不存在")
                continue
            base = os.path.basename(src)
            dst = os.path.join(dest_dir, base)
            # 处理重名
            counter = 1
            name, ext = os.path.splitext(base)
            while os.path.exists(dst):
                dst = os.path.join(dest_dir, f"{name}_{counter}{ext}")
                counter += 1
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                success_list.append(src)
            except Exception as e:
                failed_list.append(f"{base}: {str(e)}")
        return success_list, failed_list
    
    def move_files(self, src_paths, dest_dir):
        """批量移动文件到目标目录，返回 (成功列表, 失败列表)"""
        success_list = []
        failed_list = []
        for src in src_paths:
            src = os.path.normpath(os.path.abspath(src))
            if not os.path.exists(src):
                failed_list.append(f"{src}: 不存在")
                continue
            base = os.path.basename(src)
            dst = os.path.join(dest_dir, base)
            # 处理重名
            counter = 1
            name, ext = os.path.splitext(base)
            while os.path.exists(dst):
                dst = os.path.join(dest_dir, f"{name}_{counter}{ext}")
                counter += 1
            try:
                shutil.move(src, dst)
                success_list.append(src)
            except Exception as e:
                failed_list.append(f"{base}: {str(e)}")
        return success_list, failed_list