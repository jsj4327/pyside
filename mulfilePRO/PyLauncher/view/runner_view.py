# -*- coding: utf-8 -*-

from PySide2.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QLabel, QLineEdit, QGroupBox
from PySide2.QtCore import Signal

class RunnerView(QWidget):
    """运行控制面板视图：纯 UI 呈现，不包含任何复杂业务逻辑"""
    
    # 定义 UI 动作触发信号
    run_clicked = Signal(str, str)  # 信号参数：(目标脚本, 命令行参数)
    stop_clicked = Signal()         # 停止按钮点击信号

    def __init__(self, parent=None):
        """初始化运行控制面板 UI"""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """构建界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建运行配置分组框
        config_group = QGroupBox("运行配置面板", self)
        config_layout = QVBoxLayout(config_group)

        # 运行目标选择行布局
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("运行入口:"))
        
        # 下拉框支持用户手动输入或选择扫描出的主入口
        self.combo_target = QComboBox(self)
        self.combo_target.setEditable(True)
        target_layout.addWidget(self.combo_target)
        
        # 绿色运行按钮
        self.btn_run = QPushButton("运行", self)
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self._on_run_button_clicked)
        target_layout.addWidget(self.btn_run)

        # 红色停止按钮
        self.btn_stop = QPushButton("停止", self)
        self.btn_stop.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        target_layout.addWidget(self.btn_stop)

        config_layout.addLayout(target_layout)

        # 命令行附加参数输入行布局
        args_layout = QHBoxLayout()
        args_layout.addWidget(QLabel("命令行参数:"))
        self.input_args = QLineEdit(self)
        self.input_args.setPlaceholderText("多个参数以空格分隔，例如: --port 8080")
        args_layout.addWidget(self.input_args)
        config_layout.addLayout(args_layout)

        main_layout.addWidget(config_group)

    def _on_run_button_clicked(self):
        """内部槽函数：当点击运行按钮时收集界面数据并向外发射信号"""
        target = self.combo_target.currentText().strip()
        args = self.input_args.text().strip()
        self.run_clicked.emit(target, args)

    def set_candidates(self, candidates):
        """更新下拉框中的候选入口列表"""
        self.combo_target.clear()
        self.combo_target.addItems(candidates)

    def set_current_target(self, target):
        """设置当前选中的目标文件"""
        index = self.combo_target.findText(target)
        if index >= 0:
            self.combo_target.setCurrentIndex(index)
        else:
            self.combo_target.addItem(target)
            self.combo_target.setCurrentText(target)