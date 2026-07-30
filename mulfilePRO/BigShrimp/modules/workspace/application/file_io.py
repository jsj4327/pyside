# -*- coding: utf-8 -*-
"""用例：保存插件下发文件 / 单文件写盘。"""
from typing import Dict, List, Tuple

from modules.workspace.domain.code_text import clean_raw_text
from modules.workspace.domain.path_rules import resolve_under_root, sanitize_relative_path
from modules.workspace.infrastructure import local_fs


def save_files_batch(
    save_dir: str, files: List[Dict[str, str]]
) -> List[Tuple[str, bool, str]]:
    results = []
    for item in files:
        raw_name = item.get("filename", "unnamed.py")
        raw_code = item.get("code", "")
        rel = sanitize_relative_path(raw_name)
        abs_path, safe = resolve_under_root(save_dir, rel)
        if not safe:
            results.append((rel, False, "路径越界，已拒绝写入"))
            continue
        try:
            final_code = clean_raw_text(raw_code)
            local_fs.write_text_file(abs_path, final_code)
            results.append((rel, True, final_code))
        except Exception as e:
            results.append((rel, False, str(e)))
    return results


def save_single_file(save_dir: str, relative_path: str, content: str) -> Tuple[bool, str]:
    abs_path, safe = resolve_under_root(save_dir, relative_path)
    if not safe:
        return False, "路径越界，已拒绝写入"
    try:
        local_fs.write_text_file(abs_path, content)
        return True, abs_path
    except Exception as e:
        return False, str(e)