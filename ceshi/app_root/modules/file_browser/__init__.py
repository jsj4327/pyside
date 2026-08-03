# -*- coding:utf-8 -*-
"""文件浏览子模块统一对外接口"""
from .browser_widget import FileBrowserMainWidget


def get_file_browser_module_widget(parent=None):
    """模块工厂函数，外部仅通过该函数获取组件"""
    return FileBrowserMainWidget(parent)
