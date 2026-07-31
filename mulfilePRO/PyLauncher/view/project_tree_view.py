import os
from PySide2.QtWidgets import QTreeView, QFileSystemModel, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from PySide2.QtCore import Signal, QDir, Qt
from PySide2.QtGui import QKeyEvent


class LineCountFileSystemModel(QFileSystemModel):
    """自定义文件系统模型：重载第二列（Column 1）用于展示代码行数"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_counts = {}

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 1:
                return "行数"
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole and index.column() == 1:
            file_path = self.filePath(index)
            if self.isDir(index):
                return ""
            if file_path in self._line_counts:
                return f"{self._line_counts[file_path]} 行"
            return ""
        return super().data(index, role)

    def scan_line_counts(self, root_path):
        """递归遍历目录并统计 .py 源码文件行数"""
        self._line_counts.clear()
        if not root_path or not os.path.exists(root_path):
            return

        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            self._line_counts[full_path] = lines
                    except Exception:
                        self._line_counts[full_path] = 0

        self.layoutChanged.emit()


class ProjectTreeView(QWidget):
    """左侧项目文件树视图"""

    file_double_clicked = Signal(str)
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tool_layout = QHBoxLayout()
        tool_layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_scan_lines = QPushButton("扫描文件行数", self)
        self.btn_scan_lines.clicked.connect(self.scan_line_counts)
        tool_layout.addWidget(self.btn_scan_lines)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        self.tree = CustomTreeView(self)
        
        self.model = LineCountFileSystemModel(self)
        self.model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        self.model.setNameFilters(["*.py"])
        self.model.setNameFilterDisables(False)

        self.tree.setModel(self.model)

        # 隐藏修改时间、类型等列（隐藏 column >= 2），保留文件名（Col 0）与行数（Col 1）
        for i in range(2, self.model.columnCount()):
            self.tree.hideColumn(i)

        self.tree.showColumn(1)
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 80)

        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        self.tree.clicked.connect(self._on_item_clicked)
        
        layout.addWidget(self.tree)

    def load_directory(self, dir_path):
        self._current_dir = dir_path
        root_index = self.model.setRootPath(dir_path)
        self.tree.setRootIndex(root_index)

    def scan_line_counts(self):
        """执行行数扫描计算"""
        if self._current_dir:
            self.model.scan_line_counts(self._current_dir)

    def _on_item_double_clicked(self, index):
        if not self.model.isDir(index):
            file_path = self.model.filePath(index)
            self.file_double_clicked.emit(file_path)

    def _on_item_clicked(self, index):
        if not self.model.isDir(index):
            file_path = self.model.filePath(index)
            self.file_selected.emit(file_path)


class CustomTreeView(QTreeView):
    """继承原生的 QTreeView，保留 Ctrl 和 Alt 的逻辑"""
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() & Qt.ControlModifier or event.modifiers() & Qt.AltModifier:
            super().keyPressEvent(event)
            return
            
        super().keyPressEvent(event)