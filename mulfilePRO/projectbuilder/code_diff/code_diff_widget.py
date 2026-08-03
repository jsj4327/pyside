# code_diff/code_diff_widget.py
"""
代码差异比较器主控件
"""

import os
import shutil
from typing import Optional

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QLabel, QPushButton, QFileDialog,
    QMessageBox, QApplication, QCheckBox, QGroupBox,
    QLineEdit, QProgressBar
)
from PySide2.QtCore import Qt, QTimer, Signal, QEvent
from PySide2.QtGui import QKeyEvent

from .diff_model import DiffModel
from .diff_worker import DiffWorker
from .diff_viewer import DiffViewer


class CodeDiff(QWidget):
    """代码差异比较器主控件"""

    compare_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[DiffWorker] = None
        self._model: Optional[DiffModel] = None

        self._setup_ui()
        self._load_sample_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # ==========================================
        # 输入源：与左侧控件放在一行
        # ==========================================
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        # 左侧标签 + 路径显示（合并在一行）
        left_label = QLabel("左侧:")
        left_label.setStyleSheet("color: #1a73e8; font-weight: bold;")
        input_layout.addWidget(left_label)

        self.left_path_display = QLineEdit()
        self.left_path_display.setReadOnly(True)
        self.left_path_display.setPlaceholderText("从文件浏览器双击文件传入")
        self.left_path_display.setStyleSheet("background: #f0f4ff; border: 1px solid #d0d0d0; border-radius: 3px; padding: 2px 5px;")
        input_layout.addWidget(self.left_path_display, 1)

        # 分隔符
        sep_label = QLabel(" | ")
        sep_label.setStyleSheet("color: #999;")
        input_layout.addWidget(sep_label)

        # 右侧标签 + 状态
        right_label = QLabel("右侧:")
        right_label.setStyleSheet("color: #d93025; font-weight: bold;")
        input_layout.addWidget(right_label)

        self.right_status_display = QLineEdit()
        self.right_status_display.setReadOnly(True)
        self.right_status_display.setPlaceholderText("粘贴内容 (Ctrl+V)")
        self.right_status_display.setStyleSheet("background: #fff0f0; border: 1px solid #d0d0d0; border-radius: 3px; padding: 2px 5px;")
        input_layout.addWidget(self.right_status_display, 1)

        # 粘贴按钮
        self.btn_paste = QPushButton("📋 粘贴")
        self.btn_paste.setToolTip("从剪贴板粘贴到右侧 (Ctrl+V)")
        self.btn_paste.clicked.connect(self._paste_from_clipboard)
        input_layout.addWidget(self.btn_paste)

        layout.addLayout(input_layout)

        # ==========================================
        # 差异查看器
        # ==========================================
        self.viewer = DiffViewer()
        
        # 【关键修复】使用 .connect() 正确绑定信号到 CodeDiff 的比对方法
        self.viewer.compare_requested.connect(self._perform_compare)
        
        layout.addWidget(self.viewer, 1)

        # 连接状态变化信号
        self.viewer.right_content_changed.connect(self._on_right_content_changed)
        self.viewer.left_content_changed.connect(self._on_left_content_changed)

        # 初始状态
        self.viewer.status_bar.showMessage("就绪 | 从文件浏览器双击文件传入左侧")

    def _on_left_content_changed(self, file_path: str):
        """左侧内容变化"""
        if file_path:
            self.left_path_display.setText(os.path.basename(file_path))
        else:
            self.left_path_display.clear()

    def _on_right_content_changed(self, has_content: bool):
        """右侧内容变化"""
        if has_content:
            self.right_status_display.setText("已粘贴内容")
            self.right_status_display.setStyleSheet("background: #e8f5e9; border: 1px solid #81c784; border-radius: 3px; padding: 2px 5px;")
        else:
            self.right_status_display.clear()
            self.right_status_display.setStyleSheet("background: #fff0f0; border: 1px solid #d0d0d0; border-radius: 3px; padding: 2px 5px;")

    def _paste_from_clipboard(self):
        """从剪贴板粘贴到右侧"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.viewer.set_right_content(text)
            self.viewer.right_label.setText("📋 剪贴板内容")
            self.right_status_display.setText("已粘贴内容 (Ctrl+V)")
            self.viewer.status_bar.showMessage(f"📋 已粘贴 {len(text)} 个字符")
            # 自动比对
            QTimer.singleShot(100, self._perform_compare)

    # ==========================================
    # 外部接口
    # ==========================================
    def load_left_file(self, file_path: str):
        """从文件加载左侧内容（供文件浏览器调用）"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            self.viewer.set_left_content(content, file_path)
            self.left_path_display.setText(os.path.basename(file_path))
            self.viewer.status_bar.showMessage(f"✅ 已加载: {os.path.basename(file_path)}")

            # 自动比对
            QTimer.singleShot(100, self._perform_compare)
            return True
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件:\n{str(e)}")
            return False

    def set_right_content(self, content: str):
        """设置右侧内容"""
        self.viewer.set_right_content(content)
        self.right_status_display.setText("已粘贴内容")

    def get_model(self) -> Optional[DiffModel]:
        return self._model

    # ==========================================
    # 比对功能
    # ==========================================
    def _perform_compare(self):
        """执行比对"""
        
        # 比对功能的是否执行测试
        # QMessageBox.warning(self, "警告标题", "警告内容")
        left_content = self.viewer.left_editor.toPlainText()
        right_content = self.viewer.right_editor.toPlainText()

        if not left_content.strip() or not right_content.strip():
            self.viewer.status_bar.showMessage("⚠️ 请确保左右两侧都有内容")
            return

        # 检查 diff 命令是否可用
        if not shutil.which('diff'):
            QMessageBox.warning(
                self, 
                "diff 命令未找到",
                "系统中未找到 diff 命令。\n"
                "请确保系统安装了 diffutils 工具包。\n"
                "在 Ubuntu/Debian 上运行: sudo apt install diffutils"
            )
            return

        # 添加运行提示
        self.viewer.btn_compare.setEnabled(False)
        self.viewer.btn_compare.setText("⏳ 比对中...")
        self.viewer.btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:disabled {
                background-color: #ffb74d;
                color: white;
            }
        """)
        self.viewer.status_bar.showMessage("⏳ 正在比对代码，请稍候...")

        # 获取选项
        options = self.viewer.get_compare_options()

        # 启动工作线程
        self._worker = DiffWorker(
            left_content, right_content,
            options['ignore_space'],
            options['ignore_case'],
            options['ignore_blank']
        )
        self._worker.finished.connect(self._on_compare_finished)
        self._worker.progress.connect(self._on_compare_progress)
        self._worker.error.connect(self._on_compare_error)
        self._worker.start()

    def _on_compare_progress(self, value: int):
        """比对进度更新"""
        self.viewer.status_bar.showMessage(f"⏳ 正在比对... {value}%")

    def _on_compare_finished(self, model: DiffModel):
        """比对完成"""
        self._model = model
        self.viewer.display_model(model)
        self.compare_finished.emit(model)

        # 恢复按钮状态
        self.viewer.btn_compare.setEnabled(True)
        self.viewer.btn_compare.setText("🔄 比对")
        self.viewer.btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
                color: #e8f5e9;
            }
        """)

        if model and model.is_processed:
            stats = model.statistics
            self.viewer.status_bar.showMessage(
                f"✅ 比对完成 | 相似度: {stats.similarity:.1f}% | "
                f"新增: {stats.inserted} | 删除: {stats.deleted} | 修改: {stats.modified}"
            )
        else:
            self.viewer.status_bar.showMessage("✅ 比对完成")

        self._worker = None

    def _on_compare_error(self, error_msg: str):
        """比对错误"""
        QMessageBox.warning(self, "比对错误", error_msg)

        # 恢复按钮状态
        self.viewer.btn_compare.setEnabled(True)
        self.viewer.btn_compare.setText("🔄 比对")
        self.viewer.btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
                color: #e8f5e9;
            }
        """)
        self.viewer.status_bar.showMessage(f"❌ 比对错误: {error_msg}")
        self._worker = None

    # ==========================================
    # 示例数据
    # ==========================================
    def _load_sample_data(self):
        """加载示例数据"""
        sample_left = '''def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print("Hello World")'''

        sample_right = '''def factorial(n):
    """计算阶乘（递归实现）"""
    if n == 0:
        return 1
    return n * factorial(n - 1)

def fibonacci_iterative(n):
    """计算斐波那契数列（迭代版本）"""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print("Hello, World!")'''

        self.viewer.set_left_content(sample_left, "示例_v1.py")
        self.left_path_display.setText("示例_v1.py")
        self.viewer.set_right_content(sample_right)
        self.right_status_display.setText("示例_v2")
        self.viewer.right_label.setText("📝 示例_v2")

        QTimer.singleShot(200, self._perform_compare)