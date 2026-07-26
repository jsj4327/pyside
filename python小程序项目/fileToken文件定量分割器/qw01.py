import sys
import os
import re
import tiktoken
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QFileDialog, QTreeView, 
                               QTextEdit, QLabel, QCheckBox, QFileSystemModel, 
                               QMessageBox, QSpinBox)
from PySide2.QtCore import Qt

class TokenSplitterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本 Token 智能分卷工具 v4.0 (布局重构版)")
        self.resize(900, 750)
        
        # 初始化 Tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", f"无法加载 tiktoken: {e}")
            sys.exit(1)

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 文件夹选择
        folder_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_open_folder.clicked.connect(self.open_folder)
        self.lbl_path = QLabel("未选择文件夹")
        folder_layout.addWidget(self.btn_open_folder)
        folder_layout.addWidget(self.lbl_path, 1)
        main_layout.addLayout(folder_layout)

        # 【核心重构】Token设置与开关直接放在程序最顶部，采用纯水平布局，绝不嵌套
        top_settings_layout = QHBoxLayout()
        
        # Token 输入框
        top_settings_layout.addWidget(QLabel("Token上限:"))
        self.spin_token_limit = QSpinBox()
        self.spin_token_limit.setRange(100, 1000000)
        self.spin_token_limit.setValue(4000)
        self.spin_token_limit.setSingleStep(500)
        self.spin_token_limit.setMinimumWidth(120)
        self.spin_token_limit.setStyleSheet("background-color: #e3f2fd; border: 1px solid #90caf9; padding: 2px;")
        top_settings_layout.addWidget(self.spin_token_limit)

        # 开关选项
        self.chk_recursive = QCheckBox("递归子文件夹")
        self.chk_recursive.setChecked(True)
        top_settings_layout.addWidget(self.chk_recursive)

        self.chk_filter = QCheckBox("过滤注释空行")
        self.chk_filter.setChecked(True)
        top_settings_layout.addWidget(self.chk_filter)

        # 直接添加到主布局顶部
        main_layout.addLayout(top_settings_layout) 

        # 2. 目录树
        self.tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setReadOnly(True)
        self.tree_view.setModel(self.file_model)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3) 
        main_layout.addWidget(self.tree_view, 2)

        # 3. 执行按钮
        self.btn_run = QPushButton("开始处理并导出 TXT")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_run.clicked.connect(self.process_files)
        main_layout.addWidget(self.btn_run)

        # 4. 运行日志
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(100)
        self.txt_log.setPlaceholderText("运行日志...")
        main_layout.addWidget(self.txt_log, 1)

        # 5. 处理详情
        detail_layout = QHBoxLayout()
        self.lbl_file_count = QLabel("已处理文件数: 0")
        self.lbl_file_count.setStyleSheet("font-weight: bold; color: #1976D2;")
        detail_layout.addWidget(self.lbl_file_count)
        
        self.txt_file_details = QTextEdit()
        self.txt_file_details.setReadOnly(True)
        self.txt_file_details.setPlaceholderText("成功处理的文件列表将显示在这里...")
        detail_layout.addWidget(self.txt_file_details, 1)
        main_layout.addLayout(detail_layout, 2)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.file_model.setRootPath(folder)
            self.tree_view.setRootIndex(self.file_model.index(folder))
            self.lbl_path.setText(folder)
            self.log(f"已选择文件夹: {folder}")

    def log(self, message):
        self.txt_log.append(message)
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clean_code(self, text):
        """过滤注释和空行"""
        if not self.chk_filter.isChecked():
            return text
        text = re.sub(r'^\s*(//|#).*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        text = re.sub(r'^\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def process_files(self):
        root_path = self.lbl_path.text()
        if root_path == "未选择文件夹":
            QMessageBox.warning(self, "提示", "请先打开一个文件夹！")
            return

        token_limit = self.spin_token_limit.value()
        recursive = self.chk_recursive.isChecked()
        
        self.log(f"--- 开始处理 (限制: {token_limit} tokens, 递归: {recursive}, 过滤: {self.chk_filter.isChecked()}) ---")
        
        self.txt_file_details.clear()
        self.lbl_file_count.setText("已处理文件数: 0")
        
        files_to_process = []
        if recursive:
            for dirpath, _, filenames in os.walk(root_path):
                for filename in filenames:
                    files_to_process.append(os.path.join(dirpath, filename))
        else:
            for item in os.listdir(root_path):
                full_path = os.path.join(root_path, item)
                if os.path.isfile(full_path):
                    files_to_process.append(full_path)

        if not files_to_process:
            self.log("未在指定目录下找到文件。")
            return

        output_dir = os.path.join(root_path, "TokenSplit_Output")
        os.makedirs(output_dir, exist_ok=True)
        
        current_part = 1
        current_content = ""
        total_files_processed = 0
        separator = "\n\n" + "="*50 + "\n[FILE SEPARATOR]\n" + "="*50 + "\n\n"

        for file_path in files_to_process:
            try:
                content = None
                for encoding in ['utf-8', 'gbk', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    self.log(f"[跳过] 无法解码文件: {file_path}")
                    continue

                cleaned_content = self.clean_code(content)
                if not cleaned_content:
                    continue

                file_header = f"[SOURCE FILE]: {os.path.relpath(file_path, root_path)}\n"
                block = file_header + cleaned_content + separator
                block_tokens = len(self.tokenizer.encode(block))
                
                if len(self.tokenizer.encode(current_content)) + block_tokens > token_limit and current_content:
                    save_path = os.path.join(output_dir, f"output_part_{current_part}.txt")
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(current_content.strip())
                    self.log(f"[保存] {save_path} (Tokens: ~{len(self.tokenizer.encode(current_content))})")
                    current_part += 1
                    current_content = ""

                current_content += block
                total_files_processed += 1
                
                self.lbl_file_count.setText(f"已处理文件数: {total_files_processed}")
                self.txt_file_details.append(file_path)

            except Exception as e:
                self.log(f"[错误] 处理文件 {file_path} 时发生异常: {e}")

        if current_content.strip():
            save_path = os.path.join(output_dir, f"output_part_{current_part}.txt")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(current_content.strip())
            self.log(f"[保存] {save_path} (Tokens: ~{len(self.tokenizer.encode(current_content))})")

        self.log(f"--- 处理完成！共处理 {total_files_processed} 个文件，生成 {current_part} 个 TXT 文档 ---\n")
        QMessageBox.information(self, "完成", f"处理完成！\n共处理 {total_files_processed} 个文件。\n结果已保存至:\n{output_dir}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TokenSplitterApp()
    window.show()
    sys.exit(app.exec_())
