# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .model.model import FileBrowserModel
from .view.main_view import FileBrowserView
from .controller.controller import FileBrowserController


class FileBrowserWidget(QWidget):
    """文件浏览器聚合入口"""
    
    file_selected = Signal(str)
    directory_changed = Signal(str)
    file_deleted = Signal(str)
    file_renamed = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        print("[WIDGET-DEBUG] FileBrowserWidget 初始化开始")
        
        self.model = FileBrowserModel(self)
        self.view = FileBrowserView(self)
        
        print("[WIDGET-DEBUG] 创建 Controller")
        self.controller = FileBrowserController(self.model, self.view, self)
        
        # 设置删除回调：将 Controller 的 on_file_delete 方法绑定到 View
        self.view.set_delete_callback(self.controller.on_file_delete)  # 改为 on_file_delete
        print("[WIDGET-DEBUG] 删除回调已设置到 View")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.view.sig_file_double_clicked.connect(self.file_selected.emit)
        self.model.sig_directory_changed.connect(self.directory_changed.emit)
        self.model.sig_file_deleted.connect(self.file_deleted.emit)
        self.model.sig_file_renamed.connect(self.file_renamed.emit)
        
        print("[WIDGET-DEBUG] FileBrowserWidget 初始化完成")
    
    def set_root_path(self, path):
        self.model.set_current_path(path)
    
    def get_current_path(self):
        return self.model.current_path
    
    def get_selected_files(self):
        return self.view.tree.get_selected_paths()
    
    def refresh(self):
        self.controller._refresh_view()
    
    def go_up(self):
        self.model.go_up()
    
    def go_back(self):
        self.model.go_back()
    
    def go_forward(self):
        self.model.go_forward()
    
    def go_home(self):
        self.model.go_home()