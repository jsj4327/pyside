# -*- coding:utf-8 -*-
"""
AI Assistant 核心功能模块

包含：
- TemplateManager: 模板文件管理器
- TemplateEditorDialog: 模板编辑器对话框
"""

from .template_manager import TemplateManager
from .template_editor import TemplateEditorDialog

__all__ = ['TemplateManager', 'TemplateEditorDialog']