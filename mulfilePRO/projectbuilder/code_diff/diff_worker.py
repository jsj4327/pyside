"""
差异计算工作线程
使用 Python 标准库的 difflib 库进行精确的行级与块级差异比较
"""

import re
import difflib
from typing import List, Tuple
from PySide2.QtCore import QThread, Signal

from .diff_model import DiffModel, DiffBlock, DiffStatistics


class DiffWorker(QThread):
    """差异计算工作线程"""

    finished = Signal(object)
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, left_content: str, right_content: str,
                 ignore_whitespace: bool = False,
                 ignore_case: bool = False,
                 ignore_blank_lines: bool = False):
        super().__init__()
        self.left_content = left_content
        self.right_content = right_content
        self.ignore_whitespace = ignore_whitespace
        self.ignore_case = ignore_case
        self.ignore_blank_lines = ignore_blank_lines
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            self.progress.emit(0)
            if not self._is_running:
                return

            self.progress.emit(20)

            left_lines = self.left_content.splitlines() if self.left_content else []
            right_lines = self.right_content.splitlines() if self.right_content else []

            model = self._compute_diff_with_dmp(left_lines, right_lines)

            self.progress.emit(100)
            self.finished.emit(model)

        except Exception as e:
            self.error.emit(str(e))

    def _compute_diff_with_dmp(self, left_lines: List[str], right_lines: List[str]) -> DiffModel:
        """
        使用 Python 标准库的 difflib.SequenceMatcher 进行精准的行级对齐与差异计算，
        彻底杜绝行索引错位和标色错乱。
        """
        # 可选的预处理（用于比对，但保留原始内容用于展示）
        comp_left = list(left_lines)
        comp_right = list(right_lines)

        if self.ignore_case:
            comp_left = [l.lower() for l in comp_left]
            comp_right = [l.lower() for l in comp_right]

        if self.ignore_whitespace:
            comp_left = [' '.join(l.split()) for l in comp_left]
            comp_right = [' '.join(l.split()) for l in comp_right]

        matcher = difflib.SequenceMatcher(None, comp_left, comp_right)
        blocks = []
        
        # 用于构建对齐视图的数据
        model = DiffModel()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            l_count = i2 - i1
            r_count = j2 - j1

            if tag == 'equal':
                block = DiffBlock(
                    type='equal',
                    left_start=i1,
                    left_count=l_count,
                    right_start=j1,
                    right_count=r_count,
                    lines_left=left_lines[i1:i2],
                    lines_right=right_lines[j1:j2],
                    word_diff=[]
                )
                blocks.append(block)
                for i in range(l_count):
                    model.left_lines.append(left_lines[i1 + i])
                    model.right_lines.append(right_lines[j1 + i])
                    model.left_types.append('equal')
                    model.right_types.append('equal')

            elif tag == 'delete':
                block = DiffBlock(
                    type='delete',
                    left_start=i1,
                    left_count=l_count,
                    right_start=j1,
                    right_count=0,
                    lines_left=left_lines[i1:i2],
                    lines_right=[],
                    word_diff=[]
                )
                blocks.append(block)
                for i in range(l_count):
                    model.left_lines.append(left_lines[i1 + i])
                    model.right_lines.append("")
                    model.left_types.append('delete')
                    model.right_types.append('padding')

            elif tag == 'insert':
                block = DiffBlock(
                    type='insert',
                    left_start=i1,
                    left_count=0,
                    right_start=j1,
                    right_count=r_count,
                    lines_left=[],
                    lines_right=right_lines[j1:j2],
                    word_diff=[]
                )
                blocks.append(block)
                for i in range(r_count):
                    model.left_lines.append("")
                    model.right_lines.append(right_lines[j1 + i])
                    model.left_types.append('padding')
                    model.right_types.append('insert')

            elif tag == 'replace':
                block = DiffBlock(
                    type='replace',
                    left_start=i1,
                    left_count=l_count,
                    right_start=j1,
                    right_count=r_count,
                    lines_left=left_lines[i1:i2],
                    lines_right=right_lines[j1:j2],
                    word_diff=[]
                )
                block.word_diff = self._compute_word_diff(block.lines_left, block.lines_right)
                blocks.append(block)

                max_count = max(l_count, r_count)
                for i in range(max_count):
                    has_left = i < l_count
                    has_right = i < r_count
                    model.left_lines.append(left_lines[i1 + i] if has_left else "")
                    model.right_lines.append(right_lines[j1 + i] if has_right else "")
                    model.left_types.append('replace' if has_left else 'padding')
                    model.right_types.append('replace' if has_right else 'padding')

        model.blocks = blocks
        model.statistics = self._calculate_statistics(blocks, left_lines, right_lines)
        model.is_processed = True

        return model

    def _compute_word_diff(self, left_lines: List[str], right_lines: List[str]) -> List[List[Tuple[int, int, int, int]]]:
        """计算词法级差异"""
        result = []

        def tokenize(text: str) -> List[str]:
            return re.findall(r'[a-zA-Z_]\w*|\d+|[^\w\s]|\s+', text)

        max_len = max(len(left_lines), len(right_lines))
        for idx in range(max_len):
            left_line = left_lines[idx] if idx < len(left_lines) else ""
            right_line = right_lines[idx] if idx < len(right_lines) else ""

            left_tokens = tokenize(left_line)
            right_tokens = tokenize(right_line)

            if not left_tokens and not right_tokens:
                result.append([])
                continue

            matcher = difflib.SequenceMatcher(None, left_tokens, right_tokens)
            changes = []

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag in ('replace', 'delete', 'insert'):
                    left_start = len(''.join(left_tokens[:i1]))
                    left_end = len(''.join(left_tokens[:i2]))
                    right_start = len(''.join(right_tokens[:j1]))
                    right_end = len(''.join(right_tokens[:j2]))
                    changes.append((left_start, left_end, right_start, right_end))

            result.append(changes)

        return result

    def _calculate_statistics(self, blocks: List[DiffBlock],
                              left_lines: List[str],
                              right_lines: List[str]) -> DiffStatistics:
        stats = DiffStatistics()
        stats.total_lines_left = len(left_lines)
        stats.total_lines_right = len(right_lines)

        for block in blocks:
            if block.type == 'insert':
                stats.inserted += block.right_count
            elif block.type == 'delete':
                stats.deleted += block.left_count
            elif block.type == 'replace':
                stats.modified += max(block.left_count, block.right_count)
            elif block.type == 'equal':
                stats.equal += block.left_count

        total = stats.total_lines_left + stats.total_lines_right
        if total > 0:
            match = stats.equal * 2
            stats.similarity = (match / total) * 100

        return stats