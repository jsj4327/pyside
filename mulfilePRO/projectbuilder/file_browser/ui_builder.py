# file_browser/ui_builder.py
"""
文件浏览器UI构建器
"""
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QLineEdit, QPushButton, QCheckBox, QLabel, 
    QTextEdit, QHeaderView, QAbstractItemView,
    QSplitter, QStyle
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont


class FileBrowserUI:
    """文件浏览器UI组件构建类"""
    
    def __init__(self, parent):
        self.parent = parent
        self._setup_ui()
    
    def _setup_ui(self):
        """构建UI界面"""
        parent = self.parent
        
        # 主布局
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # ---- 顶部工具栏 ----
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)

        self.btn_up = QPushButton()
        self.btn_up.setIcon(parent.style().standardIcon(QStyle.SP_ArrowUp))
        self.btn_up.setToolTip("上一级目录 (Backspace)")
        self.btn_up.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_up)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("输入路径并按回车跳转...")
        self.path_edit.setToolTip("输入路径后按回车键跳转")
        toolbar_layout.addWidget(self.path_edit, 1)

        self.btn_batch_copy = QPushButton("批量复制")
        self.btn_batch_copy.setToolTip("将当前文件夹路径发送到分批复制工具")
        self.btn_batch_copy.setFixedHeight(30)
        toolbar_layout.addWidget(self.btn_batch_copy)

        self.btn_code_merge = QPushButton("代码合并")
        self.btn_code_merge.setToolTip("将当前文件夹路径发送到代码合并工具")
        self.btn_code_merge.setFixedHeight(30)
        toolbar_layout.addWidget(self.btn_code_merge)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(parent.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("刷新 (F5)")
        self.btn_refresh.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_refresh)

        self.btn_open_dir = QPushButton()
        self.btn_open_dir.setIcon(parent.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.btn_open_dir.setToolTip("在系统文件管理器中打开当前目录")
        self.btn_open_dir.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_open_dir)

        self.btn_generate_from_text = QPushButton()
        self.btn_generate_from_text.setIcon(parent.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.btn_generate_from_text.setToolTip("输入树状架构文本生成项目结构")
        self.btn_generate_from_text.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_generate_from_text)

        self.btn_export_tree = QPushButton()
        self.btn_export_tree.setIcon(parent.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_export_tree.setToolTip("导出并预览当前目录树结构")
        self.btn_export_tree.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_export_tree)

        self.btn_count_lines = QPushButton("📊")
        self.btn_count_lines.setToolTip("统计文件代码行数")
        self.btn_count_lines.setCheckable(True)
        self.btn_count_lines.setChecked(True)
        self.btn_count_lines.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_count_lines)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("🚫 排除: *.py, test, temp...")
        self.filter_edit.setToolTip("输入要排除的关键词/扩展名，用逗号或空格分隔")
        self.filter_edit.setFixedWidth(220)
        toolbar_layout.addWidget(self.filter_edit)

        self.btn_hidden = QPushButton("👁")
        self.btn_hidden.setToolTip("显示/隐藏文件")
        self.btn_hidden.setCheckable(True)
        self.btn_hidden.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_hidden)

        self.chk_auto_expand = QCheckBox("自动展开")
        self.chk_auto_expand.setChecked(True)
        self.chk_auto_expand.setToolTip("加载后自动展开所有文件夹")
        toolbar_layout.addWidget(self.chk_auto_expand)

        main_layout.addWidget(toolbar)

        # ---- 运行按钮 + 状态标签行 ----
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(5, 0, 5, 0)
        status_layout.setSpacing(5)

        self.btn_run = QPushButton()
        self.btn_run.setIcon(parent.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_run.setToolTip("运行当前项目（检测 main.py）")
        self.btn_run.setFixedSize(30, 30)
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; border: none; border-radius: 4px;")
        status_layout.addWidget(self.btn_run)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 2px 5px;")
        status_layout.addWidget(self.status_label, 1)

        main_layout.addLayout(status_layout)

        # ---- 主体：水平分割（左侧文件树 + 右侧输出） ----
        splitter = QSplitter(Qt.Horizontal)

        # 左侧文件树
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "行数", "大小", "修改时间"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setIndentation(20)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)

        font = QFont("Consolas", 10)
        self.tree.setFont(font)

        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)

        splitter.addWidget(self.tree)

        # 右侧输出控件
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(2)

        # 输出标题和清空按钮
        output_header = QHBoxLayout()
        output_header.addWidget(QLabel("📟 程序输出"))
        output_header.addStretch()
        self.btn_clear_output = QPushButton("清空")
        self.btn_clear_output.setFixedSize(60, 25)
        output_header.addWidget(self.btn_clear_output)
        output_layout.addLayout(output_header)

        # 输出文本框（类似终端）
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #444;")
        self.output_text.setPlaceholderText("程序输出将显示在这里...")
        output_layout.addWidget(self.output_text)

        splitter.addWidget(output_widget)

        # 设置初始比例：树占65%，输出占35%
        splitter.setSizes([650, 350])

        main_layout.addWidget(splitter, 1)