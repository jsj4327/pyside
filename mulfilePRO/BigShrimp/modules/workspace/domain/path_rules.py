# -*- coding: utf-8 -*-
"""Workspace 内层：路径安全规则。"""
import os
import re
from typing import Tuple


def sanitize_relative_path(raw_filename: str) -> str:
    norm = (raw_filename or "unnamed.py").replace("\\", "/")
    parts = []
    for p in norm.split("/"):
        cleaned = re.sub(r'[\\/*?:"<>|]', "", p).strip()
        if cleaned in ("", ".", ".."):
            continue
        parts.append(cleaned)
    return os.path.join(*parts) if parts else "script.py"


def resolve_under_root(root_dir: str, relative_path: str) -> Tuple[str, bool]:
    root_abs = os.path.abspath(root_dir)
    target = os.path.abspath(os.path.join(root_abs, relative_path))
    try:
        common = os.path.commonpath([root_abs, target])
    except ValueError:
        return target, False
    return target, common == root_abs