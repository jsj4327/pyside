"""
数据仓库模块
封装 JSON 文件的读写、默认数据初始化及异步加载线程。
"""
import json
import os
from typing import Dict, List, Any

from PySide2.QtCore import QThread, Signal

from config import DATA_FILE, DEFAULT_DATA, DEFAULT_CATEGORIES
from models import prompt_from_dict


class DataLoaderThread(QThread):
    """后台异步加载 JSON 数据的工作线程。"""

    loaded_signal = Signal(dict)
    error_signal = Signal(str)

    def run(self):
        try:
            data = load_data()
            self.loaded_signal.emit(data)
        except Exception as e:
            self.error_signal.emit(str(e))


def load_data() -> Dict[str, Any]:
    """
    从 JSON 文件加载数据，文件不存在时自动写入默认数据。

    Returns:
        dict: 包含 categories 和 prompts 的数据字典
    """
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA["categories"], DEFAULT_DATA["prompts"])
        return {
            "categories": list(DEFAULT_DATA["categories"]),
            "prompts": list(DEFAULT_DATA["prompts"])
        }

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        categories = raw.get("categories", list(DEFAULT_CATEGORIES))
        prompts = [prompt_from_dict(p) for p in raw.get("prompts", [])]
    elif isinstance(raw, list):
        prompts = [prompt_from_dict(p) for p in raw]
        cats = set(DEFAULT_CATEGORIES)
        for p in prompts:
            if p.get("category"):
                cats.add(p["category"])
        categories = sorted(cats)
    else:
        categories = list(DEFAULT_DATA["categories"])
        prompts = list(DEFAULT_DATA["prompts"])

    return {"categories": categories, "prompts": prompts}


def save_data(categories: List[str], prompts: List[Dict[str, Any]]) -> None:
    """
    将分类和 Prompt 数据持久化到 JSON 文件。

    Args:
        categories: 分类列表
        prompts: Prompt 数据列表

    Raises:
        IOError: 文件写入失败时抛出
    """
    data = {
        "categories": categories,
        "prompts": prompts
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
