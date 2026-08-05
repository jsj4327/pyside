"""
文件内容查看对话框模块
提供带语法高亮、关键字导航和二次搜索功能的代码查看器。
"""
import os
import subprocess
import logging
from typing import Optional, Tuple

from PySide2.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QSplitter, QListWidget, QListWidgetItem, QTabWidget, QApplication
)
from PySide2.QtCore import Qt, QTimer, QSize
from PySide2.QtGui import QTextCursor, QFont

from highlighter import CodeHighlighter

logger = logging.getLogger(__name__)


class FileContentDialog(QDialog):
    """
    文件内容查看对话框
    支持语法高亮、行号显示、关键字匹配导航和Ctrl+双击二次搜索。
    """

    def __init__(self, file_path: str, target_line_num: int = 1,
                 keyword: str = "", parent=None):
        """
        初始化文件查看对话框。
        
        Args:
            file_path: 要查看的文件绝对路径
            target_line_num: 初始滚动到的目标行号
            keyword: 搜索关键字（用于高亮和导航）
            parent: 父窗口（通常为FileViewer实例）
        """
        super().__init__(parent)
        self.file_path = file_path
        self.target_line_num = target_line_num
        self.keyword = keyword
        self.parent_viewer = parent

        self.setWindowTitle(f"代码查看器 - {os.path.basename(file_path)}")
        self.resize(1250, 820)
        self.init_ui()
        self.load_file_content()

    def init_ui(self) -> None:
        """初始化对话框的用户界面。"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)

        # === 左侧：代码编辑区 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel(f"📄 路径: {self.file_path}"))

        hbox = QHBoxLayout()

        # 行号显示区
        self.line_number_edit = QTextEdit()
        self.line_number_edit.setReadOnly(True)
        self.line_number_edit.setFixedWidth(60)
        self.line_number_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_number_edit.setStyleSheet(
            "background-color: #F0F0F0; color: #888; border: none; "
            "font-family: Consolas, monospace; font-size: 13px;"
        )
        hbox.addWidget(self.line_number_edit)

        # 代码内容区
        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.content_edit.setStyleSheet(
            "background-color: #FFFFFF; color: #333; border: 1px solid #D0D0D0; "
            "font-family: Consolas, monospace; font-size: 13px;"
        )
        self.content_edit.viewport().installEventFilter(self)
        hbox.addWidget(self.content_edit)

        left_layout.addLayout(hbox, 1)
        splitter.addWidget(left_widget)

        # === 右侧：导航与二次搜索标签页 ===
        self.tab_widget = QTabWidget()
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(5, 5, 5, 5)

        self.lbl_match_count = QLabel("📊 关键字检索: 0 处")
        self.lbl_match_count.setStyleSheet("font-weight: bold; color: #E65100;")
        vbox.addWidget(self.lbl_match_count)

        # 关键字匹配导航列表
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet(
            "QListWidget::item:selected { background-color: #B2DFDB; color: #004D40; }"
        )
        self.nav_list.itemDoubleClicked.connect(self.on_nav_item_triggered)
        self.nav_list.currentItemChanged.connect(self.on_nav_item_triggered)
        vbox.addWidget(self.nav_list)

        # 二次搜索结果列表
        vbox.addWidget(QLabel("🔄 Ctrl+双击搜索结果:"))
        self.secondary_result_list = QListWidget()
        self.secondary_result_list.setStyleSheet("""
            QListWidget { background-color: #FAFAFA; }
            QListWidget::item:selected { background-color: #C8E6C9; color: #1B5E20; }
        """)
        self.secondary_result_list.itemDoubleClicked.connect(self.on_secondary_result_clicked)
        vbox.addWidget(self.secondary_result_list)

        self.tab_widget.addTab(tab, "🔍 检索命中")
        splitter.addWidget(self.tab_widget)

        main_layout.addWidget(splitter)
        splitter.setSizes([820, 430])

        # 初始化语法高亮器
        self.highlighter = CodeHighlighter(self.content_edit.document(), self.keyword)

        # 同步行号区和代码区的滚动条
        self.content_edit.verticalScrollBar().valueChanged.connect(
            self.line_number_edit.verticalScrollBar().setValue
        )
        self.line_number_edit.verticalScrollBar().valueChanged.connect(
            self.content_edit.verticalScrollBar().setValue
        )

    def eventFilter(self, obj, event) -> bool:
        """
        事件过滤器：捕获代码区的Ctrl+双击事件以触发二次搜索。
        
        Args:
            obj: 事件源对象
            event: 事件对象
            
        Returns:
            bool: 事件是否被处理
        """
        if obj == self.content_edit.viewport() and event.type() == event.MouseButtonDblClick:
            if event.modifiers() & Qt.ControlModifier:
                self.handle_ctrl_double_click(event)
                return True
        return super().eventFilter(obj, event)

    def handle_ctrl_double_click(self, event) -> None:
        """
        处理Ctrl+双击事件：提取光标下的单词并执行二次grep搜索。
        
        Args:
            event: 鼠标双击事件
        """
        cursor = self.content_edit.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        if word and self.parent_viewer:
            self.perform_secondary_grep(word)

    def perform_secondary_grep(self, word: str) -> None:
        """
        在当前项目根目录下对指定单词执行二次grep搜索。
        
        Args:
            word: 要搜索的单词
        """
        self.secondary_result_list.clear()
        self.secondary_result_list.addItem(f"⏳ 搜索 '{word}' 中...")
        QApplication.processEvents()

        try:
            result = subprocess.run(
                ['grep', '-rn', word, '.'],
                cwd=self.parent_viewer.current_root_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors='ignore'
            )

            self.secondary_result_list.clear()

            if result.stdout:
                highlight_style = (
                    f'<b style="color:#E65100;background:#FFE0B2;padding:0 2px;">{word}</b>'
                )
                for line in result.stdout.splitlines():
                    escaped = (
                        line.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                    )
                    highlighted = (
                        escaped.replace(word, highlight_style)
                        if word in escaped else escaped
                    )

                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, (line, word))
                    item.setSizeHint(QSize(0, 42))
                    self.secondary_result_list.addItem(item)

                    label = QLabel(highlighted)
                    label.setWordWrap(True)
                    label.setStyleSheet("font-family: monospace; font-size: 13px;")
                    label.setMargin(4)
                    self.secondary_result_list.setItemWidget(item, label)
            else:
                self.secondary_result_list.addItem("❌ 未找到匹配")

        except Exception as e:
            logger.exception("二次搜索执行失败")
            self.secondary_result_list.addItem(f"错误: {e}")

    def on_secondary_result_clicked(self, current: QListWidgetItem, previous=None) -> None:
        """
        双击二次搜索结果时打开对应文件。
        
        Args:
            current: 当前选中的列表项
            previous: 之前选中的列表项（未使用）
        """
        if not current:
            return

        data = current.data(Qt.UserRole)
        if isinstance(data, tuple):
            raw_line, keyword = data
        else:
            raw_line, keyword = data, ""

        if not raw_line or ":" not in raw_line:
            return

        parts = raw_line.split(":", 2)
        rel_path = parts[0]
        try:
            line_num = int(parts[1])
        except ValueError:
            line_num = 1

        abs_path = os.path.abspath(
            os.path.join(self.parent_viewer.current_root_path, rel_path)
        )

        if os.path.isfile(abs_path):
            dialog = FileContentDialog(abs_path, line_num, keyword, self.parent_viewer)
            dialog.exec_()

    def load_file_content(self) -> None:
        """加载文件内容并填充行号和导航列表。"""
        if not os.path.exists(self.file_path):
            self.content_edit.setText("文件不存在")
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            lines = content.splitlines()
            self.line_number_edit.setPlainText("\n".join(str(i + 1) for i in range(len(lines))))
            self.content_edit.setPlainText(content)
            self.populate_navigation_sidebar(lines)

            # 延迟滚动到目标行，等待布局完成
            QTimer.singleShot(80, self.initial_scroll_position)

        except Exception as e:
            logger.exception("加载文件内容失败: %s", self.file_path)
            self.content_edit.setText(str(e))

    def populate_navigation_sidebar(self, lines: list) -> None:
        """
        填充关键字匹配导航侧边栏。
        
        Args:
            lines: 文件内容按行分割的列表
        """
        self.nav_list.clear()

        if not self.keyword:
            self.lbl_match_count.setText("未指定关键字")
            return

        count = 0
        keyword_lower = self.keyword.lower()
        for i, line in enumerate(lines):
            if keyword_lower in line.lower():
                count += 1
                display_text = line.strip()[:45]
                item = QListWidgetItem(f"第{i + 1}行: {display_text}")
                item.setData(Qt.UserRole, i + 1)
                self.nav_list.addItem(item)

        self.lbl_match_count.setText(f"📊 关键字 '{self.keyword}' 检索: {count} 处")

    def initial_scroll_position(self) -> None:
        """将视图滚动到目标行位置。"""
        if self.target_line_num > 1:
            self.scroll_to_absolute_line(self.target_line_num)

    def on_nav_item_triggered(self, current: QListWidgetItem, prev=None) -> None:
        """
        导航列表项选中时滚动到对应行。
        
        Args:
            current: 当前选中的列表项
            prev: 之前选中的列表项（未使用）
        """
        if current:
            self.scroll_to_absolute_line(current.data(Qt.UserRole))

    def scroll_to_absolute_line(self, line_num: int) -> None:
        """
        将代码编辑器滚动到指定行并将其居中显示。
        
        Args:
            line_num: 目标行号（从1开始）
        """
        block = self.content_edit.document().findBlockByLineNumber(line_num - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            self.content_edit.setTextCursor(cursor)
            rect = self.content_edit.document().documentLayout().blockBoundingRect(block)
            target = int(rect.top() - self.content_edit.viewport().height() / 2)
            scrollbar = self.content_edit.verticalScrollBar()
            scrollbar.setValue(max(0, min(target, scrollbar.maximum())))
