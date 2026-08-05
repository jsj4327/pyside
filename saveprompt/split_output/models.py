"""
数据模型模块
定义 Prompt 数据结构及序列化/反序列化工具函数。
"""
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


def create_prompt(
    title: str,
    prompt: str,
    category: str = "通用工具",
    tags: str = "",
    notes: str = "",
    id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建一条新的 Prompt 数据字典。

    Args:
        title: 标题
        prompt: Prompt 正文内容
        category: 所属分类
        tags: 标签字符串（逗号分隔）
        notes: 备注说明
        id: 唯一标识，为空则自动生成

    Returns:
        dict: 完整的 Prompt 数据字典
    """
    return {
        "id": id or str(uuid.uuid4()),
        "title": title.strip(),
        "category": category.strip() or "通用工具",
        "tags": tags.strip(),
        "prompt": prompt,
        "notes": notes.strip(),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def validate_prompt(data: Dict[str, Any]) -> bool:
    """
    校验 Prompt 数据是否合法。

    Args:
        data: Prompt 数据字典

    Returns:
        bool: 合法返回 True，否则 False
    """
    if not isinstance(data, dict):
        return False
    title = data.get("title", "").strip()
    prompt = data.get("prompt", "").strip()
    return bool(title) and bool(prompt)


def prompt_from_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    从原始字典安全构造标准 Prompt 数据，缺失字段使用默认值填充。

    Args:
        raw: 原始字典数据

    Returns:
        dict: 标准化的 Prompt 数据
    """
    return {
        "id": raw.get("id", str(uuid.uuid4())),
        "title": raw.get("title", ""),
        "category": raw.get("category", "通用工具"),
        "tags": raw.get("tags", ""),
        "prompt": raw.get("prompt", ""),
        "notes": raw.get("notes", ""),
        "updated_at": raw.get("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }
