"""
搜索过滤与分页计算服务
纯函数设计，不依赖任何 UI 组件，便于单元测试。
"""
from typing import List, Dict, Any, Tuple

from config import ALL_CATEGORY_KEY


def filter_prompts(
    prompts: List[Dict[str, Any]],
    category: str,
    keyword: str
) -> List[Dict[str, Any]]:
    """
    根据分类和关键字过滤 Prompt 列表。

    Args:
        prompts: 全量 Prompt 列表
        category: 选中的分类，ALL_CATEGORY_KEY 表示不限
        keyword: 搜索关键字（不区分大小写）

    Returns:
        List[dict]: 过滤后的 Prompt 列表
    """
    result = []
    kw = keyword.lower().strip()

    for p in prompts:
        # 分类过滤
        if category != ALL_CATEGORY_KEY and p.get("category") != category:
            continue

        # 关键字过滤
        if kw:
            searchable = (
                f"{p.get('title', '')} "
                f"{p.get('tags', '')} "
                f"{p.get('prompt', '')} "
                f"{p.get('notes', '')}"
            ).lower()
            if kw not in searchable:
                continue

        result.append(p)

    return result


def paginate(
    items: List[Any],
    page: int,
    page_size: int
) -> Tuple[List[Any], int, int]:
    """
    对列表进行分页切片。

    Args:
        items: 完整数据列表
        page: 当前页码（从1开始）
        page_size: 每页条数

    Returns:
        Tuple: (当前页数据, 总页数, 校正后的当前页码)
    """
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current = max(1, min(page, total_pages))

    start = (current - 1) * page_size
    end = min(start + page_size, total)

    return items[start:end], total_pages, current


def count_by_category(
    prompts: List[Dict[str, Any]],
    category: str
) -> int:
    """
    统计指定分类下的 Prompt 数量。

    Args:
        prompts: 全量 Prompt 列表
        category: 分类名称

    Returns:
        int: 匹配数量
    """
    return sum(1 for p in prompts if p.get("category") == category)
