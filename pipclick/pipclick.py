import sys
import os
import json
import urllib.request
import urllib.parse
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFileDialog, QMenu)
from PySide2.QtCore import Qt, QProcess, QThread, Signal

class PyPIQueryThread(QThread):
    """异步请求 PyPI 官方 API 获取包详细信息"""
    finished_signal = Signal(list, str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        results = []
        error_msg = ""
        try:
            url = f"https://pypi.org/pypi/{urllib.parse.quote(self.query)}/json"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                info = data.get('info', {})
                name = info.get('name', self.query)
                summary = info.get('summary', '无描述信息')
                version = info.get('version', '')
                results.append((f"{name} ({version})", summary))
        except Exception as e:
            error_msg = str(e)
            
        self.finished_signal.emit(results, error_msg)

class PipSimpleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PIP 离线下载与运维管理工具 (高级完善版)")

        self.startup_dir = os.getcwd()
        self.init_window_size_and_position(scale=0.85)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.query_thread = None
        self.init_ui()

    def init_window_size_and_position(self, scale=0.85):
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * scale)
        height = int(screen.height() * scale)
        self.resize(width, height)
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 顶端输入区域
        input_layout = QHBoxLayout()
        self.label_input = QLabel("软件包名:")
        self.input_package = QLineEdit()
        self.input_package.setPlaceholderText("输入包名，多个包用空格隔开（支持自动去重），例如: requests numpy pandas")
        input_layout.addWidget(self.label_input)
        input_layout.addWidget(self.input_package)
        main_layout.addLayout(input_layout)

        # 2. 核心与运维功能按钮区（划分为两行以保持整洁）
        btn_layout_top = QHBoxLayout()
        self.btn_info = QPushButton("1. 获取包详情")
        self.btn_download = QPushButton("2. 批量下载包及依赖 (.whl)")
        self.btn_install = QPushButton("3. 本地离线安装")
        btn_layout_top.addWidget(self.btn_info)
        btn_layout_top.addWidget(self.btn_download)
        btn_layout_top.addWidget(self.btn_install)
        main_layout.addLayout(btn_layout_top)

        btn_layout_sub = QHBoxLayout()
        self.btn_freeze = QPushButton("4. 导出当前已安装环境清单")
        self.btn_cache = QPushButton("5. 清理本地 Pip 缓存")
        btn_layout_sub.addWidget(self.btn_freeze)
        btn_layout_sub.addWidget(self.btn_cache)
        main_layout.addLayout(btn_layout_sub)

        # 3. 命令行预览与执行区
        cmd_layout = QHBoxLayout()
        self.label_cmd = QLabel("执行命令:")
        self.input_command = QLineEdit()
        self.input_command.setPlaceholderText("生成的命令将显示在此处，可直接修改...")
        self.btn_execute = QPushButton("立即执行")
        self.btn_execute.setStyleSheet("background-color: #006eb8; color: white; font-weight: bold; padding: 5px 15px;")

        cmd_layout.addWidget(self.label_cmd)
        cmd_layout.addWidget(self.input_command, 1)
        cmd_layout.addWidget(self.btn_execute)
        main_layout.addLayout(cmd_layout)

        # 4. 左右分栏视图
        splitter = QSplitter(Qt.Horizontal)

        # 左侧表格
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.label_table = QLabel("包信息概览 (点击行可自动智能追加填入上方输入框):")
        self.table_results = QTableWidget()
        self.table_results.setColumnCount(2)
        self.table_results.setHorizontalHeaderLabels(["软件包名称", "摘要描述"])
        self.table_results.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_results.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_results.setEditTriggers(QTableWidget.NoEditTriggers)
        left_layout.addWidget(self.label_table)
        left_layout.addWidget(self.table_results)

        # 右侧终端日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        log_header_layout = QHBoxLayout()
        self.label_output = QLabel("运行日志 (支持右键复制/菜单):")
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setFixedWidth(70)
        log_header_layout.addWidget(self.label_output)
        log_header_layout.addStretch()
        log_header_layout.addWidget(self.btn_clear)
        right_layout.addLayout(log_header_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            background-color: #2e3436; 
            color: #eeeeec; 
            font-family: 'Monospace', 'Consolas';
            font-size: 10pt;
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 700])
        main_layout.addWidget(splitter, 1)

        # 信号绑定
        self.btn_info.clicked.connect(self.on_info_clicked)
        self.btn_download.clicked.connect(self.generate_download_cmd)
        self.btn_install.clicked.connect(self.generate_install_cmd)
        self.btn_freeze.clicked.connect(self.generate_freeze_cmd)
        self.btn_cache.clicked.connect(self.generate_cache_cmd)
        
        self.btn_execute.clicked.connect(self.execute_command)
        self.btn_clear.clicked.connect(self.output_text.clear)
        self.table_results.cellClicked.connect(self.on_table_item_clicked)

    def append_log(self, text):
        """规范化追加日志，防止多任务输出错乱并自动滚动到底部"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.output_text.setTextCursor(cursor)
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def on_table_item_clicked(self, row, column):
        pkg_item = self.table_results.item(row, 0)
        if pkg_item:
            current_text = self.input_package.text().strip()
            new_pkg = pkg_item.text().split("(")[0].strip()
            
            # 智能去重逻辑：如果输入框已经包含了该包名则不重复追加
            pkg_list = current_text.split() if current_text else []
            if new_pkg not in pkg_list:
                pkg_list.append(new_pkg)
                self.input_package.setText(" ".join(pkg_list))

    def on_info_clicked(self):
        pkg_input = self.input_package.text().strip()
        if not pkg_input:
            self.append_log("[错误] 请先输入软件包名！\n")
            return
        
        first_pkg = pkg_input.split()[0]
        self.table_results.setRowCount(0)
        self.append_log(f"[提示] 正在获取 '{first_pkg}' 的官方详细信息...\n")
        self.input_command.setText(f"pip show {first_pkg}")

        self.query_thread = PyPIQueryThread(first_pkg)
        self.query_thread.finished_signal.connect(self.handle_query_result)
        self.query_thread.start()

    def handle_query_result(self, results, error_msg):
        if error_msg and not results:
            self.append_log(f"[提示] 在线获取失败: {error_msg}，切换为本地 pip show...\n")
            self.execute_command()
            return

        for pkg_title, desc in results:
            row = self.table_results.rowCount()
            self.table_results.insertRow(row)
            self.table_results.setItem(row, 0, QTableWidgetItem(pkg_title))
            self.table_results.setItem(row, 1, QTableWidgetItem(desc))
        self.append_log("[成功] 包信息加载完成。\n\n")

    def generate_download_cmd(self):
        pkg_names = self.input_package.text().strip()
        if not pkg_names:
            self.append_log("[错误] 请先输入要下载的软件包名！\n")
            return
        
        pkg_list = pkg_names.split()
        folder_name = f"{pkg_list[0]}_and_{len(pkg_list)-1}_others_pip" if len(pkg_list) > 1 else f"{pkg_list[0]}_pip"
        target_folder = os.path.join(self.startup_dir, folder_name)
        
        cmd = f"pip download -d {repr(target_folder)} {pkg_names}"
        self.input_command.setText(cmd)
        self.append_log(f"[提示] 已生成下载命令。文件将保存至:\n{target_folder}\n")

    def generate_install_cmd(self):
        pkg_names = self.input_package.text().strip()
        if not pkg_names:
            self.append_log("[错误] 请先输入要安装的软件包名！\n")
            return
            
        pkg_list = pkg_names.split()
        folder_name = f"{pkg_list[0]}_and_{len(pkg_list)-1}_others_pip" if len(pkg_list) > 1 else f"{pkg_list[0]}_pip"
        target_folder = os.path.join(self.startup_dir, folder_name)
        
        if not os.path.isdir(target_folder):
            selected_dir = QFileDialog.getExistingDirectory(self, "选择离线包文件夹", self.startup_dir)
            if selected_dir:
                target_folder = selected_dir
            else:
                return

        cmd = f"pip install --no-index --find-links={repr(target_folder)} {pkg_names}"
        self.input_command.setText(cmd)
        self.append_log(f"[提示] 已生成离线安装命令。\n")

    def generate_freeze_cmd(self):
        """新增：导出当前环境清单到 requirements.txt"""
        export_path = os.path.join(self.startup_dir, "requirements_exported.txt")
        cmd = f"pip freeze > {repr(export_path)}"
        self.input_command.setText(cmd)
        self.append_log(f"[提示] 已生成环境导出命令。执行后将保存至:\n{export_path}\n")

    def generate_cache_cmd(self):
        """新增：清理本地 pip 缓存命令"""
        cmd = "pip cache purge"
        self.input_command.setText(cmd)
        self.append_log(f"[提示] 已生成清理本地缓存命令。\n")

    def execute_command(self):
        cmd = self.input_command.text().strip()
        if not cmd:
            self.append_log("[错误] 命令为空！\n")
            return
        if self.process.state() == QProcess.Running:
            self.append_log("[提示] 有任务正在执行，请稍候...\n")
            return

        self.append_log(f"\n$ {cmd}\n")
        self.process.start("bash", ["-c", cmd])

    def handle_stdout(self):
        result = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.append_log(result)

    def handle_stderr(self):
        result = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log(result)

    def process_finished(self):
        self.append_log("\n")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PipSimpleApp()
    window.show()
    sys.exit(app.exec_())
