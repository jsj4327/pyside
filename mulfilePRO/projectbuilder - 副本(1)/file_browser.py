# file_browser.py
import os
import shutil
import subprocess
import sys
from datetime import datetime

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMenu, QAction, QMessageBox, QInputDialog, QProgressDialog,
    QApplication, QFileDialog, QLabel, QComboBox, QStyle,
    QDialog, QTextEdit, QDialogButtonBox, QAbstractItemView,
    QSplitter  # 用于左右分割
)
from PySide2.QtCore import (
    Qt, QThread, Signal, QTimer, QDir, QFileInfo,
    QPropertyAnimation, QEasingCurve, QUrl
)
from PySide2.QtGui import (
    QIcon, QFont, QColor, QPalette, QDragEnterEvent,
    QDropEvent, QMouseEvent, QKeyEvent
)

from run_manager import RunManager  # 导入运行管理器


class FileSystemWorker(QThread):
    """
    后台异步扫描目录及统计行数的工作线程
    """
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, root_path, exclude_patterns=None, show_hidden=False, count_lines=True):
        super().__init__()
        self.root_path = root_path
        self.exclude_patterns = exclude_patterns or []
        self.show_hidden = show_hidden
        self.count_lines = count_lines

    def run(self):
        file_list = []
        try:
            if not os.path.exists(self.root_path):
                self.error.emit(f"路径不存在: {self.root_path}")
                return

            entries = os.listdir(self.root_path)
            total = len(entries)
            
            for index, entry in enumerate(entries):
                if not self.show_hidden and entry.startswith('.'):
                    continue

                # 检查排除模式
                excluded = False
                for pattern in self.exclude_patterns:
                    if pattern in entry or (pattern.startswith('*') and entry.endswith(pattern[1:])):
                        excluded = True
                        break
                if excluded:
                    continue

                full_path = os.path.join(self.root_path, entry)
                try:
                    is_dir = os.path.isdir(full_path)
                    size = 0
                    modified = 0
                    lines = -1

                    if os.path.exists(full_path):
                        stat = os.stat(full_path)
                        modified = stat.st_mtime
                        if not is_dir:
                            size = stat.st_size
                            if self.count_lines and size < 2 * 1024 * 1024:
                                lines = self._count_file_lines(full_path)

                    file_info = {
                        'name': entry,
                        'path': full_path,
                        'is_dir': is_dir,
                        'size': size,
                        'modified': modified,
                        'lines': lines
                    }
                    file_list.append(file_info)

                except Exception:
                    continue

                if total > 0:
                    self.progress.emit(int((index + 1) / total * 100))

            self.finished.emit(file_list)
        except Exception as e:
            self.error.emit(str(e))

    def _count_file_lines(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return -1


class FileBrowser(QWidget):
    """
    工业级文件浏览器组件
    支持树形浏览、多选、批量删除、文本架构解析生成嵌套文件/文件夹等
    """

    # 信号
    path_changed = Signal(str)
    file_selected = Signal(str)
    file_double_clicked = Signal(str)
    folder_created = Signal(str)
    batch_copy_requested = Signal(str)
    code_merge_requested = Signal(str)

    def __init__(self, root_path=None, parent=None):
        super().__init__(parent)

        self.root_path = root_path or os.path.expanduser("~")
        self.current_path = self.root_path
        self.exclude_patterns = []
        self.show_hidden = False
        self.count_lines = True
        self._loading = False
        self._worker = None
        self._drag_enabled = False

        self._setup_ui()
        self._setup_connections()

        if os.path.exists(self.root_path):
            self.load_directory(self.root_path)
        else:
            self.root_path = os.path.expanduser("~")
            if os.path.exists(self.root_path):
                self.load_directory(self.root_path)

    # ==========================================
    # UI 构建
    # ==========================================
    def _setup_ui(self):
        """构建UI布局，左侧文件树，右侧输出控件"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # ---- 顶部工具栏 ----
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)

        self.btn_up = QPushButton()
        self.btn_up.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
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
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("刷新 (F5)")
        self.btn_refresh.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_refresh)

        self.btn_open_dir = QPushButton()
        self.btn_open_dir.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.btn_open_dir.setToolTip("在系统文件管理器中打开当前目录 (Ctrl+O)")
        self.btn_open_dir.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_open_dir)

        self.btn_generate_from_text = QPushButton()
        self.btn_generate_from_text.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.btn_generate_from_text.setToolTip("输入树状架构文本生成项目结构")
        self.btn_generate_from_text.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_generate_from_text)

        self.btn_export_tree = QPushButton()
        self.btn_export_tree.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_export_tree.setToolTip("导出并预览当前目录树结构")
        self.btn_export_tree.setFixedSize(30, 30)
        toolbar_layout.addWidget(self.btn_export_tree)

        self.btn_count_lines = QPushButton("📊")
        self.btn_count_lines.setToolTip("统计文件代码行数")
        self.btn_count_lines.setCheckable(True)
        self.btn_count_lines.setChecked(self.count_lines)
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

        main_layout.addWidget(toolbar)

        # ---- 运行按钮 + 状态标签行 ----
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(5, 0, 5, 0)
        status_layout.setSpacing(5)

        self.btn_run = QPushButton()
        self.btn_run.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
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
        self.tree.setDragDropMode(QTreeWidget.InternalMove)

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

    def _setup_connections(self):
        self.btn_up.clicked.connect(self._go_up)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_open_dir.clicked.connect(self._open_current_directory)
        self.btn_generate_from_text.clicked.connect(self._show_text_architecture_dialog)
        self.btn_export_tree.clicked.connect(self._export_directory_tree)
        self.btn_count_lines.toggled.connect(self._on_count_lines_toggled)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.btn_hidden.toggled.connect(self._on_hidden_toggled)

        self.btn_batch_copy.clicked.connect(
            lambda: self.batch_copy_requested.emit(self.current_path)
        )
        self.btn_code_merge.clicked.connect(
            lambda: self.code_merge_requested.emit(self.current_path)
        )

        # 运行按钮
        self.btn_run.clicked.connect(self._on_run_clicked)

        # 清空输出
        self.btn_clear_output.clicked.connect(self.output_text.clear)

        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.installEventFilter(self)

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

    # ---------- 运行按钮核心逻辑 ----------
    def _on_run_clicked(self):
        """运行当前目录下的 main.py，输出显示在右侧"""
        path = self.current_path
        if not os.path.isdir(path):
            self.status_label.setText("❌ 当前路径无效")
            return

        # 清空输出并显示提示
        self.output_text.clear()
        self.output_text.append(f"🚀 正在运行项目: {path}")
        self.output_text.append("-" * 60)

        # 查找 main.py
        main_file = RunManager.find_main_py(path)
        if main_file is None:
            msg = "❌ 未找到 main.py（忽略大小写）"
            self.output_text.append(msg)
            self.status_label.setText(msg)
            return

        self.output_text.append(f"📄 入口文件: {main_file}")
        self.output_text.append("⏳ 运行中...\n")

        # 运行并捕获输出
        success, stdout, stderr = RunManager.run_python_file(main_file, capture_output=True)

        # 显示输出
        if stdout:
            self.output_text.append("【标准输出】")
            self.output_text.append(stdout)
        if stderr:
            self.output_text.append("【错误输出】")
            self.output_text.append(stderr)

        if success:
            self.output_text.append("\n✅ 运行完成 (退出码 0)")
            self.status_label.setText("✅ 运行成功")
        else:
            self.output_text.append("\n❌ 运行失败")
            self.status_label.setText("❌ 运行失败")

        # 滚动到底部
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )

    # ==========================================
    # 其他原有方法（保持不变）
    # ==========================================
    def set_root_path(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            self.root_path = path
            self.load_directory(path)
            return True
        return False

    def load_directory(self, path):
        if self._loading:
            return

        if not os.path.exists(path) or not os.path.isdir(path):
            self.status_label.setText(f"❌ 路径无效: {path}")
            return

        self.current_path = os.path.abspath(path)
        self.path_edit.setText(self.current_path)
        self.status_label.setText(f"⏳ 加载中: {self.current_path}")

        self.tree.clear()

        self._loading = True
        self._worker = FileSystemWorker(
            self.current_path,
            self.exclude_patterns,
            self.show_hidden,
            self.count_lines
        )
        self._worker.finished.connect(self._on_load_finished)
        self._worker.error.connect(self._on_load_error)
        self._worker.progress.connect(self._on_load_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

        self.path_changed.emit(self.current_path)

    def refresh(self):
        if self.current_path:
            self.load_directory(self.current_path)

    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path and os.path.exists(parent):
            self.load_directory(parent)

    def _open_current_directory(self):
        self._open_in_file_manager(self.current_path)

    def _show_text_architecture_dialog(self):
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.warning(self, "错误", "当前路径无效！")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("根据树状文本架构生成文件和文件夹")
        dialog.resize(650, 500)

        layout = QVBoxLayout(dialog)
        tip_label = QLabel("请在下方粘贴您的树状目录结构文本（支持顶级根目录、缩进层级、│ 及 # 注释）：")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Consolas", 10))
        text_edit.setPlaceholderText(
            "例如：\n"
            "ProjectBuilder/\n"
            "│\n"
            "├── app.py                            # 程序入口\n"
            "├── main_window.py                    # 主窗口\n"
            "└── file_manager.py                   # 文件管理器"
        )
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("开始生成")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        def parse_and_create():
            raw_text = text_edit.toPlainText()
            if not raw_text.strip():
                QMessageBox.warning(dialog, "提示", "请输入有效的架构文本！")
                return

            lines = raw_text.splitlines()
            stack = []

            try:
                for line in lines:
                    stripped_full = line.strip()
                    if not stripped_full or stripped_full in ['│', '|']:
                        continue

                    line_without_comment = line.split('#')[0]
                    if not line_without_comment.strip():
                        continue

                    indent_level = 0
                    for char in line:
                        if char in [' ', '\t', '│', '├', '└', '─']:
                            indent_level += 1
                        else:
                            break

                    cleaned = line_without_comment.strip()
                    for prefix in ['├──', '└──', '│', '|', '─']:
                        cleaned = cleaned.replace(prefix, '')
                    cleaned = cleaned.strip()

                    if not cleaned:
                        continue

                    is_dir = cleaned.endswith('/') or ('.' not in cleaned and not cleaned.startswith('.'))
                    if cleaned.endswith('/'):
                        cleaned = cleaned.rstrip('/')

                    if not cleaned:
                        continue

                    while stack and stack[-1][0] >= indent_level:
                        stack.pop()

                    parent_dir = stack[-1][1] if stack else self.current_path
                    current_path = os.path.join(parent_dir, cleaned)

                    if is_dir:
                        os.makedirs(current_path, exist_ok=True)
                        stack.append((indent_level, current_path))
                    else:
                        dir_name = os.path.dirname(current_path)
                        if dir_name and not os.path.exists(dir_name):
                            os.makedirs(dir_name, exist_ok=True)
                        if not os.path.exists(current_path):
                            with open(current_path, 'w', encoding='utf-8') as f:
                                f.write("")

                self.refresh()
                QMessageBox.information(dialog, "成功", "已成功生成嵌套文件与目录！")
                self.status_label.setText("📁 架构解析与生成成功")
                dialog.accept()

            except Exception as e:
                QMessageBox.warning(dialog, "错误", f"解析或生成文件时出错:\n{str(e)}")

        button_box.accepted.connect(parse_and_create)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(button_box)
        dialog.exec_()

    def _export_directory_tree(self):
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.warning(self, "错误", "当前路径无效！")
            return

        def generate_tree(dir_path, prefix=""):
            tree_str = ""
            try:
                entries = sorted(os.listdir(dir_path))
                if not self.show_hidden:
                    entries = [e for e in entries if not e.startswith('.')]

                filtered_entries = []
                for entry in entries:
                    excluded = False
                    for pattern in self.exclude_patterns:
                        if pattern in entry or (pattern.startswith('*') and entry.endswith(pattern[1:])):
                            excluded = True
                            break
                    if not excluded:
                        filtered_entries.append(entry)
                entries = filtered_entries

                count = len(entries)
                for i, entry in enumerate(entries):
                    connector = "└── " if i == count - 1 else "├── "
                    path = os.path.join(dir_path, entry)
                    is_dir = os.path.isdir(path)
                    display_name = entry + "/" if is_dir else entry
                    tree_str += f"{prefix}{connector}{display_name}\n"
                    
                    if is_dir:
                        extension = "    " if i == count - 1 else "│   "
                        tree_str += generate_tree(path, prefix + extension)
            except Exception:
                pass
            return tree_str

        root_name = os.path.basename(self.current_path) or self.current_path
        result_text = f"项目路径: {self.current_path}\n\n{root_name}/\n" + generate_tree(self.current_path)

        dialog = QDialog(self)
        dialog.setWindowTitle("导出目录结构")
        dialog.resize(650, 500)
        
        dialog_layout = QVBoxLayout(dialog)
        tip_label = QLabel("您可以直接在此对话框中查看、全选、复制生成的项目目录树结构：")
        dialog_layout.addWidget(tip_label)
        
        text_edit = QTextEdit()
        text_edit.setFont(QFont("Consolas", 10))
        text_edit.setText(result_text)
        dialog_layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn = button_box.button(QDialogButtonBox.Ok)
        ok_btn.setText("关闭")
        
        btn_copy_all = button_box.addButton("复制全部", QDialogButtonBox.ActionRole)
        def handle_copy():
            text_edit.selectAll()
            text_edit.copy()
            self.status_label.setText("📋 目录树结构已成功复制到剪贴板！")
            QMessageBox.information(dialog, "成功", "已成功将目录结构复制到剪贴板！")
        btn_copy_all.clicked.connect(handle_copy)
        button_box.accepted.connect(dialog.accept)
        
        dialog_layout.addWidget(button_box)
        dialog.exec_()

    def _on_path_entered(self):
        path = self.path_edit.text().strip()
        if path:
            if path.startswith('~'):
                path = os.path.expanduser(path)

            if os.path.exists(path) and os.path.isdir(path):
                self.load_directory(path)
            else:
                self.path_edit.setText(self.current_path)
                QMessageBox.warning(self, "路径无效", f"路径不存在或不是目录:\n{path}")

    def _on_filter_changed(self, text):
        text = text.strip()
        if text:
            patterns = []
            for sep in ['，', ',', ' ']:
                text = text.replace(sep, ',')
            for p in text.split(','):
                p = p.strip()
                if p:
                    patterns.append(p)
            self.exclude_patterns = patterns
            self.status_label.setText(f"🚫 排除: {', '.join(patterns)}")
        else:
            self.exclude_patterns = []
            self.status_label.setText("✅ 显示所有文件")

        if self.current_path:
            self.load_directory(self.current_path)

    def _on_hidden_toggled(self, checked):
        self.show_hidden = checked
        self.refresh()

    def _on_count_lines_toggled(self, checked):
        self.count_lines = checked
        self.refresh()

    def _on_load_finished(self, file_list):
        self.tree.clear()
        if not file_list:
            self.status_label.setText("📭 目录为空")
            return

        for file_info in file_list:
            item = QTreeWidgetItem()
            item.setText(0, file_info['name'])

            if file_info['is_dir']:
                item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                item.setData(0, Qt.UserRole, "dir")
                item.setText(1, "-")
                item.setText(2, "-")
            else:
                item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
                item.setData(0, Qt.UserRole, "file")

                lines = file_info.get('lines', -1)
                if lines >= 0:
                    item.setText(1, f"{lines:,}")
                else:
                    item.setText(1, "-")

                size = file_info['size']
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                item.setText(2, size_str)

            mtime = datetime.fromtimestamp(file_info['modified'])
            item.setText(3, mtime.strftime("%Y-%m-%d %H:%M:%S"))
            item.setData(0, Qt.UserRole + 1, file_info['path'])

            self.tree.addTopLevelItem(item)

        self.tree.expandAll()
        self.status_label.setText(f"✅ 加载完成: {len(file_list)} 个项目")
        self._loading = False

    def _on_load_error(self, error_msg):
        self.status_label.setText(f"❌ 错误: {error_msg}")
        self._loading = False

    def _on_load_progress(self, progress):
        self.status_label.setText(f"⏳ 加载中: {progress}%")

    def _on_worker_finished(self):
        self._loading = False
        self._worker = None

    def _on_item_double_clicked(self, item, column):
        path = item.data(0, Qt.UserRole + 1)
        if not path:
            return
        if os.path.isdir(path):
            self.load_directory(path)
        else:
            self.file_double_clicked.emit(path)

    def _on_item_clicked(self, item, column):
        path = item.data(0, Qt.UserRole + 1)
        if path:
            self.file_selected.emit(path)

    def _show_context_menu(self, position):
        selected_items = self.tree.selectedItems()
        item_at_pos = self.tree.itemAt(position)
        
        if item_at_pos:
            if item_at_pos not in selected_items:
                self.tree.clearSelection()
                item_at_pos.setSelected(True)
                selected_items = [item_at_pos]
        else:
            self.tree.clearSelection()
            selected_items = []

        target_path = item_at_pos.data(0, Qt.UserRole + 1) if item_at_pos else self.current_path
        is_dir = os.path.isdir(target_path) if target_path else True
        
        menu = QMenu(self)

        if item_at_pos:
            action_open = QAction("📂 在文件管理器中打开", self)
            action_open.triggered.connect(lambda: self._open_in_file_manager(target_path))
            menu.addAction(action_open)

            action_copy = QAction("📋 复制绝对路径", self)
            action_copy.triggered.connect(lambda: self._copy_path(target_path))
            menu.addAction(action_copy)
            menu.addSeparator()

        parent_dir = target_path if (is_dir and target_path) else os.path.dirname(target_path or self.current_path)

        action_new_folder = QAction("📁 新建文件夹...", self)
        action_new_folder.triggered.connect(lambda: self._create_folder(parent_dir))
        menu.addAction(action_new_folder)

        action_new_file = QAction("📄 新建文件...", self)
        action_new_file.triggered.connect(lambda: self._create_file(parent_dir))
        menu.addAction(action_new_file)

        if selected_items:
            menu.addSeparator()
            count = len(selected_items)
            
            if count > 1:
                action_delete = QAction(f"🗑 删除选中的 {count} 个项目", self)
            else:
                name = os.path.basename(selected_items[0].data(0, Qt.UserRole + 1))
                action_delete = QAction(f"🗑 删除 '{name}'", self)
            
            action_delete.triggered.connect(self._delete_selected_items)
            menu.addAction(action_delete)

            if count == 1:
                action_rename = QAction("✏️ 重命名", self)
                action_rename.triggered.connect(lambda: self._rename_item(selected_items[0], target_path))
                menu.addAction(action_rename)

                menu.addSeparator()
                action_props = QAction("ℹ️ 属性", self)
                action_props.triggered.connect(lambda: self._show_properties(target_path))
                menu.addAction(action_props)

        global_pos = self.tree.viewport().mapToGlobal(position)
        menu.exec_(global_pos)

    def _open_in_file_manager(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件管理器:\n{str(e)}")

    def _copy_path(self, path):
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        self.status_label.setText(f"📋 已复制: {path}")

    def _create_folder(self, parent_path):
        name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if ok and name:
            name = name.strip().replace('\\', '/')
            new_path = os.path.join(parent_path, name)
            try:
                os.makedirs(new_path, exist_ok=True)
                self.folder_created.emit(new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件夹失败:\n{str(e)}")

    def _create_file(self, parent_path):
        name, ok = QInputDialog.getText(self, "新建文件", "请输入文件名:")
        if ok and name:
            name = name.strip().replace('\\', '/')
            new_path = os.path.join(parent_path, name)
            dir_name = os.path.dirname(new_path)
            try:
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建文件失败:\n{str(e)}")

    def _delete_selected_items(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        paths_to_delete = []
        for item in selected_items:
            p = item.data(0, Qt.UserRole + 1)
            if p and os.path.exists(p):
                paths_to_delete.append(p)

        if not paths_to_delete:
            return

        if len(paths_to_delete) == 1:
            name = os.path.basename(paths_to_delete[0])
            msg = f"确定要删除 '{name}' 吗？"
        else:
            msg = f"确定要删除选中的 {len(paths_to_delete)} 个项目吗？"

        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success_count = 0
            for path in paths_to_delete:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    success_count += 1
                except Exception as e:
                    print(f"删除失败 {path}: {e}")

            self.refresh()
            self.status_label.setText(f"🗑 成功删除了 {success_count} 个项目")

    def _rename_item(self, item, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "重命名", "请输入新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try:
                os.rename(path, new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败:\n{str(e)}")

    def _show_properties(self, path):
        info = QFileInfo(path)
        is_dir = info.isDir()
        size = info.size() if info.isFile() else 0
        msg = f"<b>路径:</b> {path}<br><b>类型:</b> {'文件夹' if is_dir else '文件'}<br><b>大小:</b> {size} B"
        QMessageBox.information(self, "属性", msg)

    def set_drag_enabled(self, enabled):
        self._drag_enabled = enabled
        self.tree.setDragEnabled(enabled)
        self.tree.setAcceptDrops(enabled)

    def dragEnterEvent(self, event):
        if self._drag_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._drag_enabled:
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    path = os.path.dirname(path)
                if os.path.isdir(path):
                    self.load_directory(path)
                    break
        event.acceptProposedAction()

    def get_selected_path(self):
        current = self.tree.currentItem()
        return current.data(0, Qt.UserRole + 1) if current else None

    def get_current_path(self):
        return self.current_path