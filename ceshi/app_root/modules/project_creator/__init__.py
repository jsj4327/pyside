# -*- coding:utf-8 -*-
from .widget import ProjectCreatorWidget

def get_project_creator_module_widget(parent=None):
    """模块工厂函数"""
    return ProjectCreatorWidget(parent)