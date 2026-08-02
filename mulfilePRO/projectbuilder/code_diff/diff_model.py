# code_diff/diff_model.py
"""
差异数据模型
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DiffBlock:
    """差异块数据"""
    type: str  # 'equal', 'insert', 'delete', 'replace'
    left_start: int
    left_count: int
    right_start: int
    right_count: int
    lines_left: List[str] = field(default_factory=list)
    lines_right: List[str] = field(default_factory=list)
    word_diff: List[List[Tuple[int, int, int, int]]] = field(default_factory=list)


@dataclass
class DiffStatistics:
    """差异统计信息"""
    total_lines_left: int = 0
    total_lines_right: int = 0
    inserted: int = 0
    deleted: int = 0
    modified: int = 0
    equal: int = 0
    similarity: float = 100.0


class DiffModel:
    """差异数据模型"""

    def __init__(self):
        self.left_label: str = ""
        self.right_label: str = ""
        self.blocks: List[DiffBlock] = []
        self.statistics: DiffStatistics = DiffStatistics()
        self.is_processed: bool = False

        # 对齐渲染数据
        self.left_lines: List[str] = []
        self.right_lines: List[str] = []
        self.left_types: List[str] = []
        self.right_types: List[str] = []

    def clear(self):
        self.blocks.clear()
        self.statistics = DiffStatistics()
        self.is_processed = False
        self.left_lines.clear()
        self.right_lines.clear()
        self.left_types.clear()
        self.right_types.clear()

    def is_empty(self) -> bool:
        return not self.is_processed or len(self.blocks) == 0

    def find_line_matches(self, left_line: str, right_lines: List[str]) -> List[int]:
        """
        查找与左侧行匹配的右侧行索引
        用于智能行匹配
        """
        matches = []
        left_normalized = left_line.strip().lower()
        for idx, right_line in enumerate(right_lines):
            if right_line.strip().lower() == left_normalized:
                matches.append(idx)
        return matches