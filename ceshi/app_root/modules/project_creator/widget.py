# -*- coding:utf-8 -*-
import os
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QSplitter,
    QMessageBox, QProgressBar
)
from PySide2.QtCore import Qt, Signal, QTimer

from .prompt_builder import PromptBuilder
from .file_generator import ProjectFileGenerator
from .file_manager import FileManagerWidget


class ProjectCreatorWidget(QWidget):
    """项目创建器主控件"""
    
    ai_response_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stage = 'idle'
        self.elapsed_seconds = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)
        self._init_ui()
        self._bind_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # ---------- 主分割：左侧文件管理器 + 右侧功能区 ----------
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧面板：文件管理器 + 日志
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # 文件管理器
        self.file_manager = FileManagerWidget()
        left_layout.addWidget(self.file_manager, 3)

        # 日志输出（放到文件管理器下方）
        log_group = QGroupBox("📋 日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-size:11px;background:#f8f8f8;")
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group, 1)

        main_splitter.addWidget(left_panel)

        # 右侧：功能面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # ---------- 输入区 ----------
        input_group = QGroupBox("📝 项目需求")
        input_layout = QVBoxLayout(input_group)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText(
            "请详细描述您想要创建的项目...\n\n"
            "示例：\n"
            "创建一个Python命令行工具，用于批量重命名文件，支持正则表达式替换"
        )
        self.desc_edit.setMinimumHeight(200)
        input_layout.addWidget(self.desc_edit)

        # 按钮行
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("🚀 发送请求")
        self.btn_generate.setStyleSheet(
            "QPushButton{background:#4CAF50;color:#fff;font-weight:bold;padding:6px 20px;border-radius:4px;}"
            "QPushButton:disabled{background:#a5d6a7;}"
        )
        self.btn_generate.setFixedWidth(120)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setFixedWidth(80)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_clear)
        input_layout.addLayout(btn_layout)

        right_layout.addWidget(input_group)

        # ---------- 进度条 ----------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # ---------- 状态栏 ----------
        self.status_label = QLabel("就绪 | 选择目录后输入需求点击发送")
        self.status_label.setStyleSheet("color:#666;padding:2px 4px;border-top:1px solid #ddd;")
        right_layout.addWidget(self.status_label)

        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 600])
        layout.addWidget(main_splitter)

    def _bind_signals(self):
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_clear.clicked.connect(self._on_clear)
        self.file_manager.directory_changed.connect(self._on_directory_changed)

    def _on_directory_changed(self, path):
        """目录变化时更新状态"""
        self.status_label.setText(f"当前目录: {path}")

    def _on_generate(self):
        """发送生成请求"""
        desc = self.desc_edit.toPlainText().strip()
        if not desc:
            QMessageBox.warning(self, "提示", "请输入项目描述")
            return

        # 重置日志
        self.log_text.clear()
        self.log_text.append(f"📤 发送请求...")
        self.log_text.append(f"  描述: {desc[:80]}..." if len(desc) > 80 else f"  描述: {desc}")

        # 构建提示词
        prompt = PromptBuilder.build_initial_prompt(desc)

        # 更新状态
        self.stage = 'generating'
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("⏳ 生成中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # 启动计时器
        self.elapsed_seconds = 0
        self.timer.start(1000)
        self.status_label.setText("⏳ 新建项目请求已发送，等待插件反馈...")

        # 发送给AI
        self._send_to_ai(prompt)

    def _update_timer(self):
        """更新计时器"""
        self.elapsed_seconds += 1
        self.status_label.setText(f"⏳ 新建项目请求已发送，等待插件反馈... {self.elapsed_seconds}s")

    def _send_to_ai(self, message: str):
        """发送消息给AI"""
        main_win = self.window()
        if not main_win or not hasattr(main_win, 'bridge_server'):
            QMessageBox.critical(self, "错误", "Bridge服务未启动")
            self._reset_state()
            return

        bridge = main_win.bridge_server
        if not bridge.clients:
            QMessageBox.warning(self, "警告", "没有插件客户端连接")
            self._reset_state()
            return

        payload = {
            "type": "ANALYZE_REQUEST",
            "filename": "project_request",
            "content": message,
            "message": "项目创建请求"
        }
        try:
            bridge.send_to_all_clients(payload)
            self.log_text.append("✅ 请求已发送，等待AI响应...")
            self.progress_bar.setValue(30)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")
            self._reset_state()

    def append_ai_result(self, text):
        """接收AI响应（由主窗口调用）"""
        if self.stage != 'generating':
            return

        # 停止计时器
        self.timer.stop()
        
        self.log_text.append("📥 收到AI响应，正在解析...")
        self.progress_bar.setValue(60)

        # 解析文件列表
        files_data = ProjectFileGenerator.extract_files_from_response(text)

        if not files_data:
            self.log_text.append("❌ 未能从响应中提取文件数据")
            self.log_text.append(f"响应预览: {text[:200]}...")
            self.status_label.setText("❌ 解析AI响应失败")
            self._reset_state()
            return

        # 输出所有文件名到日志
        self.log_text.append(f"✅ 解析成功，共 {len(files_data)} 个文件")
        self.log_text.append("📄 文件列表:")
        for i, file_info in enumerate(files_data, 1):
            path = file_info.get('path', '')
            # 还原下划线转义用于显示
            display_path = path.replace('\\u005f', '_')
            self.log_text.append(f"  {i}. {display_path}")

        self.progress_bar.setValue(80)

        # 使用当前目录
        base_dir = self.file_manager.get_current_path()
        self.log_text.append(f"📁 保存位置: {base_dir}")

        # 生成文件
        self.log_text.append("📝 开始生成文件...")
        success_count, errors = ProjectFileGenerator.generate_files(files_data, base_dir)

        self.progress_bar.setValue(100)

        if errors:
            self.log_text.append(f"⚠️ 生成完成，{len(errors)} 个文件失败")
            for err in errors:
                self.log_text.append(f"  ❌ {err}")
            self.status_label.setText(f"⚠️ 生成完成，{len(errors)} 个文件失败，耗时 {self.elapsed_seconds}s")
            QMessageBox.warning(self, "完成", f"生成完成，{len(errors)} 个文件失败")
        else:
            self.log_text.append(f"✅ 成功生成 {success_count} 个文件")
            self.log_text.append(f"⏱ 总耗时: {self.elapsed_seconds} 秒")
            self.status_label.setText(f"✅ 成功生成 {success_count} 个文件，耗时 {self.elapsed_seconds}s")
            QMessageBox.information(self, "完成", f"成功生成 {success_count} 个文件到:\n{base_dir}")

        # 刷新文件管理器
        self.file_manager._refresh()
        self.stage = 'complete'
        self._reset_state()

    def _reset_state(self):
        """重置状态"""
        self.stage = 'idle'
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 发送请求")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.timer.stop()
        
        # 如果状态标签还是计时状态，重置
        if "等待插件反馈" in self.status_label.text() or "耗时" in self.status_label.text():
            self.status_label.setText("就绪")

    def _on_clear(self):
        """清空"""
        self.desc_edit.clear()
        self.log_text.clear()
        self.status_label.setText("已清空")
        self._reset_state()