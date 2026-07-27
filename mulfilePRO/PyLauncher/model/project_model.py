# -*- coding: utf-8 -*-

from PySide2.QtCore import QObject, Signal

class ProjectModel(QObject):
    """项目数据模型，负责存储和管理项目相关的数据状态，并通过 Qt 信号通知外部更新"""
    
    # 定义数据变更信号：当项目路径改变时发射
    project_path_changed = Signal(str)
    # 定义文件扫描完成信号：携带发现的 Python 文件列表和推荐入口列表
    project_scanned = Signal(list, list)
    # 定义当前选中运行目标改变信号
    target_changed = Signal(str)

    def __init__(self, parent=None):
        """初始化项目数据模型"""
        super().__init__(parent)
        self._current_project_dir = ""  # 当前项目根目录路径
        self._py_files = []             # 当前项目包含的所有 .py 文件列表
        self._main_candidates = []      # 自动识别出的主程序入口候选列表
        self._selected_target = ""      # 当前用户选中的运行目标文件

    @property
    def current_project_dir(self):
        """获取当前项目根目录"""
        return self._current_project_dir

    @current_project_dir.setter
    def current_project_dir(self, path):
        """设置当前项目根目录，并触发信号"""
        if self._current_project_dir != path:
            self._current_project_dir = path
            self.project_path_changed.emit(path)

    def set_scan_results(self, py_files, mains):
        """批量设置扫描结果数据"""
        self._py_files = py_files
        self._main_candidates = mains
        # 发射扫描完成信号，供 Controller 绑定刷新 View
        self.project_scanned.emit(py_files, mains)

    @property
    def selected_target(self):
        """获取当前选中的运行目标"""
        return self._selected_target

    @selected_target.setter
    def selected_target(self, target):
        """设置当前选中的运行目标"""
        if self._selected_target != target:
            self._selected_target = target
            self.target_changed.emit(target)