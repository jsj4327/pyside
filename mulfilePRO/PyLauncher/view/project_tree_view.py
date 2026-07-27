# -*- coding: utf-8 -*-

from PySide2.QtWidgets import QTreeView, QFileSystemModel, QVBoxLayout, QWidget
from PySide2.QtCore import Signal, QDir, Qt
from PySide2.QtGui import QKeyEvent

class ProjectTreeView(QWidget):
    """左侧项目文件树视图"""

    # 保留原有的双击信号
    file_double_clicked = Signal(str)
    # 【新增】单击/选中信号
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = CustomTreeView(self)
        
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        self.model.setNameFilters(["*.py"])
        self.model.setNameFilterDisables(False)

        self.tree.setModel(self.model)
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)

        # 绑定双击事件 -> 打开文件
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        # 【新增】绑定单击事件 -> 同步程序入口
        self.tree.clicked.connect(self._on_item_clicked)
        
        layout.addWidget(self.tree)

    def load_directory(self, dir_path):
        root_index = self.model.setRootPath(dir_path)
        self.tree.setRootIndex(root_index)

    def _on_item_double_clicked(self, index):
        if not self.model.isDir(index):
            file_path = self.model.filePath(index)
            self.file_double_clicked.emit(file_path)

    # 【新增】内部槽函数：处理单击选中事件
    def _on_item_clicked(self, index):
        if not self.model.isDir(index):
            file_path = self.model.filePath(index)
            self.file_selected.emit(file_path)


class CustomTreeView(QTreeView):
    """继承原生的 QTreeView，精细管控键盘事件拦截逻辑"""
    
    def keyPressEvent(self, event: QKeyEvent):
        # 必须保留 Ctrl 和 Alt 的原生响应逻辑
        if event.modifiers() & Qt.ControlModifier or event.modifiers() & Qt.AltModifier:
            super().keyPressEvent(event)
            return
            
        super().keyPressEvent(event)