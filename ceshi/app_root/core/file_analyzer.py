# -*- coding:utf-8 -*-
from __future__ import annotations
import os
import sys
from pathlib import Path

# 自动添加项目根目录到搜索路径
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from config import TEXT_FILE_SUFFIX, CODEC_PRIORITY

class FileAnalyzer:
    """文件底层分析工具"""
    @staticmethod
    def is_text_file(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in TEXT_FILE_SUFFIX

    @staticmethod
    def read_text_file(file_path: str) -> str:
        """自动多编码兼容读取文本"""
        for codec in CODEC_PRIORITY:
            try:
                with open(file_path, "r", encoding=codec) as f:
                    return f.read()
            except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                continue
        raise UnicodeDecodeError("all_codec_failed", b"", 0, 0, "文件编码不支持")

    @staticmethod
    def stat_file_lines(file_path: str) -> tuple[int, int, int, bool]:
        if not FileAnalyzer.is_text_file(file_path):
            return 0, 0, 0, True
        try:
            content = FileAnalyzer.read_text_file(file_path)
            lines = content.splitlines()
            total = len(lines)
            empty_count = sum(1 for line in lines if line.strip() == "")
            valid_count = total - empty_count
            return total, valid_count, empty_count, False
        except Exception:
            return 0, 0, 0, True
