# modules/shell/main_window.py
import sys
from PySide2.QtCore import Qt, QTimer
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QComboBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QCheckBox,
    QGroupBox,
    QDoubleSpinBox,
    QProgressBar,
    QToolButton,
    QMessageBox,
    QFrame,
    QMenu,
    QAction
)
from modules.shell.application.shell_controller import ShellController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BigShrimp - 多模块工作台")

        # 实例化应用层控制器
        self.controller = ShellController(self)

        self.init_ui()
        self.center_window()
        self.bind_signals()

    def init_ui(self):
        # 初始化底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("本地 9002 服务初始化完成")

        # 创建持久化的连接状态指示标签
        self.connection_label = QLabel("插件未连接")
        self.connection_label.setStyleSheet("color: red; background: transparent;")
        self.status_bar.addPermanentWidget(self.connection_label)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- Tab 1: 请求台（重构版）---
        self.tab_request = QWidget()
        self.init_request_tab()
        self.tab_widget.addTab(self.tab_request, "🎯 请求台")

        # --- Tab 2: 多文件批量处理工作台 ---
        self.tab_workspace = QWidget()
        self.init_workspace_tab()
        self.tab_widget.addTab(self.tab_workspace, "📦 批量工作台")

    def init_request_tab(self):
        """重构请求台 UI - 三列布局"""
        from PySide2.QtWidgets import QToolButton
        from PySide2.QtGui import QFont, QPalette, QColor
        
        main_splitter = QSplitter(Qt.Horizontal, self.tab_request)
        main_splitter.setHandleWidth(2)

        # ========================================
        # 左侧列：输入区 (25%)
        # ========================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(8)

        # 标题
        input_title = QLabel("📥 输入")
        input_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        left_layout.addWidget(input_title)

        # 原始提示词
        left_layout.addWidget(QLabel("原始提示词:"))
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("在此输入您的提示词，或拖拽文本文件...")
        self.input_edit.setMinimumHeight(180)
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        left_layout.addWidget(self.input_edit)

        # 框架选择
        left_layout.addWidget(QLabel("提示词框架:"))
        self.framework_combo = QComboBox()
        self.framework_combo.addItems(["默认框架", "框架选项A", "框架选项B", "框架选项C"])
        self.framework_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                min-height: 28px;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
        """)
        left_layout.addWidget(self.framework_combo)

        # 高级设置（折叠面板）
        self.advanced_btn = QPushButton("⚙️ 高级设置")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setStyleSheet("""
            QPushButton {
                background: #f8f9fa;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                text-align: left;
            }
            QPushButton:checked {
                background: #e9ecef;
            }
        """)
        left_layout.addWidget(self.advanced_btn)

        self.advanced_widget = QWidget()
        self.advanced_widget.setVisible(False)
        advanced_layout = QHBoxLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(10, 5, 10, 5)
        advanced_layout.setSpacing(15)

        advanced_layout.addWidget(QLabel("温度:"))
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setFixedWidth(60)
        advanced_layout.addWidget(self.temperature_spin)

        advanced_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4", "gpt-3.5-turbo", "claude-3"])
        self.model_combo.setFixedWidth(120)
        advanced_layout.addWidget(self.model_combo)

        advanced_layout.addStretch()
        left_layout.addWidget(self.advanced_widget)

        # 发送按钮
        btn_layout = QHBoxLayout()
        self.send_button = QPushButton("🚀 发送请求")
        self.send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                min-height: 40px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5dade2, stop:1 #3498db);
            }
            QPushButton:pressed {
                background: #2980b9;
            }
            QPushButton:disabled {
                background: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        btn_layout.addWidget(self.send_button)

        self.clear_button = QPushButton("清空")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #d5dbdb;
            }
        """)
        btn_layout.addWidget(self.clear_button)
        left_layout.addLayout(btn_layout)

        # 状态指示器
        self.status_indicator = QLabel("⚪ 就绪")
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
                padding: 4px;
            }
        """)
        left_layout.addWidget(self.status_indicator)

        left_layout.addStretch()

        # ========================================
        # 中间列：处理区 (35%)
        # ========================================
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(5, 5, 5, 5)
        mid_layout.setSpacing(8)

        process_title = QLabel("🔧 处理中")
        process_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        mid_layout.addWidget(process_title)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 4px;
            }
        """)
        mid_layout.addWidget(self.progress_bar)

        # 框架预览
        mid_layout.addWidget(QLabel("框架预览:"))
        self.framework_preview_edit = QPlainTextEdit()
        self.framework_preview_edit.setReadOnly(True)
        self.framework_preview_edit.setPlaceholderText("框架模板将在此显示...")
        self.framework_preview_edit.setMinimumHeight(100)
        self.framework_preview_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                background: #f8f9fa;
                font-size: 12px;
            }
        """)
        mid_layout.addWidget(self.framework_preview_edit)

        # 处理日志
        mid_layout.addWidget(QLabel("处理日志:"))
        self.process_log_edit = QPlainTextEdit()
        self.process_log_edit.setReadOnly(True)
        self.process_log_edit.setPlaceholderText("处理日志将在此显示...")
        self.process_log_edit.setMaximumHeight(80)
        self.process_log_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                background: #f8f9fa;
                font-size: 11px;
                font-family: monospace;
            }
        """)
        mid_layout.addWidget(self.process_log_edit)

        mid_layout.addStretch()

        # ========================================
        # 右侧列：输出区 (40%)
        # ========================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(8)

        output_title = QLabel("📤 输出")
        output_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        right_layout.addWidget(output_title)

        # Tab 切换输出视图
        self.output_tabs = QTabWidget()
        self.output_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                padding: 6px 12px;
                background: #f8f9fa;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
            }
        """)

        # 输出 Tab 1: 最终提示词
        final_widget = QWidget()
        final_layout = QVBoxLayout(final_widget)
        final_layout.setContentsMargins(8, 8, 8, 8)
        final_toolbar = QHBoxLayout()
        final_toolbar.addWidget(QLabel("最终提示词"))
        final_toolbar.addStretch()
        self.copy_final_btn = QToolButton()
        self.copy_final_btn.setText("📋 复制")
        self.copy_final_btn.setToolTip("复制最终提示词")
        final_toolbar.addWidget(self.copy_final_btn)
        self.save_final_btn = QToolButton()
        self.save_final_btn.setText("💾 保存")
        self.save_final_btn.setToolTip("保存为文件")
        final_toolbar.addWidget(self.save_final_btn)
        final_layout.addLayout(final_toolbar)

        self.final_preview_edit = QPlainTextEdit()
        self.final_preview_edit.setPlaceholderText("最终提示词将在此显示...")
        self.final_preview_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
        """)
        final_layout.addWidget(self.final_preview_edit)
        self.output_tabs.addTab(final_widget, "最终提示词")

        # 输出 Tab 2: 原始结果
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(8, 8, 8, 8)
        raw_toolbar = QHBoxLayout()
        raw_toolbar.addWidget(QLabel("原始结果"))
        raw_toolbar.addStretch()
        self.copy_raw_btn = QToolButton()
        self.copy_raw_btn.setText("📋 复制")
        raw_toolbar.addWidget(self.copy_raw_btn)
        raw_layout.addLayout(raw_toolbar)

        self.raw_result_edit = QPlainTextEdit()
        self.raw_result_edit.setReadOnly(True)
        self.raw_result_edit.setPlaceholderText("插件返回的原始数据将在此显示...")
        self.raw_result_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        raw_layout.addWidget(self.raw_result_edit)
        self.output_tabs.addTab(raw_widget, "原始结果")

        # 输出 Tab 3: 解析结果
        parsed_widget = QWidget()
        parsed_layout = QVBoxLayout(parsed_widget)
        parsed_layout.setContentsMargins(8, 8, 8, 8)
        parsed_toolbar = QHBoxLayout()
        parsed_toolbar.addWidget(QLabel("解析结果"))
        parsed_toolbar.addStretch()
        self.copy_parsed_btn = QToolButton()
        self.copy_parsed_btn.setText("📋 复制")
        parsed_toolbar.addWidget(self.copy_parsed_btn)
        self.export_parsed_btn = QToolButton()
        self.export_parsed_btn.setText("📤 导出")
        parsed_toolbar.addWidget(self.export_parsed_btn)
        parsed_layout.addLayout(parsed_toolbar)

        self.parsed_result_edit = QPlainTextEdit()
        self.parsed_result_edit.setReadOnly(True)
        self.parsed_result_edit.setPlaceholderText("解析后的结构化数据将在此显示...")
        self.parsed_result_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        parsed_layout.addWidget(self.parsed_result_edit)
        self.output_tabs.addTab(parsed_widget, "解析结果")

        right_layout.addWidget(self.output_tabs)

        # ========================================
        # 组装布局
        # ========================================
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(mid_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([250, 350, 400])

        tab_layout = QVBoxLayout(self.tab_request)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(main_splitter)

        # ========================================
        # 连接新增信号
        # ========================================
        self.advanced_btn.toggled.connect(self.advanced_widget.setVisible)

        # 复制按钮
        self.copy_final_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.final_preview_edit.toPlainText())
        )
        self.copy_raw_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.raw_result_edit.toPlainText())
        )
        self.copy_parsed_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.parsed_result_edit.toPlainText())
        )

        # 保存最终提示词
        self.save_final_btn.clicked.connect(self._save_final_prompt)

        # 导出解析结果
        self.export_parsed_btn.clicked.connect(self._export_parsed_result)

        # 清空按钮
        self.clear_button.clicked.connect(self._clear_request_tab)

        print("[UI] 请求台三列布局初始化完成")

    def init_workspace_tab(self):
        """初始化多文件批量处理工作台 UI 布局"""
        workspace_layout = QVBoxLayout(self.tab_workspace)
        workspace_layout.setContentsMargins(8, 8, 8, 8)

        # 1. 顶部操作区
        top_layout = QHBoxLayout()

        self.dir_path_input = QLineEdit()
        self.dir_path_input.setPlaceholderText("请选择或输入要处理的项目文件夹路径...")
        top_layout.addWidget(self.dir_path_input, stretch=3)

        self.select_dir_btn = QPushButton("选择文件夹")
        top_layout.addWidget(self.select_dir_btn, stretch=1)

        top_layout.addWidget(QLabel("过滤后缀:"))
        self.exclude_ext_input = QLineEdit(".pyc, .png, .jpg, .log, .git, .zip")
        self.exclude_ext_input.setToolTip("多个后缀以英文逗号分隔")
        top_layout.addWidget(self.exclude_ext_input, stretch=2)

        self.exclude_empty_cb = QCheckBox("过滤空文件")
        self.exclude_empty_cb.setChecked(True)
        top_layout.addWidget(self.exclude_empty_cb)

        self.scan_btn = QPushButton("扫描文件")
        self.scan_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        top_layout.addWidget(self.scan_btn, stretch=1)

        workspace_layout.addLayout(top_layout)

        # 2. 中部内容展示区
        content_splitter = QSplitter(Qt.Horizontal, self.tab_workspace)

        # 左侧：文件列表
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("扫描到的文件及 AI 核对状态："))

        self.file_table = QTableWidget(0, 3)
        self.file_table.setHorizontalHeaderLabels(["文件路径", "大小", "AI核对状态"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        left_layout.addWidget(self.file_table)

        content_splitter.addWidget(left_container)

        # 右侧：预览
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("文件内容预览："))
        self.file_preview_edit = QPlainTextEdit()
        self.file_preview_edit.setReadOnly(True)
        right_layout.addWidget(self.file_preview_edit)

        right_layout.addWidget(QLabel("AI 核对与对账反馈日志："))
        self.audit_log_edit = QPlainTextEdit()
        self.audit_log_edit.setReadOnly(True)
        right_layout.addWidget(self.audit_log_edit)

        content_splitter.addWidget(right_container)
        content_splitter.setSizes([550, 650])

        workspace_layout.addWidget(content_splitter)

        # 3. 底部操作栏
        bottom_layout = QHBoxLayout()

        self.batch_send_btn = QPushButton("一键批量提交给插件/AI")
        self.batch_send_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        bottom_layout.addWidget(self.batch_send_btn)

        self.clear_workspace_btn = QPushButton("清空工作台")
        bottom_layout.addWidget(self.clear_workspace_btn)

        workspace_layout.addLayout(bottom_layout)

    def bind_signals(self):
        """绑定 UI 控件信号"""
        self.send_button.clicked.connect(self.on_send_clicked)
        self.framework_combo.currentTextChanged.connect(self.on_framework_changed)

        self.select_dir_btn.clicked.connect(self.on_select_directory_clicked)
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        self.batch_send_btn.clicked.connect(self.on_batch_send_clicked)
        self.clear_workspace_btn.clicked.connect(self.on_clear_workspace_clicked)
        self.file_table.itemSelectionChanged.connect(self.on_file_selection_changed)

        # 清空请求台（已通过 clear_button 连接）
        # 所有复制/保存/导出按钮已在 init_request_tab 中连接

        # 高级设置折叠（已在 init_request_tab 中连接）
        # 框架预览更新（通过 controller 处理）

    # ========================================
    # 请求台事件处理
    # ========================================

    def on_send_clicked(self):
        raw_text = self.input_edit.toPlainText()
        framework = self.framework_combo.currentText()
        self.process_log_edit.clear()
        self.process_log_edit.appendPlainText("[系统] 开始处理请求...")
        self.controller.handle_send_request(raw_text, framework)

    def on_framework_changed(self, framework_name: str):
        self.controller.handle_framework_change(framework_name)
        self.framework_preview_edit.setPlainText(f"[{framework_name}] 对应的模板预览加载中...")

    # ========================================
    # 工作台事件处理
    # ========================================

    def on_select_directory_clicked(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目文件夹", "")
        if dir_path:
            self.dir_path_input.setText(dir_path)

    def on_scan_clicked(self):
        dir_path = self.dir_path_input.text().strip()
        exclude_exts = self.exclude_ext_input.text().strip()
        exclude_empty = self.exclude_empty_cb.isChecked()

        if not dir_path:
            self.audit_log_edit.appendPlainText("[系统警告] 请先选择或输入有效的文件夹路径！")
            return
        self.audit_log_edit.clear()
        self.audit_log_edit.appendPlainText(f"[系统] 开始扫描目录: {dir_path} (过滤空文件: {exclude_empty}) ...")

        self.controller.request_scan_workspace(dir_path, exclude_exts, exclude_empty)

    def on_batch_send_clicked(self):
        self.audit_log_edit.appendPlainText("[系统] 触发一键批量提交...")

    def on_clear_workspace_clicked(self):
        self.file_table.setRowCount(0)
        self.file_preview_edit.clear()
        self.audit_log_edit.clear()

    def on_file_selection_changed(self):
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            return
        row = self.file_table.row(selected_items[0])
        path_item = self.file_table.item(row, 0)
        if path_item:
            file_content = path_item.data(Qt.UserRole)
            self.file_preview_edit.setPlainText(file_content)

    # ========================================
    # 辅助方法
    # ========================================

    def _save_final_prompt(self):
        """保存最终提示词为文本文件"""
        content = self.final_preview_edit.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "没有内容可以保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存最终提示词", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_bar.showMessage(f"✅ 已保存: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def _export_parsed_result(self):
        """导出解析结果为 JSON 或文本"""
        content = self.parsed_result_edit.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, "提示", "没有内容可以导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出解析结果", "", "JSON文件 (*.json);;文本文件 (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_bar.showMessage(f"✅ 已导出: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def _clear_request_tab(self):
        """清空请求台所有输入/输出"""
        self.input_edit.clear()
        self.framework_preview_edit.clear()
        self.raw_result_edit.clear()
        self.final_preview_edit.clear()
        self.parsed_result_edit.clear()
        self.process_log_edit.clear()
        self.progress_bar.setValue(0)
        self.status_indicator.setText("⚪ 就绪")
        self.status_indicator.setStyleSheet("color: #7f8c8d;")
        self.status_bar.showMessage("🔄 已清空请求台")

    # ========================================
    # 视图更新接口（供 Controller 调用）
    # ========================================

    def update_results(self, final_prompt: str, parsed_result: str):
        self.final_preview_edit.setPlainText(final_prompt)
        self.parsed_result_edit.setPlainText(parsed_result)

    def update_server_status(self, is_running: bool, port: int, error: str):
        if is_running:
            self.status_bar.showMessage(f"本地 WebSocket 服务已成功开启 (端口: {port})")
        else:
            self.status_bar.showMessage(f"本地 WebSocket 服务启动失败 (端口: {port}): {error}")

    def update_client_status(self, state: str):
        if state == "connected":
            self.connection_label.setText("插件已链接")
            self.connection_label.setStyleSheet("color: green; background: transparent;")
        elif state == "disconnected":
            self.connection_label.setText("插件断开")
            self.connection_label.setStyleSheet("color: red; background: transparent;")
        else:
            self.connection_label.setText("插件未连接")
            self.connection_label.setStyleSheet("color: red; background: transparent;")

    def update_plugin_received_results(self, raw_result: str, parsed_result: str):
        self.raw_result_edit.setPlainText(raw_result)
        self.parsed_result_edit.setPlainText(parsed_result)

    def update_workspace_scanned_files(self, success: bool, message: str, file_list: list):
        self.audit_log_edit.appendPlainText(f"[系统] {message}")
        self.file_table.setRowCount(0)

        if not success:
            return

        self.file_table.setRowCount(len(file_list))
        for row, file_info in enumerate(file_list):
            rel_path = file_info.get("rel_path", "")
            size = file_info.get("size", 0)
            content = file_info.get("content", "")

            item_path = QTableWidgetItem(rel_path)
            item_path.setData(Qt.UserRole, content)
            self.file_table.setItem(row, 0, item_path)

            size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} 字节"
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.file_table.setItem(row, 1, item_size)

            item_status = QTableWidgetItem("待发送")
            item_status.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            item_status.setForeground(Qt.gray)
            self.file_table.setItem(row, 2, item_status)

    def update_progress(self, percent: int, status: str):
        """更新进度条和状态指示器"""
        self.progress_bar.setValue(percent)
        if percent >= 100:
            self.status_indicator.setText("✅ 处理完成")
            self.status_indicator.setStyleSheet("color: #27ae60;")
        else:
            self.status_indicator.setText(f"🔄 {status}")
            self.status_indicator.setStyleSheet("color: #f39c12;")
        # 同时更新日志
        if status:
            self.process_log_edit.appendPlainText(f"[进度] {status} ({percent}%)")

    # ========================================
    # 窗口辅助方法
    # ========================================

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.85)
        height = int(screen.height() * 0.85)
        self.resize(width, height)

        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        self.move(x, y)