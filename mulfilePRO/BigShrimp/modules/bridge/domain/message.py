# -*- coding: utf-8 -*-
"""Bridge 内层：插件消息语义。"""
from typing import Any, Dict, List


def extract_files_payload(data: Any) -> List[Dict[str, str]]:
    """从插件 JSON 提取 files 列表。"""
    if not isinstance(data, dict):
        return []
    files = data.get("files", [])
    if not isinstance(files, list):
        return []
    result = []
    for item in files:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "filename": str(item.get("filename", "unnamed.py")),
                "code": str(item.get("code", "")),
            }
        )
    return result