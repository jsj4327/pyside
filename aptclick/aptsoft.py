import sys
import os
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFileDialog)
from PySide2.QtCore import Qt, QProcess
from PySide2.QtGui import QIcon  # 导入 QIcon 用于设置图标

class MateStyleAptApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APT 软件包管理工具 (左右分栏表格视图)")

        # 获取程序启动文件夹路径
        self.startup_dir = os.getcwd()

        # 尝试加载当前目录下的 aptsoft.png 作为软件 Logo 图标
        logo_path = os.path.join(self.startup_dir, "aptsoft.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        # 窗口大小根据屏幕可用分辨率的 90% 动态确定并居中
        self.init_window_size_and_position(scale=0.9)

        # 初始化 QProcess 用于异步执行命令行
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        # 用于收集搜索过程中的完整输出文本和分页控制
        self.search_output_buffer = ""
        self.is_searching = False
        self.search_offset = 0  # 分页偏移量记录
        self.page_size = 100    # 每页显示的行数

        self.init_ui()

    def init_window_size_and_position(self, scale=0.9):
        """根据屏幕可用分辨率的百分比（默认90%）动态设置窗口大小并居中（自动排除任务栏）"""
        screen = QApplication.primaryScreen().availableGeometry()
        
        width = int(screen.width() * scale)
        height = int(screen.height() * scale)
        
        self.resize(width, height)
        
        x = screen.left() + (screen.width() - width) // 2
        y = screen.top() + (screen.height() - height) // 2
        
        self.move(x, y)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 顶端输入区域
        input_layout = QHBoxLayout()
        self.label_input = QLabel("软件包名称:")
        self.input_package = QLineEdit()
        self.input_package.setPlaceholderText("例如: curl git vlc (支持空格分割的多个包名批量操作)...")
        
        input_layout.addWidget(self.label_input)
        input_layout.addWidget(self.input_package)
        main_layout.addLayout(input_layout)

        # 2. 按钮操作区域
        btn_layout = QHBoxLayout()
        self.btn_search = QPushButton("1. 搜索软件包")
        self.btn_more = QPushButton("加载下 100 行")
        self.btn_more.setEnabled(False) 
        self.btn_test = QPushButton("2. 测试安装/分析依赖")
        self.btn_download = QPushButton("3. 批量下载包及依赖")
        self.btn_install = QPushButton("4. 本地安装(.deb)")

        btn_layout.addWidget(self.btn_search)
        btn_layout.addWidget(self.btn_more)
        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addWidget(self.btn_install)
        main_layout.addLayout(btn_layout)

        # 3. 命令行编辑文本框与“执行”按钮
        cmd_layout = QHBoxLayout()
        self.label_cmd = QLabel("待执行命令:")
        self.input_command = QLineEdit()
        self.input_command.setPlaceholderText("点击上方按钮生成命令，或在此直接修改命令...")
        self.btn_execute = QPushButton("执行")
        self.btn_execute.setStyleSheet("background-color: #4e9a06; color: white; font-weight: bold; padding: 5px 15px;")

        cmd_layout.addWidget(self.label_cmd)
        cmd_layout.addWidget(self.input_command, 1)
        cmd_layout.addWidget(self.btn_execute)
        main_layout.addLayout(cmd_layout)

        # 4. 左右分栏视图
        splitter = QSplitter(Qt.Horizontal)

        # --- 左侧：搜索结果表格区 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.label_table = QLabel("搜索结果列表 (点击行可自动追加填入包名):")
        self.table_results = QTableWidget()
        self.table_results.setColumnCount(2)
        self.table_results.setHorizontalHeaderLabels(["软件包名称", "描述信息"])
        self.table_results.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_results.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_results.setEditTriggers(QTableWidget.NoEditTriggers)
        
        left_layout.addWidget(self.label_table)
        left_layout.addWidget(self.table_results)

        # --- 右侧：终端输出区 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        output_header_layout = QHBoxLayout()
        self.label_output = QLabel("终端输出结果:")
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setFixedWidth(80)
        
        output_header_layout.addWidget(self.label_output)
        output_header_layout.addStretch()
        output_header_layout.addWidget(self.btn_clear)
        right_layout.addLayout(output_header_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            background-color: #2e3436; 
            color: #eeeeec; 
            font-family: 'Monospace', 'Consolas', 'Courier New';
            font-size: 10pt;
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 600])
        main_layout.addWidget(splitter, 1)

        # 绑定事件
        self.btn_search.clicked.connect(self.on_search_clicked)
        self.btn_more.clicked.connect(self.on_load_more_clicked)
        self.btn_test.clicked.connect(self.generate_test_cmd)
        self.btn_download.clicked.connect(self.generate_download_cmd)
        self.btn_install.clicked.connect(self.generate_install_cmd)
        
        self.btn_execute.clicked.connect(self.execute_command)
        self.btn_clear.clicked.connect(self.output_text.clear)
        self.table_results.cellClicked.connect(self.on_table_item_clicked)

    def on_table_item_clicked(self, row, column):
        pkg_item = self.table_results.item(row, 0)
        if pkg_item:
            current_text = self.input_package.text().strip()
            new_pkg = pkg_item.text().strip()
            # 如果当前输入框中没有这个包，就追加进去，方便批量下载
            if new_pkg not in current_text.split():
                if current_text:
                    self.input_package.setText(f"{current_text} {new_pkg}")
                else:
                    self.input_package.setText(new_pkg)

    def on_search_clicked(self):
        """点击全新搜索"""
        pkg_name = self.input_package.text().strip()
        if not pkg_name:
            self.output_text.append("[错误] 请先输入要搜索的软件包名！")
            return
        
        self.search_offset = 0
        self.table_results.setRowCount(0) # 清空旧表格
        self.execute_search_query(append_mode=False)

    def on_load_more_clicked(self):
        """点击加载下 100 行"""
        self.search_offset += self.page_size
        self.execute_search_query(append_mode=True)

    def execute_search_query(self, append_mode=False):
        pkg_name = self.input_package.text().strip()
        if not pkg_name:
            return
        
        self.is_searching = True
        self.search_output_buffer = "" 
        
        start_line = self.search_offset + 1
        end_line = self.search_offset + self.page_size
        
        if not append_mode:
            self.label_table.setText(f"搜索结果列表: 正在搜索并加载前 {self.page_size} 条...")
            self.output_text.append(f"[提示] 正在搜索 '{pkg_name}' (第 {start_line} - {end_line} 行)，请稍候...")
        else:
            self.output_text.append(f"[提示] 正在加载更多结果 (第 {start_line} - {end_line} 行)，请稍候...")

        cmd = f"apt search {pkg_name} | sed -n '{start_line},{end_line}p'"
        
        self.input_command.setText(cmd)
        self.output_text.append(f"$ {cmd}")
        self.process.start("bash", ["-c", cmd])

    def generate_test_cmd(self):
        self.is_searching = False
        pkg_names = self.input_package.text().strip()
        if not pkg_names:
            self.output_text.append("[错误] 请先输入软件包名！")
            return
        # 支持以空格分割的多个包
        cmd = f"sudo apt-get install -s {pkg_names}"
        self.input_command.setText(cmd)
        self.output_text.append(f"[提示] 已生成测试安装命令。")

    def generate_download_cmd(self):
        self.is_searching = False
        pkg_names = self.input_package.text().strip()
        if not pkg_names:
            self.output_text.append("[错误] 请先输入软件包名！")
            return
        
        # 将空格分割的包名拆解为列表，以处理多个包的情况
        pkg_list = pkg_names.split()
        if len(pkg_list) > 1:
            # 如果有多个包，智能生成组合的文件夹名称
            folder_name = f"{pkg_list[0]}_and_{len(pkg_list)-1}_others"
        else:
            folder_name = pkg_list[0]

        target_folder = os.path.join(self.startup_dir, folder_name)
        cmd = (
            f"mkdir -p {repr(target_folder)} && "
            f"sudo apt-get -o Dir::Cache::archives={repr(target_folder)} install -y --download-only {pkg_names} && "
            f"rm -rf {repr(os.path.join(target_folder, 'partial'))} {repr(os.path.join(target_folder, 'lock'))}"
        )
        
        self.input_command.setText(cmd)
        self.output_text.append(f"[提示] 已生成批量下载命令 (共 {len(pkg_list)} 个核心包)。\n下载完成后将保存在:\n{target_folder}")

    def generate_install_cmd(self):
        self.is_searching = False
        pkg_names = self.input_package.text().strip()
        
        target_folder = ""
        if pkg_names:
            # 同样适配多包和单包情况的文件夹检查逻辑
            pkg_list = pkg_names.split()
            folder_name = f"{pkg_list[0]}_and_{len(pkg_list)-1}_others" if len(pkg_list) > 1 else pkg_list[0]
            
            potential_dir = os.path.join(self.startup_dir, folder_name)
            if os.path.isdir(potential_dir):
                target_folder = potential_dir
                self.output_text.append(f"[提示] 在当前目录下找到对应的下载文件夹: {target_folder}")
        
        if not target_folder:
            self.output_text.append("[提示] 未匹配到默认的文件夹，正在弹出文件夹选择对话框...")
            selected_dir = QFileDialog.getExistingDirectory(
                self, 
                "选择包含 .deb 文件的文件夹", 
                self.startup_dir
            )
            if selected_dir:
                target_folder = selected_dir
            else:
                self.output_text.append("[取消] 用户取消了文件夹选择。")
                return

        cmd = f"sudo dpkg -i {repr(target_folder)}/*.deb || sudo apt-get install -f -y"
        self.input_command.setText(cmd)
        self.output_text.append(f"[提示] 已生成本地安装命令，目标文件夹:\n{target_folder}")

    def execute_command(self):
        command_line = self.input_command.text().strip()
        if not command_line:
            self.output_text.append("\n[错误提示] 待执行的命令为空！\n")
            return

        if self.process.state() == QProcess.Running:
            self.output_text.append("\n[提示] 当前有任务正在执行，请稍候...\n")
            return
        
        if not command_line.startswith("apt search"):
            self.is_searching = False

        self.output_text.append(f"\n$ {command_line}")
        self.process.start("bash", ["-c", command_line])

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        result = data.data().decode("utf-8", errors="ignore")

        if self.is_searching:
            self.search_output_buffer += result

        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(result)
        self.output_text.setTextCursor(cursor)
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        result = data.data().decode("utf-8", errors="ignore")
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(result)
        self.output_text.setTextCursor(cursor)
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def process_finished(self):
        if self.is_searching:
            lines = self.search_output_buffer.strip().split("\n")
            valid_count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if "/" in line and not line.startswith("正在") and not line.startswith("全文"):
                    pkg_name = line.split("/")[0].strip()
                    
                    desc = ""
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if next_line.startswith(" ") or next_line.startswith("\t"):
                            desc = next_line.strip()
                            i += 1  
                    
                    row_position = self.table_results.rowCount()
                    self.table_results.insertRow(row_position)
                    self.table_results.setItem(row_position, 0, QTableWidgetItem(pkg_name))
                    self.table_results.setItem(row_position, 1, QTableWidgetItem(desc))
                    valid_count += 1
                
                i += 1
            
            total_rows = self.table_results.rowCount()
            if valid_count > 0:
                self.label_table.setText(f"搜索结果列表 (已累计加载 {total_rows} 个软件包):")
                self.output_text.append(f"\n[提示] 本次成功解析并追加了 {valid_count} 个软件包。\n")
                self.btn_more.setEnabled(True)
            else:
                self.label_table.setText(f"搜索结果列表 (已加载完毕，共 {total_rows} 个):")
                self.output_text.append(f"\n[提示] 没有更多匹配的结果了。\n")
                self.btn_more.setEnabled(False)
        
        self.output_text.append("")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MateStyleAptApp()
    window.show()
    sys.exit(app.exec_())
