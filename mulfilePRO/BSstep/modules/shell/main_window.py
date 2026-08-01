# modules/shell/main_window.py
import sys
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QComboBox,
    QPushButton,
    QSplitter,
    QStatusBar
)
from modules.shell.application.shell_controller import ShellController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BigShrimp - 请求台")
        
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

        # 创建持久化的连接状态指示标签（无底色、无图标，初始为红色未连接）
        self.connection_label = QLabel("插件未连接")
        self.connection_label.setStyleSheet("color: red; background: transparent;")
        self.status_bar.addPermanentWidget(self.connection_label)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- Tab 1: 请求台 ---
        self.tab_request = QWidget()
        self.init_request_tab()
        self.tab_widget.addTab(self.tab_request, "请求台")

        # --- Tab 2: 暂留 ---
        self.tab_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.tab_placeholder)
        placeholder_label = QLabel("暂留页面")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        self.tab_widget.addTab(self.tab_placeholder, "暂留")

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

    def bind_signals(self):
        """绑定 UI 控件信号"""
        self.send_button.clicked.connect(self.on_send_clicked)
        self.framework_combo.currentTextChanged.connect(self.on_framework_changed)

    def on_send_clicked(self):
        raw_text = self.input_edit.toPlainText()
        framework = self.framework_combo.currentText()
        self.parsed_result_edit.setPlainText("正在发送至 Agent 核心处理...")
        self.controller.handle_send_request(raw_text, framework)

    def on_framework_changed(self, framework_name: str):
        self.controller.handle_framework_change(framework_name)
        self.framework_preview_edit.setPlainText(f"[{framework_name}] 对应的模板预览加载中...")

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

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.85)
        height = int(screen.height() * 0.85)
        self.resize(width, height)
        
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        self.move(x, y)