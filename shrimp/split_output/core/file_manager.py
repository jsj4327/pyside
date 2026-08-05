# -*- coding: utf-8 -*-
import os
import re


class FileManager:
    """文件保存/读取业务逻辑，处理路径安全校验、转义还原及缓存管理"""

    def __init__(self, save_dir):
        self.save_dir = save_dir
        self.cache = {}
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def set_save_dir(self, path):
        self.save_dir = path
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    @staticmethod
    def clean_raw_text(code_text):
        """仅做基础的转义还原，保持内容原汁原味"""
        if not code_text:
            return ""
        return (
            code_text.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )

    @staticmethod
    def sanitize_path(filename):
        norm = filename.replace("\\", "/")
        parts = [re.sub(r'[\\/*?:"<>|]', "", p).strip() for p in norm.split("/")]
        safe = os.path.join(*parts) if parts else "script.py"
        return safe or "script.py"

    def save_file(self, relative_path, content):
        file_path = os.path.join(self.save_dir, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.cache[relative_path] = content

    def get_cached(self, relative_path):
        return self.cache.get(relative_path)

    def update_cache(self, relative_path, content):
        self.cache[relative_path] = content
