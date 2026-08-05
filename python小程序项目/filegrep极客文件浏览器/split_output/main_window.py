"""
主窗口模块
实现文件浏览器的主界面，包含文件树视图、grep搜索功能和结果展示。
"""
import os
import re
import shlex
import subprocess
import logging
from typing import List, Optional

from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QTreeView, QFileSystemModel, QComboBox, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QSplitter, QCheckBox, QApplication
)
from PySide2.QtCore import QDir, QTimer, Qt, QSize
from PySide2.QtGui import QFont, QIcon

from config_manager import ConfigManager
from file_content_dialog import FileContentDialog

logger = logging.getLogger(__name__)


class FileViewer(QMainWindow):
    """
    极客文件浏览器主窗口
    提供文件树浏览、grep关键字搜索、命令预览与自定义等功能。
    """

    # grep帮助提示HTML
    GREP_HELP_HTML = """
    <div style="font-family: sans-serif; font-size: 13px;">
        <b style="color: #E65100;">💡 grep 参数指南</b>
        <table border="1" cellspacing="0" cellpadding="3" style="border-collapse: collapse; margin-top: 5px;">
            <tr><td><b>-r</b></td><td>递归所有子文件夹</td></tr>
            <tr><td><b>-n</b></td><td>显示所在行号</td></tr>
            <tr><td><b>-i</b></td><td>忽略大小写区分</td></tr>
            <tr><td><b>-w</b></td><td>精准整词匹配</td></tr>
            <tr><td><b>--include="*.py"</b></td><td>只搜指定格式文件</td></tr>
        </table>
    </div>
    """

    # 需要特殊背景高亮的文件扩展名
    HIGHLIGHT_EXTENSIONS = ['.txt', '.md', '.log', '.i']

    def __init__(self):
        """初始化主窗口及其组件。"""
        super().__init__()
        self.setWindowTitle("PySide2 极客文件浏览器")

        # 设置窗口图标
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "firegrep.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.adjust_to_screen()
        self.config_mgr = ConfigManager()
        self.model = QFileSystemModel()

        # 恢复上次打开的目录
        self.current_root_path = self.config_mgr.get("last_folder", QDir.rootPath())
        if not os.path.exists(self.current_root_path):
            self.current_root_path = QDir.rootPath()

        self.model.setRootPath(self.current_root_path)
        self.model.modelReset.connect(self.trigger_auto_expand)
        self.model.directoryLoaded.connect(self.check_and_expand_sub_dir)

        self.display_mode = 2  # 默认显示模式：仅以子树方式显示
        self.init_ui()
        self.apply_persisted_config()

    def adjust_to_screen(self) -> None:
        """根据屏幕可用区域调整窗口大小和位置。"""
        screen = QApplication.primaryScreen()
        if screen:
            available_geo = screen.availableGeometry()
            self.setGeometry(available_geo)

    def init_ui(self) -> None:
        """初始化用户界面组件。"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        global_layout = QVBoxLayout(main_widget)
        global_layout.setSpacing(10)

        # === 顶部工具栏 ===
        top_layout = QHBoxLayout()
        self.btn_open = QPushButton("打开文件夹")
        self.btn_open.clicked.connect(self.select_folder)
        top_layout.addWidget(self.btn_open)

        top_layout.addWidget(QLabel("显示模式："))
        self.mode_selector = QComboBox()
        self.mode_selector.addItems([
            "1. 仅显示当前层级",
            "2. 自动展开所有子树",
            "3. 仅以子树方式显示 [默认]"
        ])
        self.mode_selector.setCurrentIndex(2)
        self.mode_selector.currentIndexChanged.connect(self.switch_mode)
        top_layout.addWidget(self.mode_selector)

        self.lbl_path = QLabel(f"当前目录: {self.current_root_path}")
        self.lbl_path.setStyleSheet("color: #666; font-weight: bold; margin-left: 10px;")
        top_layout.addWidget(self.lbl_path, 1)
        global_layout.addLayout(top_layout)

        # === 主分割区域 ===
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：文件树
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(self.current_root_path))
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.setColumnWidth(0, 350)
        self.tree_view.doubleClicked.connect(self.on_tree_view_double_clicked)
        left_layout.addWidget(self.tree_view)
        splitter.addWidget(left_widget)

        # 右侧：搜索面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("🔍 文本关键字检索 (grep):"))

        # 搜索输入行
        search_input_layout = QHBoxLayout()
        self.edit_keyword = QLineEdit()
        self.edit_keyword.setPlaceholderText("在此输入你要查找的关键字...")
        self.edit_keyword.textChanged.connect(lambda: self.update_command_preview(ignore_ext=False))
        self.edit_keyword.returnPressed.connect(self.run_grep_search)
        search_input_layout.addWidget(self.edit_keyword)

        self.edit_ext = QLineEdit()
        self.edit_ext.setPlaceholderText("后缀, 比如 .c .h")
        self.edit_ext.setFixedWidth(130)
        self.edit_ext.textChanged.connect(self.on_ext_text_changed)
        self.edit_ext.returnPressed.connect(self.run_grep_search)
        search_input_layout.addWidget(self.edit_ext)

        self.btn_all_files = QPushButton("全部文件搜索")
        self.btn_all_files.setToolTip("获取当前命令，过滤掉后缀参数后执行全局搜索（控件命令保持不变）")
        self.btn_all_files.clicked.connect(self.run_search_all_files)
        search_input_layout.addWidget(self.btn_all_files)

        self.btn_search = QPushButton("搜索")
        self.btn_search.clicked.connect(self.run_grep_search)
        search_input_layout.addWidget(self.btn_search)
        right_layout.addLayout(search_input_layout)

        # 命令预览行
        cmd_label_layout = QHBoxLayout()
        cmd_label_layout.addWidget(QLabel("🛠️ 实际执行的 Shell 命令："))
        self.chk_custom_cmd = QCheckBox("启用专家修改模式")
        self.chk_custom_cmd.toggled.connect(self.toggle_cmd_edit)
        self.chk_custom_cmd.setToolTip(self.GREP_HELP_HTML)
        cmd_label_layout.addWidget(self.chk_custom_cmd, 0, Qt.AlignRight)
        right_layout.addLayout(cmd_label_layout)

        self.edit_command = QLineEdit()
        self.edit_command.setText('grep -rn "" .')
        self.edit_command.setReadOnly(True)
        self.edit_command.setStyleSheet("background-color: #F5F5F5; font-family: monospace;")
        self.edit_command.returnPressed.connect(self.run_grep_search)
        right_layout.addWidget(self.edit_command)

        # 搜索结果列表
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.on_result_double_clicked)
        right_layout.addWidget(self.result_list)

        splitter.addWidget(right_widget)
        global_layout.addWidget(splitter, 1)
        splitter.setSizes([int(self.width() * 0.55), int(self.width() * 0.45)])

        # 应用默认显示模式
        self.switch_mode(2)

    def run_search_all_files(self) -> None:
        """执行不带文件后缀过滤的全局搜索。"""
        current_cmd = self.edit_command.text().strip()
        # 移除 --include 参数
        cleaned_cmd = re.sub(r'--include\s*=\s*"[^"]*"', '', current_cmd)
        cleaned_cmd = re.sub(r'--include\s*=\s*\S+', '', cleaned_cmd)
        cleaned_cmd = re.sub(r'\s+', ' ', cleaned_cmd).strip()
        self.execute_grep_command(cleaned_cmd)

    def on_ext_text_changed(self) -> None:
        """文件后缀输入变化时更新命令预览并持久化配置。"""
        self.update_command_preview(ignore_ext=False)
        self.config_mgr.set("file_extensions", self.edit_ext.text())

    def apply_persisted_config(self) -> None:
        """从配置中恢复上次的搜索状态。"""
        saved_ext = self.config_mgr.get("file_extensions", "")
        if saved_ext:
            self.edit_ext.setText(saved_ext)

        is_expert = self.config_mgr.get("is_expert_mode", False)
        saved_cmd = self.config_mgr.get("custom_command", 'grep -rn "" .')
        if is_expert:
            self.chk_custom_cmd.setChecked(True)
            self.edit_command.setText(saved_cmd)
        else:
            self.update_command_preview(ignore_ext=False)

    def select_folder(self) -> None:
        """打开文件夹选择对话框并切换根目录。"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", self.current_root_path)
        if folder_path:
            self._change_root_path(folder_path)

    def _change_root_path(self, folder_path: str) -> None:
        """
        切换当前根目录到指定路径。
        
        Args:
            folder_path: 新的根目录路径
        """
        self.current_root_path = folder_path
        self.lbl_path.setText(f"当前目录: {folder_path}")
        self.model.setRootPath(folder_path)
        self.tree_view.setRootIndex(self.model.index(folder_path))
        self.result_list.clear()
        self.edit_keyword.clear()
        self.update_command_preview(ignore_ext=False)
        self.config_mgr.set("last_folder", folder_path)
        self.tree_view.collapseAll()

    def switch_mode(self, index: int) -> None:
        """
        切换文件树显示模式。
        
        Args:
            index: 模式索引 (0=仅当前层级, 1=自动展开, 2=子树方式)
        """
        self.display_mode = index
        if index == 0:
            self.tree_view.collapseAll()
            self.tree_view.setItemsExpandable(False)
            self.tree_view.setRootIsDecorated(False)
        else:
            self.tree_view.setItemsExpandable(True)
            self.tree_view.setRootIsDecorated(True)
            if index == 1:
                self.trigger_auto_expand()

    def get_selected_extensions(self) -> List[str]:
        """
        解析用户输入的文件后缀列表。
        
        Returns:
            List[str]: 清理后的后缀列表
        """
        text = self.edit_ext.text().strip()
        if not text:
            return []
        tokens = text.split()
        return [token.strip() for token in tokens if token.strip()]

    def update_command_preview(self, ignore_ext: bool = False) -> None:
        """
        根据当前输入更新grep命令预览。
        
        Args:
            ignore_ext: 是否忽略文件后缀过滤
        """
        if self.chk_custom_cmd.isChecked():
            return

        kw = self.edit_keyword.text()
        selected_exts = [] if ignore_ext else self.get_selected_extensions()

        if selected_exts:
            includes = " ".join([
                f'--include="*{ext if ext.startswith(".") else "." + ext}"'
                for ext in selected_exts
            ])
            self.edit_command.setText(f'grep -rn {includes} "{kw}" .')
        else:
            self.edit_command.setText(f'grep -rn "{kw}" .')

    def toggle_cmd_edit(self, checked: bool) -> None:
        """
        切换专家命令编辑模式。
        
        Args:
            checked: 是否启用专家模式
        """
        self.edit_command.setReadOnly(not checked)
        self.config_mgr.set("is_expert_mode", checked)

        if checked:
            self.edit_command.setStyleSheet(
                "background-color: #FFFFFF; font-family: monospace; border: 1px solid #4CAF50;"
            )
            self.edit_keyword.setEnabled(False)
            self.edit_ext.setEnabled(False)
            self.btn_all_files.setEnabled(False)
        else:
            self.edit_command.setStyleSheet("background-color: #F5F5F5; font-family: monospace;")
            self.edit_keyword.setEnabled(True)
            self.edit_ext.setEnabled(True)
            self.btn_all_files.setEnabled(True)
            self.update_command_preview(ignore_ext=False)

    def get_current_keyword(self) -> str:
        """
        获取当前有效的搜索关键字。
        在专家模式下从命令中解析，否则直接取输入框内容。
        
        Returns:
            str: 清理后的搜索关键字
        """
        raw_kw = ""
        if self.chk_custom_cmd.isChecked():
            try:
                parsed_args = shlex.split(self.edit_command.text().strip())
                potential = [
                    arg for arg in parsed_args
                    if not arg.startswith('-') and arg not in ('grep', '.') and '*' not in arg
                ]
                raw_kw = potential[0] if potential else ""
            except ValueError:
                raw_kw = ""
        else:
            raw_kw = self.edit_keyword.text().strip()

        if not raw_kw:
            return ""

        # 转义正则特殊字符用于安全替换
        cleaned_kw = re.sub(r'\\([.+*?^$()\[\]{}|])', r'\1', raw_kw)
        return cleaned_kw

    def run_grep_search(self) -> None:
        """执行grep搜索。"""
        if not self.chk_custom_cmd.isChecked():
            self.update_command_preview(ignore_ext=False)
        full_command_str = self.edit_command.text().strip()
        self.execute_grep_command(full_command_str)

    def execute_grep_command(self, command_str: str) -> None:
        """
        执行grep命令并在结果列表中显示输出。
        
        Args:
            command_str: 完整的grep命令字符串
        """
        keyword = self.get_current_keyword()

        # 专家模式下保存自定义命令
        if self.chk_custom_cmd.isChecked():
            self.config_mgr.set("custom_command", command_str)

        # 验证输入有效性
        if not command_str or (not self.chk_custom_cmd.isChecked() and not keyword):
            self.result_list.clear()
            self.result_list.addItem("⚠️ 请先输入有效的检索命令或关键字")
            return

        self.result_list.clear()
        self.result_list.addItem("⏳ 正在执行搜索中...")
        QApplication.processEvents()

        try:
            cmd_list = shlex.split(command_str)

            # 确保命令以grep开头
            if cmd_list and cmd_list[0] != "grep":
                if "grep" in cmd_list:
                    cmd_list = cmd_list[cmd_list.index("grep"):]
                else:
                    cmd_list.insert(0, "grep")

            result = subprocess.run(
                cmd_list,
                cwd=self.current_root_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="ignore"
            )

            self.result_list.clear()

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.splitlines()
                highlight_style = (
                    f'<b style="color: #E65100; background-color: #FFE0B2; '
                    f'padding: 0 2px;">{keyword}</b>'
                )

                for line in lines:
                    # HTML转义防止注入
                    escaped_line = (
                        line.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                    )
                    highlighted_text = (
                        escaped_line.replace(keyword, highlight_style)
                        if keyword and keyword in escaped_line
                        else escaped_line
                    )

                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, line)
                    item.setSizeHint(QSize(0, 42))

                    # 判断是否需要特殊背景高亮
                    should_highlight = self._should_highlight_line(line)

                    label = QLabel(highlighted_text)
                    label.setWordWrap(True)
                    label.setFont(QFont("monospace", 13))
                    label.setMargin(4)

                    if should_highlight:
                        label.setAutoFillBackground(True)
                        label.setStyleSheet(
                            "font-family: monospace; font-size: 13px; "
                            "background-color: #F1F8E9; border-radius: 4px;"
                        )
                    else:
                        label.setStyleSheet("font-family: monospace; font-size: 13px;")

                    self.result_list.addItem(item)
                    self.result_list.setItemWidget(item, label)
            else:
                self.result_list.addItem("❌ 未找到匹配的结果。")

        except Exception as e:
            logger.exception("grep命令执行失败")
            self.result_list.clear()
            self.result_list.addItem(f"🚨 命令执行失败: {str(e)}")

    def _should_highlight_line(self, line: str) -> bool:
        """
        判断搜索结果行是否属于需要特殊背景高亮的文件类型。
        
        Args:
            line: grep输出的单行结果
            
        Returns:
            bool: 是否需要高亮
        """
        for ext in self.HIGHLIGHT_EXTENSIONS:
            normalized_ext = ext if ext.startswith('.') else '.' + ext
            pattern = rf'^.*\{normalized_ext}\s*:'
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def on_result_double_clicked(self, item: QListWidgetItem) -> None:
        """
        双击搜索结果项时打开对应文件并定位到目标行。
        
        Args:
            item: 被双击的列表项
        """
        raw_text = item.data(Qt.UserRole)
        if not raw_text or ":" not in raw_text:
            return

        parts = raw_text.split(":", 2)
        relative_file_path = parts[0]
        try:
            target_line = int(parts[1])
        except ValueError:
            target_line = 1

        absolute_file_path = os.path.abspath(
            os.path.join(self.current_root_path, relative_file_path)
        )

        # 在树视图中定位文件
        file_index = self.model.index(absolute_file_path)
        if file_index.isValid():
            self.tree_view.setCurrentIndex(file_index)
            self.tree_view.scrollTo(file_index)

        # 打开文件查看对话框
        if os.path.isfile(absolute_file_path):
            kw = self.get_current_keyword()
            dialog = FileContentDialog(
                absolute_file_path, target_line_num=target_line, keyword=kw, parent=self
            )
            dialog.exec_()

    def on_tree_view_double_clicked(self, index) -> None:
        """
        双击文件树节点时：如果是文件夹则切换当前目录，如果是文件则打开查看器。
        
        Args:
            index: 被双击的模型索引
        """
        file_path = self.model.filePath(index)
        if self.model.isDir(index):
            # 双击文件夹：切换当前根目录
            self._change_root_path(file_path)
        elif os.path.isfile(file_path):
            # 双击文件：打开查看器
            kw = self.get_current_keyword()
            dialog = FileContentDialog(file_path, target_line_num=1, keyword=kw, parent=self)
            dialog.exec_()

    def trigger_auto_expand(self) -> None:
        """触发根目录的自动展开（仅在模式1下生效）。"""
        if self.display_mode == 1:
            QTimer.singleShot(50, self._do_expand_root)

    def _do_expand_root(self) -> None:
        """展开根目录及其所有子目录。"""
        root_index = self.model.index(self.current_root_path)
        if root_index.isValid():
            self.tree_view.expand(root_index)
            self._expand_all_children(root_index)

    def _expand_all_children(self, parent_index) -> None:
        """
        递归展开指定节点的所有子目录。
        
        Args:
            parent_index: 父节点的模型索引
        """
        if self.display_mode != 1 or not parent_index.isValid():
            return

        rows = self.model.rowCount(parent_index)
        if rows == 0:
            self.model.fetchMore(parent_index)
            return

        for i in range(rows):
            child_index = self.model.index(i, 0, parent_index)
            if self.model.isDir(child_index):
                self.tree_view.expand(child_index)
                if self.model.rowCount(child_index) == 0:
                    self.model.fetchMore(child_index)
                else:
                    self._expand_all_children(child_index)

    def check_and_expand_sub_dir(self, path: str) -> None:
        """
        当目录加载完成时检查是否需要自动展开。
        
        Args:
            path: 已加载的目录路径
        """
        if self.display_mode == 1 and path.startswith(self.current_root_path):
            dir_index = self.model.index(path)
            if dir_index.isValid():
                self.tree_view.expand(dir_index)
                self._expand_all_children(dir_index)
