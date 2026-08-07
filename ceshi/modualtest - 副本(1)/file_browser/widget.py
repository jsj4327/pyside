# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout
from PySide2.QtCore import Signal

from .model.model import FileBrowserModel
from .view.main_view import FileBrowserView
from .controller.controller import FileBrowserController


class FileBrowserWidget(QWidget):
    """文件浏览器聚合入口，对外提供简洁 API"""
    
    file_selected = Signal(str)
    directory_changed = Signal(str)
    file_deleted = Signal(str)
    file_renamed = Signal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.model = FileBrowserModel(self)
        self.view = FileBrowserView(self)
        self.controller = FileBrowserController(self.model, self.view, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.view.sig_file_double_clicked.connect(self.file_selected.emit)
        self.model.sig_directory_changed.connect(self.directory_changed.emit)
        self.model.sig_file_deleted.connect(self.file_deleted.emit)
        self.model.sig_file_renamed.connect(self.file_renamed.emit)
    
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