# -*- coding:utf-8 -*-
import os
import json
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QFileSystemModel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QTextEdit, QLabel, QMessageBox
)
from PySide2.QtCore import Qt, QDir, QTimer
from core import FileAnalyzer

class FileBrowserMainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_work_dir = QDir.homePath()
        self.current_file_path = None
        self._init_ui()
        self._bind_signals()
        self._refresh_file_table()

    @property
    def tree(self):
        """将旧的 tree 属性安全映射到实际的 tree_view 上，确保持久化兼容"""
        return getattr(self, 'tree_view', None)

    def _init_ui(self):
        horizontal_splitter = QSplitter(Qt.Horizontal)

        # --- 左侧目录树 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(self.current_work_dir)
        self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setRootIndex(self.tree_model.index(self.current_work_dir))
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        left_layout.addWidget(self.tree_view)
        horizontal_splitter.addWidget(left_panel)

        # --- 中间文件列表 ---
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        btn_bar = QHBoxLayout()
        self.btn_up = QPushButton("⬆ 上级目录")
        self.btn_refresh = QPushButton("🔄 刷新")
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        btn_bar.addWidget(self.btn_up)
        btn_bar.addWidget(self.btn_refresh)
        btn_bar.addWidget(self.path_display)
        mid_layout.addLayout(btn_bar)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["文件名", "文件大小", "总行数"])
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        mid_layout.addWidget(self.file_table)
        horizontal_splitter.addWidget(mid_panel)

        # --- 右侧预览 + AI 按钮 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        tool_bar = QHBoxLayout()
        self.btn_ai = QPushButton("🤖 发送给 AI 分析")
        self.btn_ai.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px; font-weight: bold;")
        self.btn_ai.clicked.connect(self._send_to_ai_via_ws)
        self.btn_ai.setEnabled(False)
        tool_bar.addWidget(self.btn_ai)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        right_layout.addLayout(tool_bar)
        right_layout.addWidget(self.text_preview)

        horizontal_splitter.addWidget(right_panel)
        horizontal_splitter.setStretchFactor(0, 1)
        horizontal_splitter.setStretchFactor(1, 1.3)
        horizontal_splitter.setStretchFactor(2, 2)
        horizontal_splitter.setSizes([220, 360, 620])

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(horizontal_splitter)

    def _bind_signals(self):
        self.tree_view.doubleClicked.connect(self._on_tree_dir_double_click)
        self.file_table.doubleClicked.connect(self._on_table_file_double_click)
        self.file_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_up.clicked.connect(self._goto_parent_dir)
        self.btn_refresh.clicked.connect(self._refresh_file_table)

    def _on_selection_changed(self):
        selected_items = self.file_table.selectedItems()
        if selected_items:
            item = selected_items[0]
            self.current_file_path = item.data(Qt.UserRole)
            self.btn_ai.setEnabled(True)
        else:
            self.btn_ai.setEnabled(False)

    def _send_to_ai_via_ws(self):
        """通过 WebSocket 发送文件内容给插件（即发即走，不卡顿）"""
        if not self.current_file_path:
            return

        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.warning(self, "错误", "Bridge 服务未启动")
            return

        if not main_win.bridge_server.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接，请确保 Chrome 插件已连接")
            return

        try:
            content = FileAnalyzer.read_text_file(self.current_file_path)
            filename = os.path.basename(self.current_file_path)

            payload = {
                "type": "ANALYZE_REQUEST",
                "filename": filename,
                "content": content,
                "message": f"请帮我分析文件: {filename}"
            }

            success = False
            for attempt in range(3):
                try:
                    main_win.bridge_server.send_to_all_clients(payload)
                    success = True
                    break
                except Exception as e:
                    print(f"[发送] 第 {attempt+1} 次尝试失败: {e}")
                    if attempt == 2:
                        raise
                    QTimer.singleShot(500, lambda: None)

            if success:
                if main_win.statusBar():
                    main_win.statusBar().showMessage(f"📤 已成功发送 '{filename}' 给插件", 3000)
                # 核心：发送成功后立即重置按钮，恢复可用状态
                self._reset_ai_button()
            else:
                raise Exception("发送失败，请检查插件连接")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")
            self._reset_ai_button()

    def append_ai_result(self, result_text):
        """供 MainWindow 调用，异步显示 AI 返回的结果（已完整还原）"""
        if not result_text:
            self.text_preview.append("\n" + "=" * 30 + "\n")
            self.text_preview.append("【AI 分析结果】：\n")
            self.text_preview.append("(空结果)")
            if self.window() and self.window().statusBar():
                self.window().statusBar().showMessage("⚠️ AI 返回空结果", 3000)
            return

        self.text_preview.append("\n" + "=" * 30 + "\n")
        self.text_preview.append("【AI 分析结果】：\n")
        self.text_preview.append(result_text)

        if self.window() and self.window().statusBar():
            self.window().statusBar().showMessage("✅ AI 分析完成", 3000)

    def _reset_ai_button(self):
        self.btn_ai.setText("🤖 发送给 AI 分析")
        if self.file_table.selectedItems():
            self.btn_ai.setEnabled(True)

    # --- 文件操作与浏览逻辑 ---
    def _refresh_file_table(self):
        self.file_table.setRowCount(0)
        self.path_display.setText(self.current_work_dir)
        dir_obj = QDir(self.current_work_dir)
        dir_obj.setFilter(QDir.NoDotAndDotDot | QDir.Files)
        for info in dir_obj.entryInfoList():
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            full_path = info.absoluteFilePath()
            filename = info.fileName()
            size_str = f"{info.size()} B" if info.size() < 1024 else f"{info.size() / 1024:.1f} KB"
            total, _, _, is_bin = FileAnalyzer.stat_file_lines(full_path)

            item_name = QTableWidgetItem(filename)
            item_name.setData(Qt.UserRole, full_path)
            item_size = QTableWidgetItem(size_str)
            line_item = QTableWidgetItem(str(total) if not is_bin else "二进制")

            self.file_table.setItem(row, 0, item_name)
            self.file_table.setItem(row, 1, item_size)
            self.file_table.setItem(row, 2, line_item)

    def _on_tree_dir_double_click(self, index):
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            self.current_work_dir = path
            self.tree_view.setRootIndex(index)
            self.tree_view.setCurrentIndex(index)
            self._refresh_file_table()

    def _goto_parent_dir(self):
        parent_path = os.path.dirname(self.current_work_dir)
        if parent_path != self.current_work_dir:
            self.current_work_dir = parent_path
            self.tree_view.setRootIndex(self.tree_model.index(parent_path))
            self._refresh_file_table()

    def _on_table_file_double_click(self, index):
        row = index.row()
        file_path = self.file_table.item(row, 0).data(Qt.UserRole)
        self.text_preview.clear()
        total, valid, empty, is_bin = FileAnalyzer.stat_file_lines(file_path)
        if is_bin:
            self.text_preview.setText(f"【二进制文件无法预览】\n{file_path}")
            return
        try:
            content = FileAnalyzer.read_text_file(file_path)
            self.text_preview.setText(content)
            msg = f"文件：{os.path.basename(file_path)} | 总行数:{total} | 有效行:{valid}"
            if self.window():
                self.window().statusBar().showMessage(msg, 8000)
        except Exception as e:
            self.text_preview.setText(f"读取失败：{str(e)}")