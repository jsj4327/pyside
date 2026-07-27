# -*- coding: utf-8 -*-

import os  # 导入系统路径模块
from PySide2.QtWidgets import QMessageBox  # 导入消息弹窗用于错误提示
from service.analyzer_service import AnalyzerService  # 导入代码分析服务

class EditorController:
    """编辑器控制器：负责调度源码读取、大纲分析与文件保存业务"""

    def __init__(self, editor_view):
        """初始化控制器，注入对应的视图实例"""
        self.view = editor_view  # 绑定传入的源码编辑器视图
        self.analyzer = AnalyzerService()  # 实例化代码大纲分析服务
        self.current_file_path = None  # 内部状态：当前正在编辑的文件绝对路径

        self._init_connections()  # 绑定视图的信号

    def _init_connections(self):
        """绑定视图向外发出的动作请求"""
        # 监听视图的保存请求，触发保存业务逻辑
        self.view.save_requested.connect(self.handle_save_file)

    def open_file(self, file_path):
        """核心业务：加载文件源码并提取结构大纲"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            QMessageBox.warning(self.view, "错误", f"文件不存在: {file_path}")
            return

        try:
            # 尝试以 UTF-8 编码读取 Python 源码
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 更新内部状态
            self.current_file_path = file_path
            
            # 调度 View 层刷新编辑器内容
            self.view.update_editor_content(file_path, content)
            
            # 调度 Service 层解析源码，提取类和函数大纲
            symbols = self.analyzer.extract_symbols(file_path)
            
            # 调度 View 层刷新右侧大纲列表
            self.view.update_outline(symbols)

        except Exception as e:
            # 捕获异常并弹窗提示用户
            QMessageBox.critical(self.view, "读取失败", f"无法打开文件:\n{str(e)}")

    def handle_save_file(self, content):
        """核心业务：将编辑器中的文本保存回磁盘"""
        # 如果当前没有打开任何文件，则拒绝保存
        if not self.current_file_path:
            return

        try:
            # 以覆盖写入模式保存文件
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 弹窗提示保存成功
            QMessageBox.information(self.view, "成功", "文件保存成功！")
            
            # 文件发生更改，重新触发 AST 解析以刷新大纲树
            symbols = self.analyzer.extract_symbols(self.current_file_path)
            self.view.update_outline(symbols)
            
        except Exception as e:
            # 捕获权限不足或磁盘满等异常
            QMessageBox.critical(self.view, "保存失败", f"无法保存文件:\n{str(e)}")