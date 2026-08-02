# code_diff/__init__.py
"""
代码差异比较器组件
"""

from .code_diff_widget import CodeDiff
from .diff_model import DiffModel, DiffBlock, DiffStatistics
from .diff_worker import DiffWorker
from .diff_viewer import DiffViewer, DiffHighlighter

__all__ = [
    'CodeDiff',
    'DiffModel',
    'DiffBlock',
    'DiffStatistics',
    'DiffWorker',
    'DiffViewer',
    'DiffHighlighter',
]