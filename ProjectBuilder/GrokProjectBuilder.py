#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Builder - PySide2 大型项目辅助构建工具
- 代码预览带行号
- 项目树按钮 2x2 布局
- 扫描文件代码行数，显示在第二列
"""

import os
import re
import sys
import shutil
from datetime import datetime

from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QTreeView, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QPlainTextEdit, QPushButton, QMenu, QAction, QStatusBar,
    QFileDialog, QInputDialog, QMessageBox, QLabel, QToolBar, QDialog,
    QDialogButtonBox, QFormLayout, QFileSystemModel, QTabWidget,
    QTextBrowser, QLineEdit, QShortcut, QHeaderView, QAbstractItemView,
)
from PySide2.QtCore import (
    Qt, QDir, QProcess, QTimer, QSettings, QUrl, QRect, QSize,
    QModelIndex, QIdentityProxyModel,
)
from PySide2.QtGui import (
    QIcon, QKeySequence, QFont, QColor, QTextCursor, QSyntaxHighlighter,
    QTextCharFormat, QDesktopServices, QPainter, QTextFormat,
)


DEFAULT_ARCHITECTURE_TEXT = (
    "SimpleGitClient/\n"
    "├── main.py                  # 程序的唯一入口点\n"
    "├── requirements.txt         # 项目依赖管理\n"
    "└── core/                    # 核心逻辑层\n"
    "    └── git_manager.py       # 封装 git 操作"
)


# ===================== 行号编辑器 =====================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#888888"))
                painter.setFont(self.font())
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )
            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#FFFDE7"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra.append(selection)
        self.setExtraSelections(extra)


# ===================== 行数代理模型（第二列显示代码行数） =====================
class LineCountProxyModel(QIdentityProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_counts = {}  # abs_path -> int

    def set_line_counts(self, counts: dict):
        self._line_counts = dict(counts or {})
        # 刷新整列显示
        self.dataChanged.emit(
            self.index(0, 1),
            self.index(max(0, self.rowCount() - 1), 1),
            [Qt.DisplayRole],
        )
        # 更稳妥：全量 layout 提示
        self.layoutChanged.emit()

    def clear_line_counts(self):
        self._line_counts.clear()
        self.layoutChanged.emit()

    def columnCount(self, parent=QModelIndex()):
        # 保证至少有名称 + 行数两列
        src = self.sourceModel()
        if src is None:
            return 2
        return max(2, src.columnCount(self.mapToSource(parent)))

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "名称"
            if section == 1:
                return "行数"
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole and index.column() == 1:
            src_model = self.sourceModel()
            if src_model is None:
                return ""
            src_index = self.mapToSource(self.index(index.row(), 0, index.parent()))
            if not src_index.isValid():
                return ""
            path = src_model.filePath(src_index)
            if os.path.isdir(path):
                # 目录可显示子文件总行数（可选）；此处留空更清晰
                return ""
            if path in self._line_counts:
                return str(self._line_counts[path])
            return ""
        if index.column() == 1 and role == Qt.TextAlignmentRole:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        # 其它列走源模型；源模型列1本是 Size，被我们盖住 Display
        if index.column() >= 1 and role != Qt.DisplayRole:
            return super().data(index, role)
        if index.column() == 0:
            return super().data(index, role)
        if index.column() > 1:
            return super().data(index, role)
        return super().data(index, role)


# ===================== Python 语法高亮 =====================
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "exec", "finally",
            "for", "from", "global", "if", "import", "in", "is",
            "lambda", "not", "or", "pass", "print", "raise",
            "return", "try", "while", "with", "yield", "None", "True", "False",
            "as", "async", "await", "nonlocal",
        ]
        for word in keywords:
            self.highlighting_rules.append((rf"\b{word}\b", keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"#[^\n]*", comment_format))

        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#2B91AF"))
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r"\b[A-Z][a-zA-Z0-9_]*\b", class_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


# ===================== 项目配置 =====================
class ProjectConfig:
    SETTINGS_FILE = "project_builder.ini"

    @staticmethod
    def get_recent_project():
        settings = QSettings(ProjectConfig.SETTINGS_FILE, QSettings.IniFormat)
        return settings.value("recent_project", "")

    @staticmethod
    def set_recent_project(path):
        settings = QSettings(ProjectConfig.SETTINGS_FILE, QSettings.IniFormat)
        settings.setValue("recent_project", path)


# ===================== 主窗口 =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project_root = ""
        self.open_files = {}
        self.setup_ui()
        self.center_window()
        self.apply_style()

        style = self.style()
        self.icon_dir = style.standardIcon(QApplication.style().SP_DirClosedIcon)
        self.icon_file = style.standardIcon(QApplication.style().SP_FileIcon)

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(5000)
        self.status_timer.timeout.connect(self.refresh_modification_tree)

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projectbuilder.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        recent = ProjectConfig.get_recent_project()
        if recent and os.path.exists(recent):
            QTimer.singleShot(500, lambda: self.open_project(recent))
        else:
            self.status_bar.showMessage("就绪 — 请新建或打开项目")

    def setup_ui(self):
        screen = QApplication.primaryScreen().size()
        self.resize(int(screen.width() * 0.85), int(screen.height() * 0.85))
        self.setWindowTitle("Project Builder — 大型项目辅助构建工具 (AI结构导出版)")

        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        new_action = QAction("新建项目...", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("打开项目...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        save_action = QAction("保存当前文件", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_current_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑(&E)")
        new_module_action = QAction("新建模块...", self)
        new_module_action.setShortcut(QKeySequence("Ctrl+M"))
        new_module_action.triggered.connect(self.new_module)
        edit_menu.addAction(new_module_action)

        delete_action = QAction("删除当前文件", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.delete_current_file)
        edit_menu.addAction(delete_action)

        build_menu = menubar.addMenu("构建(&B)")
        run_action = QAction("运行项目", self)
        run_action.setShortcut(QKeySequence("Ctrl+R"))
        run_action.triggered.connect(self.run_project)
        build_menu.addAction(run_action)

        stop_action = QAction("停止运行", self)
        stop_action.triggered.connect(self.stop_project)
        build_menu.addAction(stop_action)

        help_menu = menubar.addMenu("帮助(&H)")
        stages_action = QAction("开发阶段说明", self)
        stages_action.triggered.connect(self.show_stages)
        help_menu.addAction(stages_action)
        help_menu.addSeparator()
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        toolbar = QToolBar()
        self.addToolBar(toolbar)
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addAction(run_action)

        main_splitter = QSplitter(Qt.Horizontal)
        left_splitter = QSplitter(Qt.Horizontal)

        # ---------- 左侧：项目文件浏览 ----------
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_header_layout = QVBoxLayout()
        tree_header_layout.setContentsMargins(0, 0, 0, 0)
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("<b>项目文件浏览</b>"))
        title_layout.addStretch()
        tree_header_layout.addLayout(title_layout)

        # 每行 2 个按钮，共 2 行（4 个按钮）
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(6)

        self.btn_export_structure = QPushButton("导出AI结构")
        self.btn_export_structure.clicked.connect(self.export_project_structure_for_ai)
        buttons_grid.addWidget(self.btn_export_structure, 0, 0)

        self.btn_copy_all_files = QPushButton("📋 复制所有文件")
        self.btn_copy_all_files.clicked.connect(self.copy_files_to_clipboard)
        buttons_grid.addWidget(self.btn_copy_all_files, 0, 1)

        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_open_folder.clicked.connect(self.open_current_directory_external)
        buttons_grid.addWidget(self.btn_open_folder, 1, 0)

        self.btn_scan_lines = QPushButton("扫描文件代码行数")
        self.btn_scan_lines.clicked.connect(self.scan_file_line_counts)
        buttons_grid.addWidget(self.btn_scan_lines, 1, 1)

        tree_header_layout.addLayout(buttons_grid)
        tree_layout.addLayout(tree_header_layout)

        self.tree_view = QTreeView()
        self.tree_view.setMinimumWidth(220)
        self.tree_view.setMaximumWidth(320)
        tree_container.setMinimumWidth(220)
        tree_container.setMaximumWidth(320)

        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.Filters(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot))

        self.line_proxy = LineCountProxyModel(self)
        self.line_proxy.setSourceModel(self.fs_model)

        self.tree_view.setModel(self.line_proxy)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.setColumnWidth(0, 160)
        self.tree_view.setColumnWidth(1, 56)
        header = self.tree_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)

        self.tree_view.doubleClicked.connect(self.on_tree_double_clicked)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_tree_context_menu)

        tree_layout.addWidget(self.tree_view)
        left_splitter.addWidget(tree_container)

        # ---------- 修改状态监控 ----------
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(QLabel("<b>实时修改状态监控</b>:"))

        self.mod_tree = QTreeWidget()
        self.mod_tree.setHeaderLabels(["文件 / 状态备注"])
        self.mod_tree.itemDoubleClicked.connect(self.on_mod_tree_double_clicked)
        status_layout.addWidget(self.mod_tree)

        left_splitter.addWidget(status_container)
        left_splitter.setSizes([int(self.width() * 0.22), int(self.width() * 0.18)])

        main_splitter.addWidget(left_splitter)

        # ---------- 右侧编辑 + 控制台 ----------
        right_splitter = QSplitter(Qt.Vertical)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab_at)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        right_splitter.addWidget(self.tab_widget)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setMaximumBlockCount(1000)
        right_splitter.addWidget(self.console)

        right_splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])

        self.setCentralWidget(main_splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("未打开项目")
        self.status_bar.addWidget(self.status_label)

        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.on_process_output)
        self.process.readyReadStandardError.connect(self.on_process_error)
        self.process.finished.connect(self.on_process_finished)

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + (screen.width() - self.width()) // 2,
            screen.y() + (screen.height() - self.height()) // 2,
        )

    def apply_style(self):
        style = """
            QMainWindow { background: #f0f0f0; }
            QTreeView, QTreeWidget { background: #ffffff; color: #000000; border: 1px solid #d0d0d0; outline: none; }
            QTreeView::item:selected, QTreeWidget::item:selected { background: #cde8ff; color: #000000; }
            QTreeView::item:hover, QTreeWidget::item:hover { background: #e5f3ff; }
            QTextEdit, QPlainTextEdit { background: #ffffff; color: #000000; border: 1px solid #d0d0d0; font-family: "Consolas", monospace; }
            QMenuBar { background: #f0f0f0; color: #000000; }
            QMenuBar::item:selected { background: #cde8ff; }
            QMenu { background: #ffffff; color: #000000; border: 1px solid #d0d0d0; }
            QMenu::item:selected { background: #cde8ff; }
            QToolBar { background: #f0f0f0; border: none; spacing: 5px; }
            QStatusBar { background: #f0f0f0; color: #000000; }
            QPushButton { background: #e0e0e0; color: #000000; border: 1px solid #b0b0b0; padding: 4px 8px; border-radius: 4px; }
            QPushButton:hover { background: #d0d0d0; }
            QLabel { color: #000000; }
            QTabWidget::pane { border: 1px solid #d0d0d0; background: #ffffff; }
        """
        self.setStyleSheet(style)

    # -------------------- 扫描代码行数 --------------------
    def scan_file_line_counts(self):
        """遍历项目，统计每个文本文件行数，显示在树第二列。"""
        if not self.project_root or not os.path.isdir(self.project_root):
            QMessageBox.warning(self, "提示", "请先打开一个项目目录")
            return

        skip_ext = {
            ".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
            ".exe", ".dll", ".so", ".dylib", ".zip", ".tar", ".gz", ".7z",
            ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".class", ".o", ".a",
        }
        counts = {}
        total_files = 0
        total_lines = 0

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv", "node_modules")
            ]
            for name in files:
                if name.startswith("."):
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext in skip_ext:
                    continue
                full_path = os.path.join(root, name)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        n = sum(1 for _ in f)
                    counts[full_path] = n
                    total_files += 1
                    total_lines += n
                except Exception:
                    continue

        self.line_proxy.set_line_counts(counts)
        # 确保第二列可见
        self.tree_view.setColumnHidden(1, False)
        self.tree_view.setColumnWidth(1, 56)

        self.status_bar.showMessage(
            f"行数扫描完成：{total_files} 个文件，共 {total_lines} 行"
        )
        self.console.appendPlainText(
            f"[系统] 代码行数扫描完成：文件 {total_files}，总行数 {total_lines}"
        )

    # -------------------- 项目打开 / 新建（与原逻辑一致，略压缩） --------------------
    def new_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("新建项目与架构蓝图配置")
        dialog.resize(900, 750)

        main_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("例如: SimpleGitClient")
        form_layout.addRow("项目名称:", name_edit)

        path_layout = QHBoxLayout()
        path_edit = QLineEdit()
        path_edit.setReadOnly(True)
        path_edit.setPlaceholderText("选择父目录...")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(lambda: self.choose_parent_dir(path_edit))
        path_layout.addWidget(path_edit)
        path_layout.addWidget(browse_btn)
        form_layout.addRow("父目录:", path_layout)
        main_layout.addLayout(form_layout)

        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>架构蓝图输入区</b>:"))
        blueprint_edit = QPlainTextEdit()
        blueprint_edit.setPlainText(DEFAULT_ARCHITECTURE_TEXT)
        blueprint_edit.setFont(QFont("Consolas", 10))
        left_layout.addWidget(blueprint_edit)
        analyze_btn = QPushButton("🔍 分析架构")
        left_layout.addWidget(analyze_btn)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>架构分析预览空间</b>:"))
        analysis_browser = QTextBrowser()
        analysis_browser.setFont(QFont("Consolas", 10))
        right_layout.addWidget(analysis_browser)
        splitter.addWidget(right_widget)
        splitter.setSizes([430, 430])
        main_layout.addWidget(splitter)

        def on_analyze_clicked():
            text = blueprint_edit.toPlainText().strip()
            if not text:
                analysis_browser.setPlainText("错误: 蓝图内容为空！")
                return
            summary, folders_count, files_count = self._parse_blueprint_structure(text)
            report = (
                f"=== 架构解析成功 ===\n"
                f"📁 统计目录数: {folders_count}\n"
                f"📄 统计文件数: {files_count}\n\n{summary}"
            )
            analysis_browser.setPlainText(report)

        analyze_btn.clicked.connect(on_analyze_clicked)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        main_layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            parent = path_edit.text().strip()
            blueprint_text = blueprint_edit.toPlainText().strip()
            if not name or not parent:
                QMessageBox.warning(self, "错误", "请填写完整的项目名称和父目录")
                return
            project_path = os.path.join(parent, name)
            if os.path.exists(project_path):
                QMessageBox.warning(self, "错误", "项目目录已存在")
                return
            self._create_project_from_blueprint(project_path, blueprint_text)
            self.open_project(project_path)

    def choose_parent_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择父目录")
        if dir_path:
            line_edit.setText(dir_path)

    def _parse_blueprint_structure(self, text):
        lines = text.splitlines()
        dir_stack = []
        result_lines = []
        folders_count = 0
        files_count = 0

        for line in lines:
            if not line.strip() or line.strip() == "│":
                continue
            clean_line = line.replace("│", " ").replace("├──", "").replace("└──", "").rstrip()
            indent = len(line) - len(line.lstrip(" │"))
            item_name = clean_line.strip()
            if not item_name:
                continue
            if "#" in item_name:
                item_name = item_name.split("#")[0].strip()
            if not item_name:
                continue
            level = indent // 4
            while len(dir_stack) > level:
                dir_stack.pop()
            if item_name.endswith("/"):
                dir_name = item_name.rstrip("/")
                dir_stack.append(dir_name)
                folders_count += 1
                result_lines.append("  " * level + f"📁 {dir_name}/")
            else:
                files_count += 1
                result_lines.append("  " * level + f"📄 {item_name}")
        return "\n".join(result_lines), folders_count, files_count

    def _create_project_from_blueprint(self, base_path, text):
        os.makedirs(base_path, exist_ok=True)
        lines = text.splitlines()
        dir_stack = []
        for line in lines:
            if not line.strip() or line.strip() == "│":
                continue
            clean_line = line.replace("│", " ").replace("├──", "").replace("└──", "").rstrip()
            indent = len(line) - len(line.lstrip(" │"))
            item_name = clean_line.strip()
            if not item_name:
                continue
            if "#" in item_name:
                item_name = item_name.split("#")[0].strip()
            if not item_name:
                continue
            level = indent // 4
            while len(dir_stack) > level:
                dir_stack.pop()
            if item_name.endswith("/"):
                dir_name = item_name.rstrip("/")
                current_dir = os.path.join(base_path, *dir_stack, dir_name)
                os.makedirs(current_dir, exist_ok=True)
                dir_stack.append(dir_name)
            else:
                current_dir = os.path.join(base_path, *dir_stack)
                os.makedirs(current_dir, exist_ok=True)
                file_path = os.path.join(current_dir, item_name)
                content = f"# -*- coding: utf-8 -*-\n# 文件: {item_name}\n\n"
                if item_name == "main.py":
                    content = (
                        "import sys\n"
                        "from PySide2.QtWidgets import QApplication\n\n"
                        "def main():\n"
                        "    app = QApplication(sys.argv)\n"
                        "    sys.exit(app.exec_())\n\n"
                        "if __name__ == '__main__':\n"
                        "    main()\n"
                    )
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception:
                    pass

    def open_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "打开项目目录")
        if folder:
            self.open_project(folder)

    def open_project(self, path):
        if not os.path.isdir(path):
            return
        self.project_root = path
        root_index = self.fs_model.setRootPath(path)
        proxy_index = self.line_proxy.mapFromSource(root_index)
        self.tree_view.setRootIndex(proxy_index)
        self.line_proxy.clear_line_counts()

        self.status_label.setText(path)
        self.status_bar.showMessage(f"已打开项目: {path}")
        ProjectConfig.set_recent_project(path)
        self.console.appendPlainText(f"[系统] 项目已打开: {path}")

        self.tab_widget.clear()
        self.open_files = {}
        self.refresh_modification_tree()
        self.status_timer.start()

    def open_current_directory_external(self):
        if not self.project_root or not os.path.isdir(self.project_root):
            QMessageBox.warning(self, "提示", "请先打开一个项目目录")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_root))

    def export_project_structure_for_ai(self):
        if not self.project_root or not os.path.isdir(self.project_root):
            QMessageBox.warning(self, "提示", "请先打开一个项目目录")
            return

        structure_lines = []
        project_name = os.path.basename(self.project_root)
        structure_lines.append(f"{project_name}/")

        def build_tree_text(current_dir, prefix=""):
            try:
                entries = sorted(os.listdir(current_dir))
            except Exception:
                return
            valid_entries = [e for e in entries if not e.startswith(".")]
            for i, entry in enumerate(valid_entries):
                full_path = os.path.join(current_dir, entry)
                is_last = i == len(valid_entries) - 1
                connector = "└── " if is_last else "├── "
                if os.path.isdir(full_path):
                    structure_lines.append(f"{prefix}{connector}{entry}/")
                    extension = "    " if is_last else "│   "
                    build_tree_text(full_path, prefix + extension)
                else:
                    structure_lines.append(f"{prefix}{connector}{entry}")

        build_tree_text(self.project_root)
        tree_str = "\n".join(structure_lines)
        ai_prompt_text = f"项目路径: {self.project_root}\n\n{tree_str}"

        dialog = QDialog(self)
        dialog.setWindowTitle("导出AI结构助手")
        dialog.resize(700, 550)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("<b>已为您生成结构文本：</b>"))
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(ai_prompt_text)
        text_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(text_edit)
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 一键复制")

        def on_copy():
            QApplication.clipboard().setText(text_edit.toPlainText())
            QMessageBox.information(dialog, "成功", "已复制到剪贴板！")

        copy_btn.clicked.connect(on_copy)
        btn_layout.addWidget(copy_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        dialog.exec_()

    def refresh_modification_tree(self):
        if not self.project_root or not os.path.isdir(self.project_root):
            return
        self.mod_tree.clear()
        root_name = os.path.basename(self.project_root) or self.project_root
        root_item = QTreeWidgetItem([root_name])
        root_item.setIcon(0, self.icon_dir)
        self.mod_tree.addTopLevelItem(root_item)
        now = datetime.now()

        def add_recursive(current_dir, parent_item):
            try:
                entries = sorted(os.listdir(current_dir))
            except Exception:
                return
            for entry in entries:
                if entry.startswith("."):
                    continue
                full_path = os.path.join(current_dir, entry)
                if os.path.isdir(full_path):
                    dir_item = QTreeWidgetItem([entry + "/"])
                    dir_item.setIcon(0, self.icon_dir)
                    parent_item.addChild(dir_item)
                    add_recursive(full_path, dir_item)
                elif os.path.isfile(full_path):
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                        delta_min = (now - mtime).total_seconds() / 60.0
                    except Exception:
                        delta_min = 9999
                    if delta_min <= 5:
                        display_text = f"{entry} (5分钟内)"
                        color = QColor("#D32F2F")
                    elif delta_min <= 15:
                        display_text = f"{entry} (15分钟内)"
                        color = QColor("#1976D2")
                    else:
                        display_text = f"{entry} (30分钟以上)"
                        color = QColor("#388E3C")
                    file_item = QTreeWidgetItem([display_text])
                    file_item.setIcon(0, self.icon_file)
                    file_item.setData(0, Qt.UserRole, full_path)
                    file_item.setForeground(0, color)
                    parent_item.addChild(file_item)

        add_recursive(self.project_root, root_item)
        self.mod_tree.expandAll()

    def on_mod_tree_double_clicked(self, item, column):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.isfile(file_path):
            self.load_file_to_tab(file_path)

    def on_tree_double_clicked(self, index):
        if not index.isValid():
            return
        # 映射到源模型取路径
        src = self.line_proxy.mapToSource(index)
        if src.column() != 0:
            src = src.sibling(src.row(), 0)
        file_path = self.fs_model.filePath(src)
        if os.path.isfile(file_path):
            self.load_file_to_tab(file_path)

    def focus_search_input(self, search_input):
        search_input.selectAll()
        search_input.setFocus()

    def find_in_editor(self, editor, text):
        if not text:
            return
        cursor = editor.textCursor()
        found = editor.document().find(text, cursor)
        if found.isNull():
            start_cursor = QTextCursor(editor.document())
            start_cursor.movePosition(QTextCursor.Start)
            found = editor.document().find(text, start_cursor)
        if found.isNull():
            QMessageBox.information(self, "查找结果", f"未找到：{text}")
        else:
            editor.setTextCursor(found)
            editor.ensureCursorVisible()

    def jump_to_structure_line(self, editor, item):
        line_number = item.data(0, Qt.UserRole)
        if not isinstance(line_number, int):
            return
        block = editor.document().findBlockByNumber(line_number - 1)
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.LineUnderCursor)
        editor.setTextCursor(cursor)
        editor.centerCursor()
        editor.ensureCursorVisible()

    def refresh_structure_tree(self, file_path, editor, structure_tree):
        structure_tree.clear()
        root_item = QTreeWidgetItem(["类 / 方法"])
        root_item.setExpanded(True)
        structure_tree.addTopLevelItem(root_item)
        if not file_path.endswith(".py"):
            root_item.addChild(QTreeWidgetItem(["当前文件暂不支持自动解析"]))
            return
        class_stack = []
        lines = editor.toPlainText().splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            while class_stack and indent <= class_stack[-1][0]:
                class_stack.pop()
            class_match = re.match(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
            if class_match:
                class_item = QTreeWidgetItem([class_match.group(1)])
                class_item.setData(0, Qt.UserRole, idx)
                root_item.addChild(class_item)
                class_stack.append((indent, class_item))
                continue
            method_match = re.match(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
            if method_match:
                parent_item = class_stack[-1][1] if class_stack else root_item
                method_item = QTreeWidgetItem([method_match.group(1)])
                method_item.setData(0, Qt.UserRole, idx)
                parent_item.addChild(method_item)
        if root_item.childCount() == 0:
            root_item.addChild(QTreeWidgetItem(["未解析到类或方法"]))

    def create_editor_panel(self, file_path, content):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        search_row = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Ctrl+F 查找")
        search_input.setClearButtonEnabled(True)
        find_btn = QPushButton("查找")
        search_row.addWidget(search_input)
        search_row.addWidget(find_btn)
        layout.addLayout(search_row)

        main_splitter = QSplitter(Qt.Horizontal)
        editor = CodeEditor()
        editor.setFont(QFont("Consolas", 11))
        editor.setPlainText(content)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        main_splitter.addWidget(editor)

        structure_tree = QTreeWidget()
        structure_tree.setHeaderHidden(True)
        structure_tree.setMinimumWidth(200)
        structure_tree.setMaximumWidth(300)
        structure_tree.itemClicked.connect(
            lambda item, column: self.jump_to_structure_line(editor, item)
        )
        main_splitter.addWidget(structure_tree)
        layout.addWidget(main_splitter)

        search_input.returnPressed.connect(
            lambda: self.find_in_editor(editor, search_input.text())
        )
        find_btn.clicked.connect(lambda: self.find_in_editor(editor, search_input.text()))
        QShortcut(QKeySequence("Ctrl+F"), editor).activated.connect(
            lambda: self.focus_search_input(search_input)
        )
        QShortcut(QKeySequence("Ctrl+F"), container).activated.connect(
            lambda: self.focus_search_input(search_input)
        )

        def on_editor_changed():
            self.mark_tab_modified(editor, file_path)
            self.refresh_structure_tree(file_path, editor, structure_tree)

        editor.textChanged.connect(on_editor_changed)
        self.refresh_structure_tree(file_path, editor, structure_tree)
        return container, editor, structure_tree, search_input

    def load_file_to_tab(self, file_path):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabToolTip(i) == file_path:
                self.tab_widget.setCurrentIndex(i)
                return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取文件失败:\n{str(e)}")
            return

        container, editor, structure_tree, search_input = self.create_editor_panel(
            file_path, content
        )
        highlighter = None
        if file_path.endswith(".py"):
            highlighter = PythonHighlighter(editor.document())

        file_name = os.path.basename(file_path)
        index = self.tab_widget.addTab(container, file_name)
        self.tab_widget.setTabToolTip(index, file_path)
        self.tab_widget.setCurrentIndex(index)

        self.open_files[file_path] = {
            "editor": editor,
            "highlighter": highlighter,
            "modified": False,
            "structure_tree": structure_tree,
            "search_input": search_input,
        }
        self.status_bar.showMessage(f"已加载: {file_path}")
        editor.setFocus()

    def mark_tab_modified(self, editor, file_path):
        if file_path in self.open_files:
            if not self.open_files[file_path]["modified"]:
                self.open_files[file_path]["modified"] = True
                idx = self.get_tab_index_by_path(file_path)
                if idx != -1:
                    current_text = self.tab_widget.tabText(idx)
                    if not current_text.endswith("*"):
                        self.tab_widget.setTabText(idx, current_text + "*")

    def get_tab_index_by_path(self, file_path):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabToolTip(i) == file_path:
                return i
        return -1

    def close_tab_at(self, index):
        file_path = self.tab_widget.tabToolTip(index)
        if file_path in self.open_files and self.open_files[file_path]["modified"]:
            reply = QMessageBox.question(
                self,
                "未保存",
                f"文件 {os.path.basename(file_path)} 有修改，是否保存？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                self.save_file_by_path(file_path)
            del self.open_files[file_path]
        elif file_path in self.open_files:
            del self.open_files[file_path]
        self.tab_widget.removeTab(index)

    def on_tab_changed(self, index):
        if index != -1:
            path = self.tab_widget.tabToolTip(index)
            self.status_bar.showMessage(f"当前文件: {path}")
            info = self.open_files.get(path)
            if info and "editor" in info and "structure_tree" in info:
                self.refresh_structure_tree(path, info["editor"], info["structure_tree"])

    def save_current_file(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1:
            return
        self.save_file_by_path(self.tab_widget.tabToolTip(idx))

    def save_file_by_path(self, file_path):
        if file_path not in self.open_files:
            return
        editor = self.open_files[file_path]["editor"]
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            self.open_files[file_path]["modified"] = False
            idx = self.get_tab_index_by_path(file_path)
            if idx != -1:
                self.tab_widget.setTabText(idx, os.path.basename(file_path))
            self.status_bar.showMessage(f"已保存: {file_path}")
            self.refresh_modification_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

    def delete_current_file(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1:
            QMessageBox.information(self, "提示", "没有打开的活动文件可删除")
            return
        self.delete_file_by_path(self.tab_widget.tabToolTip(idx))

    def delete_file_by_path(self, file_path):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要彻底删除:\n{file_path}？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            idx = self.get_tab_index_by_path(file_path)
            if idx != -1:
                self.tab_widget.removeTab(idx)
            if file_path in self.open_files:
                del self.open_files[file_path]
            self.status_bar.showMessage("已删除: " + file_path)
            self.refresh_modification_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败:\n{str(e)}")

    def new_module(self):
        if not self.project_root:
            QMessageBox.warning(self, "提示", "请先打开一个项目")
            return
        module_name, ok = QInputDialog.getText(self, "新建模块", "输入模块名称 (不含.py):")
        if not ok or not module_name.strip():
            return
        name = module_name.strip()
        class_name = "".join(part.capitalize() for part in name.split("_"))
        file_name = name + ".py"
        target_dir = os.path.join(self.project_root, "ui")
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, file_name)
        if os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件已存在")
            return
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# -*- coding: utf-8 -*-\nclass {class_name}:\n    pass\n")
        self.status_bar.showMessage(f"模块已创建: {file_path}")
        self.load_file_to_tab(file_path)
        self.refresh_modification_tree()

    def show_tree_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        menu = QMenu(self)

        if not index.isValid():
            if not self.project_root:
                return
            new_file_action = QAction("新建文件...", self)
            new_file_action.triggered.connect(
                lambda: self.create_file_in_directory(self.project_root)
            )
            menu.addAction(new_file_action)
            new_dir_action = QAction("新建文件夹...", self)
            new_dir_action.triggered.connect(
                lambda: self.create_directory_in_directory(self.project_root)
            )
            menu.addAction(new_dir_action)
        else:
            src = self.line_proxy.mapToSource(index)
            if src.column() != 0:
                src = src.sibling(src.row(), 0)
            file_path = self.fs_model.filePath(src)
            is_dir = self.fs_model.isDir(src)
            if is_dir:
                menu.addAction(QAction("打开文件", self)).setEnabled(False)
                menu.addSeparator()
                a1 = QAction("新建文件...", self)
                a1.triggered.connect(lambda: self.create_file_in_directory(file_path))
                menu.addAction(a1)
                a2 = QAction("新建文件夹...", self)
                a2.triggered.connect(lambda: self.create_directory_in_directory(file_path))
                menu.addAction(a2)
                menu.addSeparator()
                a3 = QAction("删除文件夹", self)
                a3.triggered.connect(lambda: self.delete_file_by_path(file_path))
                menu.addAction(a3)
            else:
                a0 = QAction("打开文件", self)
                a0.triggered.connect(lambda: self.load_file_to_tab(file_path))
                menu.addAction(a0)
                menu.addSeparator()
                a3 = QAction("删除文件", self)
                a3.triggered.connect(lambda: self.delete_file_by_path(file_path))
                menu.addAction(a3)

        menu.exec_(self.tree_view.viewport().mapToGlobal(pos))

    def create_file_in_directory(self, dir_path):
        file_name, ok = QInputDialog.getText(self, "新建文件", "输入文件名:")
        if ok and file_name.strip():
            full_path = os.path.join(dir_path, file_name.strip())
            if os.path.exists(full_path):
                QMessageBox.warning(self, "错误", "文件已存在！")
                return
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("# -*- coding: utf-8 -*-\n\n")
                self.status_bar.showMessage(f"已创建文件: {full_path}")
                self.load_file_to_tab(full_path)
                self.refresh_modification_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建文件失败:\n{str(e)}")

    def create_directory_in_directory(self, dir_path):
        dir_name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:")
        if ok and dir_name.strip():
            full_path = os.path.join(dir_path, dir_name.strip())
            if os.path.exists(full_path):
                QMessageBox.warning(self, "错误", "文件夹已存在！")
                return
            try:
                os.makedirs(full_path, exist_ok=True)
                self.status_bar.showMessage(f"已创建文件夹: {full_path}")
                self.refresh_modification_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建文件夹失败:\n{str(e)}")

    def run_project(self):
        if not self.project_root:
            QMessageBox.warning(self, "提示", "请先打开一个项目")
            return
        main_path = os.path.join(self.project_root, "main.py")
        if not os.path.exists(main_path):
            QMessageBox.critical(self, "错误", "项目根目录下没有找到 main.py")
            return
        for path, info in self.open_files.items():
            if info["modified"]:
                self.save_file_by_path(path)
        self.console.clear()
        self.console.appendPlainText(f"[系统] 运行项目: {main_path}\n")
        self.process.setWorkingDirectory(self.project_root)
        self.process.start(sys.executable, [main_path])

    def stop_project(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.console.appendPlainText("[系统] 项目已强制停止")

    def on_process_output(self):
        data = self.process.readAllStandardOutput()
        text = data.data().decode("utf-8", errors="ignore")
        self.console.appendPlainText(text)
        self.console.moveCursor(QTextCursor.End)

    def on_process_error(self):
        data = self.process.readAllStandardError()
        text = data.data().decode("utf-8", errors="ignore")
        self.console.appendPlainText("[错误] " + text)
        self.console.moveCursor(QTextCursor.End)

    def on_process_finished(self, exit_code, exit_status):
        self.console.appendPlainText(f"\n[系统] 进程结束，退出码: {exit_code}")

    def show_stages(self):
        QMessageBox.information(
            self, "开发阶段建议", "推荐开发顺序：1.工程框架 2.核心模块 3.UI与文件树"
        )

    def show_about(self):
        QMessageBox.about(self, "关于", "Project Builder v2.2（行号 + 代码行数扫描）")

    def closeEvent(self, event):
        for path, info in list(self.open_files.items()):
            if info["modified"]:
                reply = QMessageBox.question(
                    self,
                    "未保存",
                    f"文件 {os.path.basename(path)} 有修改，是否保存？",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                )
                if reply == QMessageBox.Cancel:
                    event.ignore()
                    return
                if reply == QMessageBox.Yes:
                    self.save_file_by_path(path)
        if self.process.state() == QProcess.Running:
            self.process.kill()
        event.accept()

    def copy_files_to_clipboard(self):
        """保留原分批复制对话框的入口（完整实现与原版一致的核心能力）。"""
        if not self.project_root or not os.path.isdir(self.project_root):
            QMessageBox.warning(self, "提示", "请先打开一个项目目录！")
            return

        all_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if file.startswith("."):
                    continue
                full_path = os.path.join(root, file)
                if os.path.isfile(full_path):
                    rel_path = os.path.relpath(full_path, self.project_root)
                    all_files.append((rel_path, full_path))

        if not all_files:
            QMessageBox.warning(self, "提示", "当前项目中未找到任何文件！")
            return

        # 简化：一次性复制全部文本内容到剪贴板（路径标注格式）
        chunks = []
        count = 0
        for rel_path, full_path in all_files:
            ext = os.path.splitext(rel_path)[1].lower()
            if ext in {".png", ".jpg", ".jpeg", ".gif", ".exe", ".pyc", ".pyo"}:
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                chunks.append(f"# === FILE: {rel_path} ===\n{content}")
                count += 1
            except Exception as e:
                chunks.append(f"# === FILE: {rel_path} ===\n# [读取失败: {e}]")

        if count == 0:
            QMessageBox.warning(self, "提示", "没有可复制的文本文件！")
            return

        QApplication.clipboard().setText("\n\n".join(chunks))
        QMessageBox.information(
            self,
            "复制成功",
            f"已复制 {count} 个文件内容到剪贴板。",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Project Builder")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
