# -*- coding:utf-8 -*-
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QSpinBox, QTextEdit, QGroupBox,
    QProgressBar, QSplitter, QTreeView, QFileSystemModel,
    QHeaderView
)
from PySide2.QtCore import Qt, QDir


def build_ui(self):
    """构建 AISplitterWidget 的 UI"""
    main_layout = QVBoxLayout(self)

    splitter = QSplitter(Qt.Horizontal)

    # ----- 左侧：文件树 -----
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.addWidget(QLabel("📁 文件浏览器"))

    # 工具栏
    toolbar = QHBoxLayout()
    self.btn_up = QPushButton("⬆ 上一层")
    self.btn_back = QPushButton("↩ 后退")
    self.btn_back.setEnabled(False)
    self.btn_open_dir = QPushButton("📂 打开")
    self.btn_open_dir.setToolTip("在文件管理器中打开当前目录")
    toolbar.addWidget(self.btn_up)
    toolbar.addWidget(self.btn_back)
    toolbar.addWidget(self.btn_open_dir)
    toolbar.addStretch()
    left_layout.addLayout(toolbar)

    # 文件树模型
    self.tree_model = QFileSystemModel()
    self.tree_model.setRootPath(QDir.homePath())
    self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

    self.tree_view = QTreeView()
    self.tree_view.setModel(self.tree_model)
    self.tree_view.setRootIndex(self.tree_model.index(QDir.homePath()))
    self.tree_view.hideColumn(1)
    self.tree_view.hideColumn(2)
    self.tree_view.hideColumn(3)
    self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
    self.tree_view.setSortingEnabled(True)
    self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
    # 启用拖拽
    self.tree_view.setDragEnabled(True)
    self.tree_view.setAcceptDrops(True)
    self.tree_view.setDragDropMode(QTreeView.DragDrop)

    left_layout.addWidget(self.tree_view)
    splitter.addWidget(left_widget)

    # ----- 右侧：功能面板 -----
    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    right_layout.setContentsMargins(5, 0, 0, 0)

    # 源文件
    file_group = QGroupBox("源文件")
    file_layout = QHBoxLayout()
    self.file_path_edit = QLineEdit()
    self.file_path_edit.setPlaceholderText("选择要拆分的文件...")
    self.btn_browse = QPushButton("浏览")
    file_layout.addWidget(self.file_path_edit, 1)
    file_layout.addWidget(self.btn_browse)
    file_group.setLayout(file_layout)
    right_layout.addWidget(file_group)

    # 目标目录
    dir_group = QGroupBox("目标目录（保存拆分结果）")
    dir_layout = QHBoxLayout()
    self.target_dir_edit = QLineEdit()
    self.target_dir_edit.setPlaceholderText("选择或输入目标目录...")
    self.btn_target_dir = QPushButton("选择目录")
    dir_layout.addWidget(self.target_dir_edit, 1)
    dir_layout.addWidget(self.btn_target_dir)
    dir_group.setLayout(dir_layout)
    right_layout.addWidget(dir_group)

    # 参数设置
    param_group = QGroupBox("参数设置")
    param_layout = QHBoxLayout()
    param_layout.addWidget(QLabel("最大Token限制:"))
    self.spin_max_tokens = QSpinBox()
    self.spin_max_tokens.setRange(1000, 100000)
    self.spin_max_tokens.setValue(8000)
    self.spin_max_tokens.setSingleStep(500)
    param_layout.addWidget(self.spin_max_tokens)
    param_layout.addStretch()
    param_group.setLayout(param_layout)
    right_layout.addWidget(param_group)

    # 操作按钮
    btn_layout = QHBoxLayout()
    self.btn_analyze = QPushButton("🚀 分析并拆分")
    self.btn_analyze.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
    self.btn_clear = QPushButton("清空结果")
    btn_layout.addWidget(self.btn_analyze)
    btn_layout.addWidget(self.btn_clear)
    right_layout.addLayout(btn_layout)

    # 进度条
    self.progress_bar = QProgressBar()
    self.progress_bar.setVisible(False)
    right_layout.addWidget(self.progress_bar)

    # 日志
    log_group = QGroupBox("日志输出")
    log_layout = QVBoxLayout()
    self.log_text = QTextEdit()
    self.log_text.setReadOnly(True)
    log_layout.addWidget(self.log_text)
    log_group.setLayout(log_layout)
    right_layout.addWidget(log_group)

    splitter.addWidget(right_widget)
    splitter.setSizes([300, 700])
    main_layout.addWidget(splitter)

    self.btn_analyze.setEnabled(False)
    self.log_text.append("就绪：选择文件并设置目标目录后点击“分析并拆分”。")