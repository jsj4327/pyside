# -*- coding:utf-8 -*-
"""
Debug 模块 - 独立的 Python 调试执行器

提供：
- DebugWidget: 调试入口
- PythonExecutor: Python 文件执行器
- FeedbackBuilder: 反馈信息打包器
"""

from .widget import DebugWidget
from .core.executor import PythonExecutor
from .core.feedback_builder import FeedbackBuilder

__all__ = ['DebugWidget', 'PythonExecutor', 'FeedbackBuilder']