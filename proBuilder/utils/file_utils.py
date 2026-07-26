#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

class FileUtils:
    """文件与目录工具类"""

    @staticmethod
    def read_file_safely(file_path: str, encoding: str = 'utf-8') -> str:
        """安全读取文件内容"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            return f.read()

    @staticmethod
    def write_file_safely(file_path: str, content: str, encoding: str = 'utf-8'):
        """安全写入文件内容（自动创建父目录）"""
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def remove_path(path: str):
        """安全删除文件或目录"""
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)