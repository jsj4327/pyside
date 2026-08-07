# -*- coding:utf-8 -*-
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QStyle
from PySide2.QtCore import Signal

from .tree_view import TreeView
from .status_view import StatusView


class FileBrowserView(QWidget):
    """文件浏览器主视图"""

    sig_navigate_up = Signal()
    sig_navigate_back = Signal()
    sig_navigate_forward = Signal()
    sig_navigate_home = Signal()
    sig_refresh = Signal()
    sig_navigate_to = Signal(str)
    sig_file_double_clicked = Signal(str)
    sig_file_selected = Signal(str)
    sig_file_rename = Signal(str, str)
    sig_folder_create = Signal(str)
    sig_file_create = Signal(str)
    sig_copy = Signal(object)
    sig_cut = Signal(object)
    sig_paste = Signal()
    sig_show_properties = Signal(str)
    sig_open_in_file_manager = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = ""
        self._init_ui()
        self._connect_signals()

    def set_delete_callback(self, callback):
        """设置删除回调（传递给 TreeView）"""
        self.tree.set_delete_callback(callback)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setSpacing(4)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)

        self.btn_up = QPushButton("⬆")
        self.btn_up.setToolTip("上级目录")
        self.btn_up.setFixedWidth(35)

        self.btn_back = QPushButton("↩")
        self.btn_back.setToolTip("后退")
        self.btn_back.setFixedWidth(35)
        self.btn_back.setEnabled(False)

        self.btn_forward = QPushButton("↪")
        self.btn_forward.setToolTip("前进")
        self.btn_forward.setFixedWidth(35)
        self.btn_forward.setEnabled(False)

        self.btn_home = QPushButton("🏠")
        self.btn_home.setToolTip("主目录")
        self.btn_home.setFixedWidth(35)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setToolTip("刷新")
        self.btn_refresh.setFixedWidth(35)
        refresh_icon = self.style().standardIcon(QStyle.SP_BrowserReload)
        self.btn_refresh.setIcon(refresh_icon)

        self.btn_open = QPushButton()
        self.btn_open.setToolTip("在文件管理器中打开")
        self.btn_open.setFixedWidth(35)
        open_icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        self.btn_open.setIcon(open_icon)

        self.btn_expand = QPushButton("⊕")
        self.btn_expand.setToolTip("展开所有子目录")
        self.btn_expand.setFixedWidth(35)

        self.btn_collapse = QPushButton("⊖")
        self.btn_collapse.setToolTip("收缩所有子目录")
        self.btn_collapse.setFixedWidth(35)

        toolbar_layout.addWidget(self.btn_up)
        toolbar_layout.addWidget(self.btn_back)
        toolbar_layout.addWidget(self.btn_forward)
        toolbar_layout.addWidget(self.btn_home)
        toolbar_layout.addWidget(self.btn_refresh)
        toolbar_layout.addWidget(self.btn_open)
        toolbar_layout.addWidget(self.btn_expand)
        toolbar_layout.addWidget(self.btn_collapse)
        toolbar_layout.addStretch()
        layout.addWidget(toolbar)

        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(4, 0, 4, 4)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setStyleSheet("background:#f5f5f5;border:1px solid #ddd;border-radius:3px;padding:4px 8px;")
        path_layout.addWidget(self.path_display)
        layout.addWidget(path_widget)

        self.tree = TreeView()
        layout.addWidget(self.tree)

        self.status = StatusView()
        layout.addWidget(self.status)

    def _connect_signals(self):
        self.btn_up.clicked.connect(self.sig_navigate_up.emit)
        self.btn_back.clicked.connect(self.sig_navigate_back.emit)
        self.btn_forward.clicked.connect(self.sig_navigate_forward.emit)
        self.btn_home.clicked.connect(self.sig_navigate_home.emit)
        self.btn_refresh.clicked.connect(self.sig_refresh.emit)
        self.btn_open.clicked.connect(lambda: self.sig_open_in_file_manager.emit(self.current_path))
        self.btn_expand.clicked.connect(self.tree.expand_all)
        self.btn_collapse.clicked.connect(self.tree.collapse_all)

        self.tree.sig_navigate_to.connect(self.sig_navigate_to.emit)
        self.tree.sig_file_double_clicked.connect(self.sig_file_double_clicked.emit)
        self.tree.sig_file_selected.connect(self.sig_file_selected.emit)
        self.tree.sig_file_rename.connect(self.sig_file_rename.emit)
        self.tree.sig_folder_create.connect(self.sig_folder_create.emit)
        self.tree.sig_file_create.connect(self.sig_file_create.emit)
        self.tree.sig_copy.connect(self.sig_copy.emit)
        self.tree.sig_cut.connect(self.sig_cut.emit)
        self.tree.sig_paste.connect(self.sig_paste.emit)
        self.tree.sig_show_properties.connect(self.sig_show_properties.emit)

    def update_path(self, path):
        self.current_path = path
        self.path_display.setText(path)
        self.tree.update_path(path)
        self.status.update_path(path)

    def update_nav_buttons(self, can_back, can_forward):
        self.btn_back.setEnabled(can_back)
        self.btn_forward.setEnabled(can_forward)

    def update_status(self, message):
        self.status.update_status(message)

    def update_file_count(self, dirs, files):
        self.status.update_file_count(dirs, files)

    def update_clipboard_status(self, has_content):
        self.tree.update_clipboard_status(has_content)