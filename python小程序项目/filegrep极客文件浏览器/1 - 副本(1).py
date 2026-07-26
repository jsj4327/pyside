import sys
import os
import json
import subprocess
import shlex
import re
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTreeView, 
                             QFileSystemModel, QComboBox, QLabel, QLineEdit, 
                             QListWidget, QListWidgetItem, QSplitter, QCheckBox,
                             QDialog, QTextEdit, QMessageBox, QScrollBar, QTabWidget)
from PySide2.QtCore import QDir, QTimer, Qt, QSize, QRegExp
from PySide2.QtGui import QTextCursor, QTextCharFormat, QColor, QSyntaxHighlighter, QFont

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config.json")

class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, search_keyword=""):
        super().__init__(parent)
        self.highlighting_rules = []
        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0056b3"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ["\\bchar\\b", "\\bclass\\b", "\\bconst\\b", "\\bdouble\\b", "\\benum\\b", "\\bexplicit\\b", "\\bfriend\\b", "\\binline\\b", "\\bint\\b", "\\blong\\b", "\\bnamespace\\b", "\\boperator\\b", "\\bprivate\\b", "\\bprotected\\b", "\\bpublic\\b", "\\bshort\\b", "\\bsigned\\b", "\\bstatic\\b", "\\bstruct\\b", "\\btemplate\\b", "\\bthis\\b", "\\btypedef\\b", "\\btypename\\b", "\\bunion\\b", "\\bunsigned\\b", "\\bvirtual\\b", "\\bvoid\\b", "\\bdef\\b", "\\bimport\\b", "\\bfrom\\b", "\\bif\\b", "\\belse\\b", "\\belif\\b", "\\breturn\\b", "\\bfor\\b", "\\bwhile\\b", "\\btry\\b", "\\bexcept\\b"]
        for pattern in keywords:
            self.highlighting_rules.append((QRegExp(pattern), keyword_format))
        # 数字、字符串、注释
        number_format = QTextCharFormat(); number_format.setForeground(QColor("#D35400"))
        self.highlighting_rules.append((QRegExp("\\b[0-9]+L?\\b"), number_format))
        string_format = QTextCharFormat(); string_format.setForeground(QColor("#A31515"))
        self.highlighting_rules.append((QRegExp("\".*\""), string_format))
        self.highlighting_rules.append((QRegExp("'.*'"), string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#008000"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegExp("//[^\n]*"), comment_format))
        self.highlighting_rules.append((QRegExp("#[^\n]*"), comment_format))
        # 搜索关键字高亮
        if search_keyword:
            search_format = QTextCharFormat()
            search_format.setBackground(QColor("#FFF176"))
            search_format.setForeground(QColor("#000000"))
            search_format.setFontWeight(QFont.Bold)
            self.highlighting_rules.append((QRegExp(QRegExp.escape(search_keyword)), search_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)

class FileContentDialog(QDialog):
    def __init__(self, file_path, target_line_num=1, keyword="", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.target_line_num = target_line_num
        self.keyword = keyword
        self.parent_viewer = parent
        
        self.setWindowTitle(f"代码查看器 - {os.path.basename(file_path)}")
        self.resize(1250, 820)
        self.init_ui()
        self.load_file_content()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        splitter = QSplitter(Qt.Horizontal)

        # 左侧代码区
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel(f"📄 路径: {self.file_path}"))
        
        hbox = QHBoxLayout()
        self.line_number_edit = QTextEdit()
        self.line_number_edit.setReadOnly(True)
        self.line_number_edit.setFixedWidth(60)
        self.line_number_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.line_number_edit.setStyleSheet("background-color: #F0F0F0; color: #888; border: none; font-family: Consolas, monospace; font-size: 13px;")
        hbox.addWidget(self.line_number_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.content_edit.setStyleSheet("background-color: #FFFFFF; color: #333; border: 1px solid #D0D0D0; font-family: Consolas, monospace; font-size: 13px;")
        self.content_edit.viewport().installEventFilter(self)
        hbox.addWidget(self.content_edit)
        left_layout.addLayout(hbox, 1)
        splitter.addWidget(left_widget)

        # 右侧面板
        self.tab_widget = QTabWidget()
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(5,5,5,5)

        self.lbl_match_count = QLabel("📊 关键字检索: 0 处")
        self.lbl_match_count.setStyleSheet("font-weight: bold; color: #E65100;")
        vbox.addWidget(self.lbl_match_count)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("QListWidget::item:selected { background-color: #B2DFDB; color: #004D40; }")
        self.nav_list.itemDoubleClicked.connect(self.on_nav_item_triggered)
        self.nav_list.currentItemChanged.connect(self.on_nav_item_triggered)
        vbox.addWidget(self.nav_list)

        # 二次搜索
        vbox.addWidget(QLabel("🔄 Ctrl+双击搜索结果:"))
        self.secondary_result_list = QListWidget()
        self.secondary_result_list.setStyleSheet("""
            QListWidget { background-color: #FAFAFA; }
            QListWidget::item:selected { background-color: #C8E6C9; color: #1B5E20; }
        """)
        self.secondary_result_list.itemDoubleClicked.connect(self.on_secondary_result_clicked)
      # self.secondary_result_list.currentItemChanged.connect(self.on_secondary_result_clicked)
        vbox.addWidget(self.secondary_result_list)

        self.tab_widget.addTab(tab, "🔍 检索命中")
        splitter.addWidget(self.tab_widget)
        main_layout.addWidget(splitter)
        splitter.setSizes([820, 430])

        self.highlighter = CodeHighlighter(self.content_edit.document(), self.keyword)

        # 滚动同步
        self.content_edit.verticalScrollBar().valueChanged.connect(self.line_number_edit.verticalScrollBar().setValue)
        self.line_number_edit.verticalScrollBar().valueChanged.connect(self.content_edit.verticalScrollBar().setValue)

    def eventFilter(self, obj, event):
        if obj == self.content_edit.viewport() and event.type() == event.MouseButtonDblClick:
            if event.modifiers() & Qt.ControlModifier:
                self.handle_ctrl_double_click(event)
                return True
        return super().eventFilter(obj, event)

    def handle_ctrl_double_click(self, event):
        cursor = self.content_edit.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        if word and self.parent_viewer:
            self.perform_secondary_grep(word)

    def perform_secondary_grep(self, word):
        self.secondary_result_list.clear()
        self.secondary_result_list.addItem(f"⏳ 搜索 '{word}' 中...")
        QApplication.processEvents()
        try:
            result = subprocess.run(['grep', '-rn', word, '.'], cwd=self.parent_viewer.current_root_path,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='ignore')
            self.secondary_result_list.clear()
            if result.stdout:
                highlight_style = f'<b style="color:#E65100;background:#FFE0B2;padding:0 2px;">{word}</b>'
                for line in result.stdout.splitlines():
                    escaped = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                    highlighted = escaped.replace(word, highlight_style) if word in escaped else escaped
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, (line, word))   # 保存原始行和当前关键字
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
            self.secondary_result_list.addItem(f"错误: {e}")

    def on_secondary_result_clicked(self, current, previous=None):
        if not current: return
        data = current.data(Qt.UserRole)
        if isinstance(data, tuple):
            raw_line, keyword = data
        else:
            raw_line, keyword = data, ""
        if not raw_line or ":" not in raw_line: return
        parts = raw_line.split(":", 2)
        rel_path = parts[0]
        try:
            line_num = int(parts[1])
        except:
            line_num = 1
        abs_path = os.path.abspath(os.path.join(self.parent_viewer.current_root_path, rel_path))
        if os.path.isfile(abs_path):
            dialog = FileContentDialog(abs_path, line_num, keyword, self.parent_viewer)  # 传递当前关键字
            dialog.exec_()

    def load_file_content(self):
        # ... (保持不变)
        if not os.path.exists(self.file_path):
            self.content_edit.setText("文件不存在")
            return
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            lines = content.splitlines()
            self.line_number_edit.setPlainText("\n".join(str(i+1) for i in range(len(lines))))
            self.content_edit.setPlainText(content)
            self.populate_navigation_sidebar(lines)
            QTimer.singleShot(80, self.initial_scroll_position)
        except Exception as e:
            self.content_edit.setText(str(e))

    def populate_navigation_sidebar(self, lines):
        self.nav_list.clear()
        if not self.keyword:
            self.lbl_match_count.setText("未指定关键字")
            return
        count = 0
        for i, line in enumerate(lines):
            if self.keyword.lower() in line.lower():
                count += 1
                item = QListWidgetItem(f"第{i+1}行: {line.strip()[:45]}")
                item.setData(Qt.UserRole, i+1)
                self.nav_list.addItem(item)
        self.lbl_match_count.setText(f"📊 关键字 '{self.keyword}' 检索: {count} 处")

    def initial_scroll_position(self):
        if self.target_line_num > 1:
            self.scroll_to_absolute_line(self.target_line_num)

    def on_nav_item_triggered(self, current, prev=None):
        if current:
            self.scroll_to_absolute_line(current.data(Qt.UserRole))

    def scroll_to_absolute_line(self, line_num):
        block = self.content_edit.document().findBlockByLineNumber(line_num-1)
        if block.isValid():
            cursor = QTextCursor(block)
            self.content_edit.setTextCursor(cursor)
            rect = self.content_edit.document().documentLayout().blockBoundingRect(block)
            target = int(rect.top() - self.content_edit.viewport().height()/2)
            self.content_edit.verticalScrollBar().setValue(max(0, min(target, self.content_edit.verticalScrollBar().maximum())))

# ====================== FileViewer (保持完整) ======================
class FileViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide2 极客文件浏览器 (几何精确定位与快捷侧边栏)")
        self.adjust_to_screen()
        self.config = self.load_config()
        self.model = QFileSystemModel()
        self.current_root_path = self.config.get("last_folder", QDir.rootPath())
        if not os.path.exists(self.current_root_path):
            self.current_root_path = QDir.rootPath()
            
        self.model.setRootPath(self.current_root_path)
        self.model.modelReset.connect(self.trigger_auto_expand)
        self.model.directoryLoaded.connect(self.check_and_expand_sub_dir)
        self.display_mode = 2  
        self.init_ui()
        self.apply_persisted_config()
    
    def adjust_to_screen(self):
        screen = QApplication.primaryScreen()
        available_geo = screen.availableGeometry()
        self.setGeometry(available_geo)
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        global_layout = QVBoxLayout(main_widget)
        global_layout.setSpacing(10)
        # ================= 顶部控制栏 =================
        top_layout = QHBoxLayout()
        self.btn_open = QPushButton("打开文件夹")
        self.btn_open.clicked.connect(self.select_folder)
        top_layout.addWidget(self.btn_open)
        top_layout.addWidget(QLabel("显示模式："))
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["1. 仅显示当前层级", "2. 自动展开所有子树", "3. 仅以子树方式显示 [默认]"])
        self.mode_selector.setCurrentIndex(2) 
        self.mode_selector.currentIndexChanged.connect(self.switch_mode)
        top_layout.addWidget(self.mode_selector)
        
        self.lbl_path = QLabel(f"当前目录: {self.current_root_path}")
        self.lbl_path.setStyleSheet("color: #666; font-weight: bold; margin-left: 10px;")
        top_layout.addWidget(self.lbl_path, 1) 
        global_layout.addLayout(top_layout)
        # ================= 中间区域 =================
        splitter = QSplitter(Qt.Horizontal)
        # 左侧树
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
        # 右侧搜索
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("🔍 文本关键字检索 (grep):"))
        
        search_input_layout = QHBoxLayout()
        self.edit_keyword = QLineEdit()
        self.edit_keyword.setPlaceholderText("在此输入你要查找的关键字...")
        self.edit_keyword.textChanged.connect(self.update_command_preview) 
        self.edit_keyword.returnPressed.connect(self.run_grep_search)
        search_input_layout.addWidget(self.edit_keyword)
        
        self.btn_search = QPushButton("搜索")
        self.btn_search.clicked.connect(self.run_grep_search)
        search_input_layout.addWidget(self.btn_search)
        right_layout.addLayout(search_input_layout)
        
        cmd_label_layout = QHBoxLayout()
        cmd_label_layout.addWidget(QLabel("🛠️ 实际执行的 Shell 命令："))
        self.chk_custom_cmd = QCheckBox("启用专家修改模式")
        self.chk_custom_cmd.toggled.connect(self.toggle_cmd_edit)
        
        grep_help_html = """
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
        self.chk_custom_cmd.setToolTip(grep_help_html)
        cmd_label_layout.addWidget(self.chk_custom_cmd, 0, Qt.AlignRight)
        right_layout.addLayout(cmd_label_layout)
        self.edit_command = QLineEdit()
        self.edit_command.setText('grep -rn "" .') 
        self.edit_command.setReadOnly(True)       
        self.edit_command.setStyleSheet("background-color: #F5F5F5; font-family: monospace;")
        self.edit_command.returnPressed.connect(self.run_grep_search)
        right_layout.addWidget(self.edit_command)
        
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.on_result_double_clicked)
        right_layout.addWidget(self.result_list)
        splitter.addWidget(right_widget)
        global_layout.addWidget(splitter, 1) 
        splitter.setSizes([int(self.width() * 0.55), int(self.width() * 0.45)])
        self.switch_mode(2)
    
    def apply_persisted_config(self):
        is_expert = self.config.get("is_expert_mode", False)
        saved_cmd = self.config.get("custom_command", 'grep -rn "" .')
        if is_expert:
            self.chk_custom_cmd.setChecked(True)
            self.edit_command.setText(saved_cmd)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", self.current_root_path)
        if folder_path:
            self.current_root_path = folder_path
            self.lbl_path.setText(f"当前目录: {folder_path}")
            self.model.setRootPath(folder_path)
            self.tree_view.setRootIndex(self.model.index(folder_path))
            self.result_list.clear()
            self.edit_keyword.clear()
            self.update_command_preview()
            
            self.config["last_folder"] = folder_path
            self.save_config()
            self.tree_view.collapseAll()
    
    def switch_mode(self, index):
        self.display_mode = index
        if index == 0:
            self.tree_view.collapseAll()
            self.tree_view.setItemsExpandable(False)
            self.tree_view.setRootIsDecorated(False)
        else:
            self.tree_view.setItemsExpandable(True)   
            self.tree_view.setRootIsDecorated(True)   
            if index == 1: self.trigger_auto_expand()
    
    def update_command_preview(self):
        if self.chk_custom_cmd.isChecked(): return 
        self.edit_command.setText(f'grep -rn "{self.edit_keyword.text()}" .')
    
    def toggle_cmd_edit(self, checked):
        self.edit_command.setReadOnly(not checked)
        self.config["is_expert_mode"] = checked
        self.save_config()
        if checked:
            self.edit_command.setStyleSheet("background-color: #FFFFFF; font-family: monospace; border: 1px solid #4CAF50;")
            self.edit_keyword.setEnabled(False) 
        else:
            self.edit_command.setStyleSheet("background-color: #F5F5F5; font-family: monospace;")
            self.edit_keyword.setEnabled(True)
            self.update_command_preview()
    
    def get_current_keyword(self):
        raw_kw = ""
        if self.chk_custom_cmd.isChecked():
            try:
                parsed_args = shlex.split(self.edit_command.text().strip())
                potential = [arg for arg in parsed_args if not arg.startswith('-') and arg != 'grep' and arg != '.']
                raw_kw = potential[0] if potential else ""
            except Exception:
                raw_kw = ""
        else:
            raw_kw = self.edit_keyword.text().strip()
        if not raw_kw:
            return ""
        cleaned_kw = re.sub(r'\\([.\\+*?^$()\[\]{}|])', r'\1', raw_kw)
        return cleaned_kw
    
    def run_grep_search(self):
        full_command_str = self.edit_command.text().strip()
        keyword = self.get_current_keyword()
        if self.chk_custom_cmd.isChecked():
            self.config["custom_command"] = full_command_str
            self.save_config()
        if not full_command_str or (not self.chk_custom_cmd.isChecked() and not keyword):
            self.result_list.clear()
            self.result_list.addItem("⚠️ 请先输入有效的检索命令或关键字")
            return
        self.result_list.clear()
        self.result_list.addItem("⏳ 正在执行自定义命令搜索中...")
        QApplication.processEvents()
        try:
            cmd_list = shlex.split(full_command_str)
            if cmd_list and cmd_list[0] != "grep":
                if "grep" in cmd_list: cmd_list = cmd_list[cmd_list.index("grep"):]
                else: cmd_list.insert(0, "grep")
            result = subprocess.run(cmd_list, cwd=self.current_root_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
            self.result_list.clear()
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.splitlines()
                highlight_style = f'<b style="color: #E65100; background-color: #FFE0B2; padding: 0 2px;">{keyword}</b>'
                for line in lines:
                    escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    highlighted_text = escaped_line.replace(keyword, highlight_style) if keyword and keyword in escaped_line else escaped_line
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, line) 
                    item.setSizeHint(QSize(0, 42)) 
                    self.result_list.addItem(item)
                    
                    label = QLabel(highlighted_text)
                    label.setWordWrap(True) 
                    label.setStyleSheet("font-family: monospace; font-size: 13px;")
                    label.setMargin(4)
                    self.result_list.setItemWidget(item, label)
            else:
                self.result_list.addItem("❌ 未找到匹配的结果。")
        except Exception as e:
            self.result_list.clear()
            self.result_list.addItem(f"🚨 命令执行失败: {str(e)}")
    
    def on_result_double_clicked(self, item):
        raw_text = item.data(Qt.UserRole)
        if not raw_text or ":" not in raw_text: return
            
        parts = raw_text.split(":", 2)
        relative_file_path = parts[0]
        
        try:
            target_line = int(parts[1])
        except ValueError:
            target_line = 1
            
        absolute_file_path = os.path.abspath(os.path.join(self.current_root_path, relative_file_path))
        
        file_index = self.model.index(absolute_file_path)
        if file_index.isValid():
            self.tree_view.setCurrentIndex(file_index)
            self.tree_view.scrollTo(file_index)
            
        if os.path.isfile(absolute_file_path):
            kw = self.get_current_keyword()
            dialog = FileContentDialog(absolute_file_path, target_line_num=target_line, keyword=kw, parent=self)
            dialog.exec_()
    
    def on_tree_view_double_clicked(self, index):
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path):
            kw = self.get_current_keyword()
            dialog = FileContentDialog(file_path, target_line_num=1, keyword=kw, parent=self)
            dialog.exec_()
    
    def trigger_auto_expand(self):
        if self.display_mode == 1: QTimer.singleShot(50, self._do_expand_root)
    
    def _do_expand_root(self):
        root_index = self.model.index(self.current_root_path)
        if root_index.isValid():
            self.tree_view.expand(root_index)
            self._expand_all_children(root_index)
    
    def _expand_all_children(self, parent_index):
        if self.display_mode != 1 or not parent_index.isValid(): return
        rows = self.model.rowCount(parent_index)
        if rows == 0:
            self.model.fetchMore(parent_index)
            return
        for i in range(rows):
            child_index = self.model.index(i, 0, parent_index)
            if self.model.isDir(child_index):
                self.tree_view.expand(child_index)
                if self.model.rowCount(child_index) == 0: self.model.fetchMore(child_index)
                else: self._expand_all_children(child_index)
    
    def check_and_expand_sub_dir(self, path):
        if self.display_mode == 1 and path.startswith(self.current_root_path):
            dir_index = self.model.index(path)
            if dir_index.isValid():
                self.tree_view.expand(dir_index)
                self._expand_all_children(dir_index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FileViewer()
    viewer.show()
    sys.exit(app.exec_())
