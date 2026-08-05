# -*- coding:utf-8 -*-
import os
import json
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QSpinBox, QTextEdit, QFileDialog,
    QMessageBox, QGroupBox, QCheckBox, QProgressBar,
    QSplitter, QTreeView, QFileSystemModel, QHeaderView
)
from PySide2.QtCore import Qt, QDir, QTimer
from core import FileAnalyzer

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

class TokenManagerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file_path = None
        self.file_content = ""
        self.total_tokens = 0
        self.chunks = []  # 存储拆分后的文本块
        self.history = []  # 历史浏览目录列表
        self.history_index = -1  # 当前在历史中的位置
        self.init_ui()
        self.bind_signals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 创建水平分割器（左侧文件树，右侧功能面板）
        splitter = QSplitter(Qt.Horizontal)

        # ----- 左侧：文件树 -----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("📁 文件浏览器"))

        # ---- 工具栏：返回上一层 + 后退 ----
        toolbar = QHBoxLayout()
        self.btn_up = QPushButton("⬆ 上一层")
        self.btn_back = QPushButton("↩ 后退")
        self.btn_back.setEnabled(False)  # 初始无历史
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.btn_back)
        toolbar.addStretch()
        left_layout.addLayout(toolbar)

        # 文件树
        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath(QDir.homePath())
        self.tree_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setRootIndex(self.tree_model.index(QDir.homePath()))
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setSortingEnabled(True)
        left_layout.addWidget(self.tree_view)
        splitter.addWidget(left_widget)

        # ----- 右侧：功能面板 -----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        # 文件选择区域（保留浏览按钮）
        file_group = QGroupBox("选择文件")
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择要检测的文件...")
        self.btn_browse = QPushButton("浏览")
        file_layout.addWidget(self.file_path_edit, 1)
        file_layout.addWidget(self.btn_browse)
        file_group.setLayout(file_layout)
        right_layout.addWidget(file_group)

        # Token统计显示
        stats_group = QGroupBox("Token统计")
        stats_layout = QVBoxLayout()
        self.lbl_total_tokens = QLabel("总Token数: 0")
        self.lbl_chars = QLabel("字符数: 0")
        stats_layout.addWidget(self.lbl_total_tokens)
        stats_layout.addWidget(self.lbl_chars)
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)

        # 拆分设置
        split_group = QGroupBox("拆分设置")
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel("每块最大Token数:"))
        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(100, 100000)
        self.spin_max_tokens.setValue(2000)
        self.spin_max_tokens.setSingleStep(100)
        split_layout.addWidget(self.spin_max_tokens)
        split_group.setLayout(split_layout)
        right_layout.addWidget(split_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_calc = QPushButton("计算Token")
        self.btn_split = QPushButton("拆分")
        self.btn_save = QPushButton("保存拆分结果")
        self.btn_send_batch = QPushButton("分批次发送给AI")
        btn_layout.addWidget(self.btn_calc)
        btn_layout.addWidget(self.btn_split)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_send_batch)
        right_layout.addLayout(btn_layout)

        # 结果显示区域
        result_group = QGroupBox("拆分结果")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        right_layout.addWidget(result_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # 状态栏消息
        self.status_label = QLabel("就绪")
        right_layout.addWidget(self.status_label)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])  # 左侧树占300，右侧占700

        main_layout.addWidget(splitter)

        # 初始禁用按钮
        self.btn_split.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_send_batch.setEnabled(False)

        if not TIKTOKEN_AVAILABLE:
            self.status_label.setText("⚠️ tiktoken未安装，将使用字符估算（不精确）")

        # 初始目录设为用户主目录
        self.set_current_dir(QDir.homePath())

    def set_current_dir(self, path):
        """设置当前目录，并记录历史"""
        if not os.path.isdir(path):
            return
        # 如果历史记录为空，或当前目录与最后一个记录不同，则入栈
        if not self.history or self.history[-1] != path:
            # 如果当前不是历史末尾（即处于后退状态），则截断后面
            if self.history_index != -1 and self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        self.tree_view.setRootIndex(self.tree_model.index(path))
        self.update_back_button()

    def update_back_button(self):
        """更新后退按钮状态"""
        self.btn_back.setEnabled(self.history_index > 0)

    def on_up_clicked(self):
        """返回上一层"""
        current_path = self.tree_model.filePath(self.tree_view.rootIndex())
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and os.path.exists(parent_path):
            self.set_current_dir(parent_path)

    def on_back_clicked(self):
        """后退到上一个浏览过的目录"""
        if self.history_index > 0:
            self.history_index -= 1
            prev_path = self.history[self.history_index]
            self.tree_view.setRootIndex(self.tree_model.index(prev_path))
            self.update_back_button()

    def bind_signals(self):
        self.btn_browse.clicked.connect(self.on_browse)
        self.btn_calc.clicked.connect(self.on_calc_token)
        self.btn_split.clicked.connect(self.on_split)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_send_batch.clicked.connect(self.on_send_batch)
        # 双击文件树节点
        self.tree_view.doubleClicked.connect(self.on_tree_double_click)
        # 工具栏按钮
        self.btn_up.clicked.connect(self.on_up_clicked)
        self.btn_back.clicked.connect(self.on_back_clicked)

    def on_tree_double_click(self, index):
        """双击树节点：如果是文件则加载，如果是目录则进入"""
        path = self.tree_model.filePath(index)
        if os.path.isdir(path):
            # 进入子目录
            self.set_current_dir(path)
            return
        elif os.path.isfile(path):
            # 加载文件
            self.load_file(path)

    def load_file(self, file_path):
        """加载文件并自动计算 Token"""
        try:
            self.file_content = FileAnalyzer.read_text_file(file_path)
            self.current_file_path = file_path
            self.file_path_edit.setText(file_path)
            self.lbl_chars.setText(f"字符数: {len(self.file_content)}")
            self.status_label.setText(f"已加载文件: {os.path.basename(file_path)}")
            # 自动计算 Token
            self.total_tokens = self.estimate_tokens(self.file_content)
            self.lbl_total_tokens.setText(f"总Token数: {self.total_tokens}")
            self.btn_calc.setEnabled(True)
            self.btn_split.setEnabled(True)
            self.btn_save.setEnabled(False)
            self.btn_send_batch.setEnabled(False)
            self.result_text.clear()
            self.chunks = []
            self.status_label.setText(f"文件已加载，Token数: {self.total_tokens}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取文件失败: {str(e)}")

    def on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "", "所有文件 (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def on_calc_token(self):
        if not self.file_content:
            QMessageBox.warning(self, "提示", "请先选择文件")
            return
        self.total_tokens = self.estimate_tokens(self.file_content)
        self.lbl_total_tokens.setText(f"总Token数: {self.total_tokens}")
        self.status_label.setText(f"Token计算完成: {self.total_tokens}")
        self.btn_split.setEnabled(True)

    def estimate_tokens(self, text):
        if TIKTOKEN_AVAILABLE:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(text, disallowed_special=()))
            except Exception as e:
                print(f"tiktoken error: {e}")
                # 回退到字符估算
        # 估算：中文约1.5字/token，英文约4字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def on_split(self):
        if not self.file_content:
            return
        max_tokens = self.spin_max_tokens.value()
        if max_tokens <= 0:
            QMessageBox.warning(self, "错误", "最大Token数必须大于0")
            return

        if self.total_tokens == 0:
            self.total_tokens = self.estimate_tokens(self.file_content)

        if self.total_tokens <= max_tokens:
            self.chunks = [self.file_content]
            self.result_text.setText("文件无需拆分，内容将作为单块")
            self.status_label.setText("无需拆分")
        else:
            lines = self.file_content.splitlines(keepends=True)
            chunks = []
            current_chunk = ""
            current_tokens = 0
            for line in lines:
                line_tokens = self.estimate_tokens(line)
                if current_tokens + line_tokens > max_tokens and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = line
                    current_tokens = line_tokens
                else:
                    current_chunk += line
                    current_tokens += line_tokens
            if current_chunk:
                chunks.append(current_chunk)

            self.chunks = chunks
            self.result_text.setText(f"拆分完成，共 {len(chunks)} 块")
            self.status_label.setText(f"拆分为 {len(chunks)} 块")
        self.btn_save.setEnabled(True)
        self.btn_send_batch.setEnabled(True)

    def on_save(self):
        if not self.chunks:
            QMessageBox.warning(self, "提示", "请先拆分")
            return
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not dir_path:
            return
        base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        for i, chunk in enumerate(self.chunks):
            file_name = f"{base_name}_chunk_{i+1}.txt"
            file_path = os.path.join(dir_path, file_name)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存 {file_name} 失败: {str(e)}")
                return
        QMessageBox.information(self, "成功", f"已保存 {len(self.chunks)} 个文件到 {dir_path}")
        self.status_label.setText(f"已保存 {len(self.chunks)} 个文件")

    def on_send_batch(self):
        if not self.chunks:
            QMessageBox.warning(self, "提示", "请先拆分")
            return
        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.warning(self, "错误", "Bridge 服务未启动")
            return
        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.chunks))
        self.progress_bar.setValue(0)

        self.current_chunk_index = 0
        self.send_next_chunk()

    def send_next_chunk(self):
        if self.current_chunk_index >= len(self.chunks):
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "完成", "所有块已发送")
            self.status_label.setText("所有块已发送")
            return

        chunk = self.chunks[self.current_chunk_index]
        filename = os.path.basename(self.current_file_path)
        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": f"{filename}_part_{self.current_chunk_index+1}",
            "content": chunk,
            "message": f"请分析文件部分 {self.current_chunk_index+1}/{len(self.chunks)}"
        }
        try:
            main_win = self.window()
            bridge = main_win.bridge_server
            bridge.send_to_all_clients(payload)
            self.status_label.setText(f"已发送第 {self.current_chunk_index+1} 块")
            self.progress_bar.setValue(self.current_chunk_index+1)
        except Exception as e:
            QMessageBox.critical(self, "发送失败", f"发送第 {self.current_chunk_index+1} 块失败: {str(e)}")
            self.progress_bar.setVisible(False)
            return

        self.current_chunk_index += 1
        QTimer.singleShot(500, self.send_next_chunk)