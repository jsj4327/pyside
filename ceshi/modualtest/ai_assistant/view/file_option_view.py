# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QCheckBox, QLabel, QButtonGroup
)
from PySide2.QtCore import Signal, Qt


class FileOptionView(QWidget):
    """文件选项视图（3个 CheckBox）"""
    
    sig_option_changed = Signal(int)  # 0=无, 1=选中文件, 2=文件夹
    
    # 选项常量
    OPTION_NONE = 0
    OPTION_SELECTED_FILE = 1
    OPTION_FOLDER_FILES = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(16)
        
        layout.addWidget(QLabel("文件附加:"))
        layout.addSpacing(4)
        
        # 选项1：不附加文件
        self.radio_none = QCheckBox("不附加")
        self.radio_none.setChecked(True)
        layout.addWidget(self.radio_none)
        
        layout.addSpacing(8)
        
        # 选项2：附加选中文件
        self.radio_selected = QCheckBox("附加选中文件")
        self.radio_selected.setToolTip("从文件浏览器获取选中的文件")
        layout.addWidget(self.radio_selected)
        
        layout.addSpacing(8)
        
        # 选项3：附加当前文件夹文件
        self.radio_folder = QCheckBox("附加当前文件夹")
        self.radio_folder.setToolTip("从文件浏览器获取当前文件夹下所有文件")
        layout.addWidget(self.radio_folder)
        
        layout.addStretch()
        
        # 互斥分组（使用 QButtonGroup 实现互斥）
        self.option_group = QButtonGroup(self)
        self.option_group.addButton(self.radio_none, self.OPTION_NONE)
        self.option_group.addButton(self.radio_selected, self.OPTION_SELECTED_FILE)
        self.option_group.addButton(self.radio_folder, self.OPTION_FOLDER_FILES)
        self.option_group.setExclusive(True)
    
    def _connect_signals(self):
        self.radio_none.toggled.connect(lambda: self._on_option_changed(self.OPTION_NONE))
        self.radio_selected.toggled.connect(lambda: self._on_option_changed(self.OPTION_SELECTED_FILE))
        self.radio_folder.toggled.connect(lambda: self._on_option_changed(self.OPTION_FOLDER_FILES))
    
    def _on_option_changed(self, option: int):
        """选项变化"""
        # 只有被选中时才触发
        if self.get_option() == option:
            self.sig_option_changed.emit(option)
    
    def get_option(self) -> int:
        """获取当前选中的选项"""
        checked_id = self.option_group.checkedId()
        return checked_id if checked_id != -1 else self.OPTION_NONE
    
    def set_option(self, option: int):
        """设置选项"""
        if option == self.OPTION_NONE:
            self.radio_none.setChecked(True)
        elif option == self.OPTION_SELECTED_FILE:
            self.radio_selected.setChecked(True)
        elif option == self.OPTION_FOLDER_FILES:
            self.radio_folder.setChecked(True)