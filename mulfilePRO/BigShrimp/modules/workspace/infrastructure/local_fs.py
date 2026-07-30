# -*- coding: utf-8 -*-
"""Workspace 外层：本地文件系统。"""
import os
from typing import Optional


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def ensure_parent_dir(file_path: str) -> None:
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> None:
    ensure_parent_dir(file_path)
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)


def read_text_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    if not os.path.isfile(file_path):
        return None
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()