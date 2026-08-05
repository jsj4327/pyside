"""图片列表数据模型，管理文件路径与排序逻辑"""
import os
import re
from typing import List, Dict
from config.constants import VALID_IMAGE_EXTENSIONS


class ImageModel:
    """封装图片文件列表的状态管理"""

    def __init__(self):
        self.folder_path: str = ""
        self.file_names: List[str] = []
        self.rotation_map: Dict[str, int] = {}  # 存储每个文件的旋转角度

    def load_folder(self, folder_path: str) -> int:
        """加载文件夹中的图片文件，返回加载数量"""
        self.folder_path = folder_path
        all_files = os.listdir(folder_path)
        self.file_names = [
            f for f in all_files
            if f.lower().endswith(VALID_IMAGE_EXTENSIONS)
        ]
        self.file_names.sort(key=self.natural_sort_key)
        self.rotation_map.clear()
        return len(self.file_names)

    def get_full_path(self, filename: str) -> str:
        """获取文件的完整路径"""
        return os.path.join(self.folder_path, filename)

    def get_file_at(self, index: int) -> str:
        """按索引获取文件名"""
        if 0 <= index < len(self.file_names):
            return self.file_names[index]
        return ""

    def move_item(self, from_index: int, to_index: int):
        """将项目从 from_index 移动到 to_index"""
        if (0 <= from_index < len(self.file_names) and
                0 <= to_index < len(self.file_names)):
            item = self.file_names.pop(from_index)
            self.file_names.insert(to_index, item)

    def remove_at(self, index: int):
        """移除指定索引的文件"""
        if 0 <= index < len(self.file_names):
            filename = self.file_names.pop(index)
            if filename in self.rotation_map:
                del self.rotation_map[filename]

    def clear(self):
        """清空文件列表"""
        self.file_names.clear()
        self.folder_path = ""
        self.rotation_map.clear()

    def get_rotation(self, filename: str) -> int:
        """获取指定文件的旋转角度"""
        return self.rotation_map.get(filename, 0)

    def rotate(self, filename: str, angle: int):
        """旋转指定文件，angle应为90的倍数"""
        current = self.rotation_map.get(filename, 0)
        new_angle = (current + angle) % 360
        if new_angle == 0:
            self.rotation_map.pop(filename, None)
        else:
            self.rotation_map[filename] = new_angle

    @property
    def count(self) -> int:
        return len(self.file_names)

    @staticmethod
    def natural_sort_key(s: str):
        """自然排序键函数"""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)
        ]