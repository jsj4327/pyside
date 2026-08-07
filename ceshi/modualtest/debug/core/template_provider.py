# -*- coding:utf-8 -*-
import os
from typing import Dict, Optional
from PySide2.QtCore import QObject


class TemplateProvider(QObject):
    """模板提供者 - 已废弃，现在直接从 view 加载模板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def get_all_templates(self) -> Dict[str, str]:
        """获取所有模板（空实现，实际由 view 提供）"""
        return {}
    
    def get_template(self, name: str) -> Optional[str]:
        """获取模板内容（空实现）"""
        return None
    
    def _find_template_manager(self):
        """查找 AI 模块的 TemplateManager（已废弃）"""
        return None