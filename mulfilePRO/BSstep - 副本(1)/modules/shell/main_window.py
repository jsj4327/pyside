# modules/shell/main_window.py
import sys
from PySide2.QtCore import Qt
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
    QCheckBox
)
from modules.shell.application.shell_controller import ShellController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BigShrimp - 多模块工作台")
        
        # 实例化应用层控制器，解耦业务逻辑
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

        # --- Tab 1: 请求台 ---
        self.tab_request = QWidget()
        self.init_request_tab()
        self.tab_widget.addTab(self.tab_request, "请求台")

        # --- Tab 2: 多文件批量处理工作台 ---
        self.tab_workspace = QWidget()
        self.init_workspace_tab()
        self.tab_widget.addTab(self.tab_workspace, "批量工作台")

    def init_request_tab(self):
        main_splitter = QSplitter(Qt.Horizontal, self.tab_request)
        
        # --- 左侧列 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        left_layout.addWidget(QLabel("原始提示词："))
        self.input_edit = QPlainTextEdit()
        left_layout.addWidget(self.input_edit)

        left_layout.addWidget(QLabel("提示词处理框架（下拉选择）："))
        self.framework_combo = QComboBox()
        self.framework_combo.addItems(["默认框架", "框架选项A", "框架选项B"])
        left_layout.addWidget(self.framework_combo)

        left_layout.addWidget(QLabel("框架预览："))
        self.framework_preview_edit = QPlainTextEdit()
        left_layout.addWidget(self.framework_preview_edit)

        left_layout.addWidget(QLabel("反馈结果："))
        self.raw_result_edit = QPlainTextEdit()
        left_layout.addWidget(self.raw_result_edit)

        # --- 右侧列 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        right_layout.addWidget(QLabel("最终提示词"))
        self.final_preview_edit = QPlainTextEdit()
        right_layout.addWidget(self.final_preview_edit)

        self.send_button = QPushButton("发送请求")
        right_layout.addWidget(self.send_button)

        right_layout.addWidget(QLabel("结果解析："))
        self.parsed_result_edit = QPlainTextEdit()
        right_layout.addWidget(self.parsed_result_edit)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([600, 600])

        tab_layout = QVBoxLayout(self.tab_request)
        tab_layout.addWidget(main_splitter)

    def init_workspace_tab(self):
        """初始化多文件批量处理工作台 UI 布局"""
        workspace_layout = QVBoxLayout(self.tab_workspace)
        workspace_layout.setContentsMargins(8, 8, 8, 8)

        # 1. 顶部操作区：选择文件夹、过滤后缀、过滤空文件勾选框、扫描按钮
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

        # 新增：过滤空文件复选框（默认勾选）
        self.exclude_empty_cb = QCheckBox("过滤空文件")
        self.exclude_empty_cb.setChecked(True)
        top_layout.addWidget(self.exclude_empty_cb)

        self.scan_btn = QPushButton("扫描文件")
        self.scan_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        top_layout.addWidget(self.scan_btn, stretch=1)

        workspace_layout.addLayout(top_layout)

        # 2. 中部内容展示区：左右分栏 (左侧文件树/表格列表，右侧文本预览)
        content_splitter = QSplitter(Qt.Horizontal, self.tab_workspace)

        # 左侧：文件列表与核对状态表
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

        # 右侧：选中文件的内容预览与核对反馈区
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

        # 3. 底部操作栏：批量提交与逐一核对控制
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

    def on_send_clicked(self):
        raw_text = self.input_edit.toPlainText()
        framework = self.framework_combo.currentText()
        self.parsed_result_edit.setPlainText("正在发送至 Agent 核心处理...")
        self.controller.handle_send_request(raw_text, framework)

    def on_framework_changed(self, framework_name: str):
        self.controller.handle_framework_change(framework_name)
        self.framework_preview_edit.setPlainText(f"[{framework_name}] 对应的模板预览加载中...")

    def on_select_directory_clicked(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目文件夹", "")
        if dir_path:
            self.dir_path_input.setText(dir_path)

    def on_scan_clicked(self):
        dir_path = self.dir_path_input.text().strip()
        exclude_exts = self.exclude_ext_input.text().strip()
        exclude_empty = self.exclude_empty_cb.isChecked()  # 获取复选框状态
        
        if not dir_path:
            self.audit_log_edit.appendPlainText("[系统警告] 请先选择或输入有效的文件夹路径！")
            return
        self.audit_log_edit.clear()
        self.audit_log_edit.appendPlainText(f"[系统] 开始扫描目录: {dir_path} (过滤空文件: {exclude_empty}) ...")
        
        # 调动控制器发起扫描，带上 exclude_empty 参数
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

    # --- 纯视图更新接口供 Controller 调用 ---

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

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.85)
        height = int(screen.height() * 0.85)
        self.resize(width, height)
        
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        self.move(x, y)