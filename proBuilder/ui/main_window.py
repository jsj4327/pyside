#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide2.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QMessageBox, QFileDialog,
    QApplication, QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout, QLabel
)
from PySide2.QtCore import Qt, QTimer, QProcess, QUrl
from PySide2.QtGui import QFont, QTextCursor, QClipboard, QDesktopServices

from config.settings import SettingsManager
from core.generator import ProjectGenerator
from ui.widgets.file_tree import FileTreeWidget
from ui.widgets.console import ConsoleWidget
from ui.new_project_dialog import NewProjectDialog

class MainWindow(QMainWindow):
    """ProBuilder 主窗口"""
    def __init__(self):
        super().__init__()
        self.project_root = ""
        self.open_files = {}  # 记录当前打开的文件标签页内容状态
        self.setup_ui()
        self.apply_style()

        # 后台监控定时器（每5秒刷新一次修改状态树）
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(5000)
        self.status_timer.timeout.connect(self.file_tree.refresh_modification_tree)

        # 异步进程运行器
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.on_process_output)
        self.process.readyReadStandardError.connect(self.on_process_error)
        self.process.finished.connect(self.on_process_finished)

        # 自动加载最近项目
        recent = SettingsManager.get_recent_project()
        if recent and os.path.exists(recent):
            QTimer.singleShot(300, lambda: self.open_project(recent))

    def setup_ui(self):
        geom = SettingsManager.get_window_geometry()
        self.resize(geom["width"], geom["height"])
        self.setWindowTitle("ProBuilder — 大型项目辅助构建与AI结构导出版")

        # 菜单栏与动作
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        
        new_action = file_menu.addAction("新建项目...")
        new_action.triggered.connect(self.new_project)
        
        open_action = file_menu.addAction("打开项目...")
        open_action.triggered.connect(self.open_project_dialog)
        
        file_menu.addSeparator()
        save_action = file_menu.addAction("保存当前文件")
        save_action.triggered.connect(self.save_current_file)

        # 核心布局分栏
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：文件树面板
        self.file_tree = FileTreeWidget()
        self.file_tree.file_double_clicked.connect(self.load_file_to_tab)
        self.file_tree.btn_export.clicked.connect(self.export_ai_structure)
        self.file_tree.btn_open_folder.clicked.connect(self.open_external_folder)
        main_splitter.addWidget(self.file_tree)

        # 右侧分栏：上方标签页编辑器，下方控制台
        right_splitter = QSplitter(Qt.Vertical)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        right_splitter.addWidget(self.tab_widget)

        self.console = ConsoleWidget()
        right_splitter.addWidget(self.console)
        
        right_splitter.setSizes([600, 200])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([300, 900])

        self.setCentralWidget(main_splitter)

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f7; }
            QTabWidget::pane { border: 1px solid #dcdcdc; background: white; }
            QPushButton { background-color: #e1e1e1; border: 1px solid #adadad; padding: 4px 10px; border-radius: 3px; }
            QPushButton:hover { background-color: #e5f1fb; border-color: #0078d7; }
        """)

    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            ProjectGenerator.generate_project(dialog.project_path, dialog.blueprint_text)
            self.open_project(dialog.project_path)

    def open_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if folder:
            self.open_project(folder)

    def open_project(self, path: str):
        if not os.path.isdir(path):
            return
        self.project_root = path
        self.file_tree.set_root_path(path)
        SettingsManager.set_recent_project(path)
        self.console.append_output(f"[系统] 已成功加载项目: {path}\n")
        
        self.tab_widget.clear()
        self.open_files.clear()
        self.status_timer.start()

    def open_external_folder(self):
        if self.project_root:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_root))

    def export_ai_structure(self):
        if not self.project_root:
            QMessageBox.warning(self, "提示", "请先打开项目！")
            return

        # 实时生成目录树文本给AI
        lines = [os.path.basename(self.project_root) + "/"]
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            level = root.replace(self.project_root, '').count(os.sep)
            indent = "    " * level
            for f in files:
                if not f.startswith('.'):
                    lines.append(f"{indent}├── {f}")

        tree_str = "\n".join(lines)
        
        # 弹窗展示
        dlg = QDialog(self)
        dlg.setWindowTitle("一键导出AI项目结构")
        dlg.resize(600, 450)
        lay = QVBoxLayout(dlg)
        
        te = QPlainTextEdit()
        te.setPlainText(tree_str)
        te.setFont(QFont("Consolas", 10))
        lay.addWidget(te)

        btn = QPushButton("📋 复制到剪贴板")
        btn.clicked.connect(lambda: QApplication.clipboard().setText(te.toPlainText()))
        lay.addWidget(btn)
        dlg.exec_()

    def load_file_to_tab(self, file_path: str):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabToolTip(i) == file_path:
                self.tab_widget.setCurrentIndex(i)
                return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件:\n{e}")
            return

        editor = QPlainTextEdit()
        editor.setFont(QFont("Consolas", 10))
        editor.setPlainText(content)
        editor.textChanged.connect(lambda: self.mark_modified(file_path))

        file_name = os.path.basename(file_path)
        index = self.tab_widget.addTab(editor, file_name)
        self.tab_widget.setTabToolTip(index, file_path)
        self.tab_widget.setCurrentIndex(index)
        
        self.open_files[file_path] = {"editor": editor, "modified": False}

    def mark_modified(self, file_path: str):
        if file_path in self.open_files and not self.open_files[file_path]["modified"]:
            self.open_files[file_path]["modified"] = True
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabToolTip(i) == file_path:
                    curr_text = self.tab_widget.tabText(i)
                    if not curr_text.endswith("*"):
                        self.tab_widget.setTabText(i, curr_text + "*")

    def save_current_file(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1:
            return
        file_path = self.tab_widget.tabToolTip(idx)
        if file_path in self.open_files:
            editor = self.open_files[file_path]["editor"]
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                self.open_files[file_path]["modified"] = False
                self.tab_widget.setTabText(idx, os.path.basename(file_path))
                self.console.append_output(f"[系统] 文件已保存: {file_path}\n")
                self.file_tree.refresh_modification_tree()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def close_tab(self, index):
        file_path = self.tab_widget.tabToolTip(index)
        if file_path in self.open_files and self.open_files[file_path]["modified"]:
            reply = QMessageBox.question(
                self, "未保存", f"文件 {os.path.basename(file_path)} 已修改，是否保存？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.Yes:
                self.tab_widget.setCurrentIndex(index)
                self.save_current_file()
            del self.open_files[file_path]
        self.tab_widget.removeTab(index)

    def on_process_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.console.append_output(data, is_error=False)

    def on_process_error(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.console.append_output(data, is_error=True)

    def on_process_finished(self, exit_code, exit_status):
        self.console.append_output(f"\n[系统] 进程退出，状态码: {exit_code}\n")

    def closeEvent(self, event):
        # 记录窗口尺寸
        SettingsManager.set_window_geometry(self.width(), self.height())
        if self.process.state() == QProcess.Running:
            self.process.kill()
        event.accept()