# -*- coding: utf-8 -*-

import os
import time
import markdown
from PySide2 import QtWidgets, QtGui, QtCore
from ui_note import Ui_NoteApp
from database import NoteDatabase
from core import PythonHighlighter, get_code_block_html, LIGHT_STYLE, DARK_STYLE
from visual_effects import CurrentLineHighlighter, get_modern_scrollbar_style


class CustomTextEdit(QtWidgets.QTextEdit):
    """自定义文本编辑框：支持直接粘贴剪贴板中的图片"""
    def __init__(self, parent=None, app_window=None, tab_page=None):
        super().__init__(parent)
        self.app_window = app_window
        self.tab_page = tab_page

    def canInsertFromMimeData(self, source: QtCore.QMimeData) -> bool:
        if source.hasImage() and self.app_window and not getattr(self.tab_page, "is_read_only", False):
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QtCore.QMimeData):
        if source.hasImage() and self.app_window:
            image = source.imageData()
            if isinstance(image, QtGui.QImage):
                self.app_window.save_and_insert_image(image, self.tab_page)
                return
        super().insertFromMimeData(source)


class NoteAppWindow(QtWidgets.QMainWindow, Ui_NoteApp):
    """笔记软件核心业务逻辑类（整合全部增强功能版）"""
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.current_notebook_id = 1
        self.is_in_trash_bin = False
        self.is_dark_mode = False
        
        self.apply_global_theme()
        self.db = NoteDatabase()
        
        self.load_notebooks_tree()
        self.load_tags_list()
        self.bind_signals()
        self.init_shortcuts()
        
        if self.listWidget.count() > 0:
            self.open_note_in_tab(self.listWidget.item(0).data(QtCore.Qt.UserRole))

    def apply_global_theme(self):
        base_style = DARK_STYLE if self.is_dark_mode else LIGHT_STYLE
        scrollbar_style = get_modern_scrollbar_style(self.is_dark_mode)
        self.setStyleSheet(base_style + "\n" + scrollbar_style)

    def load_notebooks_tree(self):
        self.treeWidget.clear()
        notebooks = self.db.get_all_notebooks()
        for nb_id, name in notebooks:
            item = QtWidgets.QTreeWidgetItem(self.treeWidget)
            item.setText(0, f"📁 {name}")
            item.setData(0, QtCore.Qt.UserRole, nb_id)
            
        trash_item = QtWidgets.QTreeWidgetItem(self.treeWidget)
        trash_item.setText(0, "🗑️ 回收站")
        trash_item.setData(0, QtCore.Qt.UserRole, -999)
        
        if self.treeWidget.topLevelItemCount() > 0:
            first_item = self.treeWidget.topLevelItem(0)
            self.treeWidget.setCurrentItem(first_item)
            self.current_notebook_id = first_item.data(0, QtCore.Qt.UserRole)
            self.load_notes_list()

    def load_tags_list(self):
        self.tagListWidget.clear()
        tags = self.db.get_all_tags()
        for tag in tags:
            item = QtWidgets.QListWidgetItem(f"🏷️ {tag}")
            item.setData(QtCore.Qt.UserRole, tag)
            self.tagListWidget.addItem(item)

    def load_notes_list(self, keyword=""):
        self.listWidget.clear()
        if self.is_in_trash_bin:
            rows = self.db.get_deleted_notes()
            self.newNoteBtn.setEnabled(False)
            self.delNoteBtn.setText("恢复")
        else:
            self.newNoteBtn.setEnabled(True)
            self.delNoteBtn.setText("删除")
            if keyword.strip():
                rows = self.db.search_notes(keyword)
            else:
                rows = self.db.get_notes_by_notebook(self.current_notebook_id)
        
        for row in rows:
            note_id, title = row
            item = QtWidgets.QListWidgetItem(title)
            item.setData(QtCore.Qt.UserRole, note_id)
            self.listWidget.addItem(item)

    def bind_signals(self):
        self.treeWidget.itemClicked.connect(self.on_notebook_clicked)
        # 开启树状目录右键菜单及拖拽支持
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenuRequested)
        self.treeWidget.customContextMenuRequested.connect(self.show_notebook_context_menu)
        self.treeWidget.setDragEnabled(True)
        self.treeWidget.setAcceptDrops(True)
        self.treeWidget.setDropIndicatorShown(True)
        self.treeWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.newNotebookBtn.clicked.connect(self.on_new_notebook)
        self.delNotebookBtn.clicked.connect(self.on_delete_notebook)
        
        self.tagListWidget.itemClicked.connect(self.on_tag_clicked)
        self.listWidget.itemDoubleClicked.connect(lambda item: self.open_note_in_tab(item.data(QtCore.Qt.UserRole)))
        self.newNoteBtn.clicked.connect(self.on_new_note)
        self.delNoteBtn.clicked.connect(self.on_delete_or_restore_note)
        
        self.searchLineEdit.textChanged.connect(self.load_notes_list)
        self.tabWidget.tabCloseRequested.connect(self.close_tab_page)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        self.exportBtn.clicked.connect(self.export_note)
        self.themeBtn.clicked.connect(self.toggle_theme)

    def init_shortcuts(self):
        self.shortcut_new = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.on_new_note)
        self.shortcut_search = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(lambda: self.searchLineEdit.setFocus())

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.themeBtn.setText("☀️ 亮色模式" if self.is_dark_mode else "🌙 暗黑模式")
        self.apply_global_theme()
        
        for i in range(self.tabWidget.count()):
            page = self.tabWidget.widget(i)
            if hasattr(page, "line_highlighter"):
                page.line_highlighter.update_theme(self.is_dark_mode)

    def show_notebook_context_menu(self, position):
        item = self.treeWidget.itemAt(position)
        if not item:
            return
        nb_id = item.data(0, QtCore.Qt.UserRole)
        if nb_id == -999:
            return
            
        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction("✏️ 重命名笔记本")
        delete_action = menu.addAction("🗑️ 删除笔记本")
        
        action = menu.exec_(self.treeWidget.mapToGlobal(position))
        if action == rename_action:
            self.rename_notebook(item, nb_id)
        elif action == delete_action:
            self.treeWidget.setCurrentItem(item)
            self.on_delete_notebook()

    def rename_notebook(self, item, nb_id):
        old_name = item.text(0).replace("📁 ", "")
        new_name, ok = QtWidgets.QInputDialog.getText(self, "重命名笔记本", "请输入新的笔记本名称：", text=old_name)
        if ok and new_name.strip():
            clean_name = new_name.strip()
            self.db.update_notebook_name(nb_id, clean_name)
            item.setText(0, f"📁 {clean_name}")
            self.statusbar.showMessage(f"笔记本已重命名为: {clean_name}", 2000)

    def open_note_in_tab(self, note_id):
        for i in range(self.tabWidget.count()):
            page = self.tabWidget.widget(i)
            if getattr(page, "note_id", None) == note_id:
                self.tabWidget.setCurrentIndex(i)
                return

        row = self.db.get_note_by_id(note_id)
        if not row:
            return
            
        title, content, tags, nb_id, is_md, is_deleted = row
        
        page_widget = QtWidgets.QWidget()
        page_layout = QtWidgets.QVBoxLayout(page_widget)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)
        
        page_widget.note_id = note_id
        page_widget.is_loading = True
        page_widget.is_markdown_mode = bool(is_md)
        page_widget.is_read_only = bool(is_deleted)
        page_widget.markdown_source = content if content else ""  # 初始化 Markdown 源码缓存
        
        titleLineEdit = QtWidgets.QLineEdit(page_widget)
        titleLineEdit.setText(title)
        titleLineEdit.setReadOnly(page_widget.is_read_only)
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        titleLineEdit.setFont(font)
        page_layout.addWidget(titleLineEdit)
        page_widget.titleLineEdit = titleLineEdit
        
        tagsLineEdit = QtWidgets.QLineEdit(page_widget)
        tagsLineEdit.setPlaceholderText("添加标签...")
        tagsLineEdit.setText(tags if tags else "")
        tagsLineEdit.setReadOnly(page_widget.is_read_only)
        page_layout.addWidget(tagsLineEdit)
        page_widget.tagsLineEdit = tagsLineEdit
        
        formatContainerLayout = QtWidgets.QVBoxLayout()
        formatContainerLayout.setSpacing(5)
        formatContainerLayout.setContentsMargins(0, 0, 0, 0)
        
        formatRow1 = QtWidgets.QHBoxLayout()
        boldBtn = QtWidgets.QPushButton("加粗", page_widget)
        italicBtn = QtWidgets.QPushButton("斜体", page_widget)
        underlineBtn = QtWidgets.QPushButton("下划线", page_widget)
        fontSizeCombo = QtWidgets.QComboBox(page_widget)
        fontSizeCombo.addItems(["字号", "10", "12", "14", "16", "18", "20", "24", "28"])
        colorBtn = QtWidgets.QPushButton("文字颜色", page_widget)
        indentBtn = QtWidgets.QPushButton("首行缩进", page_widget)
        
        formatRow1.addWidget(boldBtn)
        formatRow1.addWidget(italicBtn)
        formatRow1.addWidget(underlineBtn)
        formatRow1.addWidget(fontSizeCombo)
        formatRow1.addWidget(colorBtn)
        formatRow1.addWidget(indentBtn)
        formatRow1.addSpacerItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        
        formatRow2 = QtWidgets.QHBoxLayout()
        codeBtn = QtWidgets.QPushButton("插入代码", page_widget)
        imageBtn = QtWidgets.QPushButton("🖼️ 插入图片", page_widget)
        markdownModeBtn = QtWidgets.QPushButton("👁️ 预览模式" if page_widget.is_markdown_mode else "📝 Markdown 模式", page_widget)
        
        formatRow2.addWidget(codeBtn)
        formatRow2.addWidget(imageBtn)
        formatRow2.addWidget(markdownModeBtn)
        formatRow2.addSpacerItem(QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        
        formatContainerLayout.addLayout(formatRow1)
        formatContainerLayout.addLayout(formatRow2)
        page_layout.addLayout(formatContainerLayout)
        
        textEdit = CustomTextEdit(page_widget, app_window=self, tab_page=page_widget)
        textEdit.setReadOnly(page_widget.is_read_only)
        highlighter = PythonHighlighter(textEdit.document())
        line_highlighter = CurrentLineHighlighter(textEdit, self.is_dark_mode)
        
        page_widget.textEdit = textEdit
        page_widget.highlighter = highlighter
        page_widget.line_highlighter = line_highlighter
        
        if page_widget.is_markdown_mode:
            textEdit.setPlainText(page_widget.markdown_source)
        else:
            # 初始化预览模式渲染
            raw_html = markdown.markdown(page_widget.markdown_source, extensions=['fenced_code', 'tables', 'nl2br'])
            textEdit.setHtml(raw_html)
            
        page_layout.addWidget(textEdit)
        
        if page_widget.is_read_only:
            for btn in [boldBtn, italicBtn, underlineBtn, fontSizeCombo, colorBtn, indentBtn, codeBtn, imageBtn, markdownModeBtn]:
                btn.setEnabled(False)
            titleLineEdit.setStyleSheet("background-color: #f5f5f5; color: #888;")
            tagsLineEdit.setStyleSheet("background-color: #f5f5f5; color: #888;")
            textEdit.setStyleSheet("background-color: #f9f9f9;")
        else:
            titleLineEdit.textChanged.connect(lambda: self.auto_save(page_widget))
            tagsLineEdit.textChanged.connect(lambda: self.auto_save(page_widget))
            textEdit.textChanged.connect(lambda: self.auto_save(page_widget))
            
            boldBtn.clicked.connect(lambda: self.format_text(page_widget, "bold"))
            italicBtn.clicked.connect(lambda: self.format_text(page_widget, "italic"))
            underlineBtn.clicked.connect(lambda: self.format_text(page_widget, "underline"))
            fontSizeCombo.currentIndexChanged.connect(lambda idx: self.change_font_size(page_widget, idx))
            colorBtn.clicked.connect(lambda: self.change_text_color(page_widget))
            indentBtn.clicked.connect(lambda: self.set_paragraph_indent(page_widget))
            codeBtn.clicked.connect(lambda: self.insert_code_block(page_widget))
            imageBtn.clicked.connect(lambda: self.browse_and_insert_image(page_widget))
            markdownModeBtn.clicked.connect(lambda: self.toggle_markdown_mode(page_widget, markdownModeBtn, boldBtn, italicBtn, underlineBtn, fontSizeCombo, colorBtn))

        textEdit.textChanged.connect(lambda: self.update_word_count(page_widget))
        page_widget.is_loading = False
        
        tab_title = f"[回收站] {title}" if is_deleted else title
        tab_index = self.tabWidget.addTab(page_widget, tab_title)
        self.tabWidget.setCurrentIndex(tab_index)
        self.update_word_count(page_widget)

    def close_tab_page(self, index):
        self.tabWidget.removeTab(index)

    def on_tab_changed(self, index):
        if index != -1:
            page = self.tabWidget.widget(index)
            self.update_word_count(page)

    def auto_save(self, page_widget):
        if getattr(page_widget, "is_loading", False) or getattr(page_widget, "is_read_only", False):
            return
            
        title = page_widget.titleLineEdit.text().strip() or "无标题笔记"
        tags = page_widget.tagsLineEdit.text().strip()
        
        if page_widget.is_markdown_mode:
            content = page_widget.textEdit.toPlainText()
            page_widget.markdown_source = content  # 实时缓存源码
        else:
            content = page_widget.textEdit.toHtml()
            
        is_md = 1 if page_widget.is_markdown_mode else 0
        self.db.update_note(page_widget.note_id, title, content, tags, is_md)
        self.load_tags_list()
        
        current_idx = self.tabWidget.indexOf(page_widget)
        if current_idx != -1:
            self.tabWidget.setTabText(current_idx, title)
            
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.data(QtCore.Qt.UserRole) == page_widget.note_id:
                item.setText(title)
                break
                
        self.statusbar.showMessage("已自动保存", 1500)

    def toggle_markdown_mode(self, page_widget, btn, boldBtn, italicBtn, underlineBtn, fontSizeCombo, colorBtn):
        if not hasattr(page_widget, "markdown_source"):
            page_widget.markdown_source = page_widget.textEdit.toPlainText()

        page_widget.is_markdown_mode = not page_widget.is_markdown_mode
        
        block_bg = "#1e293b" if self.is_dark_mode else "#f1f5f9"
        block_border = "#3b82f6"
        code_bg = "#090d16" if self.is_dark_mode else "#f8fafc"
        text_color = "#e2e8f0" if self.is_dark_mode else "#1e293b"
        border_color = "#334155" if self.is_dark_mode else "#cbd5e1"

        if page_widget.is_markdown_mode:
            btn.setText("👁️ 预览模式")
            boldBtn.setEnabled(False)
            italicBtn.setEnabled(False)
            underlineBtn.setEnabled(False)
            fontSizeCombo.setEnabled(False)
            colorBtn.setEnabled(False)
            
            if hasattr(page_widget, "markdown_source"):
                page_widget.textEdit.setPlainText(page_widget.markdown_source)
        else:
            btn.setText("📝 Markdown 模式")
            boldBtn.setEnabled(True)
            italicBtn.setEnabled(True)
            underlineBtn.setEnabled(True)
            fontSizeCombo.setEnabled(True)
            colorBtn.setEnabled(True)
            
            page_widget.markdown_source = page_widget.textEdit.toPlainText()
            raw_html = markdown.markdown(page_widget.markdown_source, extensions=['fenced_code', 'tables', 'nl2br'])
            
            styled_html = f"""
            <style>
                body {{ color: {text_color}; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; line-height: 1.6; }}
                blockquote {{ background-color: {block_bg}; border-left: 4px solid {block_border}; margin: 10px 0px; padding: 8px 12px; border-radius: 0px 6px 6px 0px; }}
                pre, code {{ background-color: {code_bg}; border: 1px solid {border_color}; border-radius: 6px; padding: 6px; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }}
                h1, h2, h3 {{ border-bottom: 1px solid {border_color}; padding-bottom: 4px; margin-top: 16px; }}
            </style>
            {raw_html}
            """
            page_widget.textEdit.setHtml(styled_html)
            
        self.auto_save(page_widget)

    def on_notebook_clicked(self, item, column):
        nb_id = item.data(0, QtCore.Qt.UserRole)
        if nb_id == -999:
            self.is_in_trash_bin = True
            self.searchLineEdit.clear()
            self.load_notes_list()
            self.statusbar.showMessage("当前处于回收站视图", 2000)
        else:
            self.is_in_trash_bin = False
            self.current_notebook_id = nb_id
            self.searchLineEdit.clear()
            self.load_notes_list()

    def on_tag_clicked(self, item):
        if self.is_in_trash_bin:
            return
        tag = item.data(QtCore.Qt.UserRole)
        self.searchLineEdit.clear()
        self.listWidget.clear()
        
        rows = self.db.get_notes_by_tag(tag)
        for row in rows:
            note_id, title = row
            listItem = QtWidgets.QListWidgetItem(title)
            listItem.setData(QtCore.Qt.UserRole, note_id)
            self.listWidget.addItem(listItem)
        self.statusbar.showMessage(f"已过滤标签: {tag}", 2000)

    def on_new_notebook(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "新建笔记本", "请输入笔记本名称：")
        if ok and name.strip():
            self.db.add_notebook(name.strip())
            self.load_notebooks_tree()
            last_item = self.treeWidget.topLevelItem(self.treeWidget.topLevelItemCount() - 2)
            self.treeWidget.setCurrentItem(last_item)
            self.current_notebook_id = last_item.data(0, QtCore.Qt.UserRole)
            self.is_in_trash_bin = False
            self.load_notes_list()

    def on_delete_notebook(self):
        current_item = self.treeWidget.currentItem()
        if not current_item:
            return
        nb_id = current_item.data(0, QtCore.Qt.UserRole)
        if nb_id == -999:
            QtWidgets.QMessageBox.warning(self, "警告", "无法删除回收站系统目录！")
            return
        if self.treeWidget.topLevelItemCount() <= 2:
            QtWidgets.QMessageBox.warning(self, "警告", "必须保留至少一个笔记本分类！")
            return
            
        reply = QtWidgets.QMessageBox.question(self, "确认删除", "删除笔记本将同时删除其下的所有笔记，是否继续？",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.delete_notebook(nb_id)
            self.load_notebooks_tree()
            self.load_tags_list()

    def on_new_note(self):
        if self.is_in_trash_bin:
            return
        self.db.add_note(self.current_notebook_id, "新建笔记", "# 新笔记内容\n```python\nprint('Hello')\n```", "Python", 0)
        self.searchLineEdit.clear()
        self.load_notes_list()
        self.load_tags_list()
        newest_row = self.db.get_notes_by_notebook(self.current_notebook_id)[0]
        self.open_note_in_tab(newest_row[0])

    def on_delete_or_restore_note(self):
        current_item = self.listWidget.currentItem()
        if not current_item:
            return
        note_id = current_item.data(QtCore.Qt.UserRole)
        
        if self.is_in_trash_bin:
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("回收站管理")
            box.setText("请选择对该笔记的操作：")
            restore_btn = box.addButton("还原笔记", QtWidgets.QMessageBox.AcceptRole)
            perm_del_btn = box.addButton("彻底销毁", QtWidgets.QMessageBox.DestructiveRole)
            cancel_btn = box.addButton("取消", QtWidgets.QMessageBox.RejectRole)
            box.exec_()
            
            if box.clickedButton() == restore_btn:
                self.db.restore_note(note_id)
                for i in range(self.tabWidget.count()):
                    page = self.tabWidget.widget(i)
                    if getattr(page, "note_id", None) == note_id:
                        self.tabWidget.removeTab(i)
                        break
                self.load_notes_list()
                self.load_tags_list()
                self.statusbar.showMessage("笔记已成功恢复", 2000)
            elif box.clickedButton() == perm_del_btn:
                reply = QtWidgets.QMessageBox.warning(self, "警告", "彻底销毁后将无法找回，确定要永久删除吗？",
                                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if reply == QtWidgets.QMessageBox.Yes:
                    for i in range(self.tabWidget.count()):
                        page = self.tabWidget.widget(i)
                        if getattr(page, "note_id", None) == note_id:
                            self.tabWidget.removeTab(i)
                            break
                    self.db.permanent_delete_note(note_id)
                    self.load_notes_list()
                    self.statusbar.showMessage("笔记已被彻底销毁", 2000)
        else:
            if self.db.count_active_notes() <= 1:
                QtWidgets.QMessageBox.warning(self, "警告", "必须保留至少一篇活跃笔记！")
                return
                
            for i in range(self.tabWidget.count()):
                page = self.tabWidget.widget(i)
                if getattr(page, "note_id", None) == note_id:
                    self.tabWidget.removeTab(i)
                    break
                    
            self.db.soft_delete_note(note_id)
            self.load_notes_list(self.searchLineEdit.text())
            self.load_tags_list()
            self.statusbar.showMessage("笔记已移至回收站", 2000)

    def update_word_count(self, page_widget):
        if self.tabWidget.currentWidget() == page_widget:
            text = page_widget.textEdit.toPlainText()
            total_chars = len(text)
            chars_no_space = len(text.replace(" ", "").replace("\n", ""))
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fa5'])
            paragraphs = len([p for p in text.split('\n') if p.strip()])
            reading_time_mins = max(1, round(chars_no_space / 350)) if chars_no_space > 0 else 0
            
            status_text = (
                f"字符数: {total_chars} (不含空格: {chars_no_space}) | "
                f"中文汉字: {chinese_chars} | 段落: {paragraphs} | 预估阅读: 约 {reading_time_mins} 分钟"
            )
            self.statusbar.showMessage(status_text, 0)

    def format_text(self, page_widget, action):
        if page_widget.is_markdown_mode or getattr(page_widget, "is_read_only", False):
            return
        cursor = page_widget.textEdit.textCursor()
        fmt = QtGui.QTextCharFormat()
        if action == "bold":
            fmt.setFontWeight(QtGui.QTextCharFormat.Bold if cursor.charFormat().fontWeight() != QtGui.QTextCharFormat.Bold else QtGui.QTextCharFormat.Normal)
        elif action == "italic":
            fmt.setFontItalic(not cursor.charFormat().fontItalic())
        elif action == "underline":
            fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(fmt)

    def change_font_size(self, page_widget, index):
        if page_widget.is_markdown_mode or index == 0 or getattr(page_widget, "is_read_only", False):
            return
        cursor = page_widget.textEdit.textCursor()
        fmt = QtGui.QTextCharFormat()
        fmt.setFontPointSize(14)
        cursor.mergeCharFormat(fmt)

    def change_text_color(self, page_widget):
        if page_widget.is_markdown_mode or getattr(page_widget, "is_read_only", False):
            return
        color = QtWidgets.QColorDialog.getColor(QtCore.Qt.black, self, "选择文字颜色")
        if color.isValid():
            cursor = page_widget.textEdit.textCursor()
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(color)
            cursor.mergeCharFormat(fmt)

    def set_paragraph_indent(self, page_widget):
        if page_widget.is_markdown_mode or getattr(page_widget, "is_read_only", False):
            return
        cursor = page_widget.textEdit.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setTextIndent(40.0 if block_fmt.textIndent() == 0 else 0.0)
        cursor.setBlockFormat(block_fmt)

    def insert_code_block(self, page_widget):
        if getattr(page_widget, "is_read_only", False):
            return
        cursor = page_widget.textEdit.textCursor()
        if page_widget.is_markdown_mode:
            cursor.insertText("```python\n# 输入代码\ndef hello():\n    print('Hello')\n```\n")
        else:
            cursor.insertHtml(get_code_block_html())

    def browse_and_insert_image(self, page_widget):
        if getattr(page_widget, "is_read_only", False):
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            image = QtGui.QImage(file_path)
            if not image.isNull():
                self.save_and_insert_image(image, page_widget)

    def save_and_insert_image(self, image: QtGui.QImage, page_widget):
        assets_dir = "assets"
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
        file_name = f"img_{int(time.time() * 1000)}.png"
        file_path = os.path.join(assets_dir, file_name)
        if image.save(file_path, "PNG"):
            cursor = page_widget.textEdit.textCursor()
            if page_widget.is_markdown_mode:
                cursor.insertText(f"![image]({file_path})\n")
            else:
                cursor.insertHtml(f'<p><img src="{file_path}" style="max-width: 100%; height: auto;"/></p>')
            self.statusbar.showMessage("图片插入成功", 1500)

    def export_note(self):
        current_page = self.tabWidget.currentWidget()
        if not current_page:
            QtWidgets.QMessageBox.warning(self, "提示", "当前没有可导出的活动标签页笔记！")
            return
        title = current_page.titleLineEdit.text().strip() or "未命名笔记"
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出笔记", f"{safe_title}.html", "HTML 文件 (*.html);; 文本文件 (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    content_to_export = current_page.textEdit.toPlainText()
                    if file_path.endswith(".html"):
                        rendered = markdown.markdown(content_to_export, extensions=['fenced_code', 'tables']) if current_page.is_markdown_mode else current_page.textEdit.toHtml()
                        f.write(f"<html><head><meta charset='utf-8'><title>{title}</title></head><body><h1>{title}</h1>{rendered}</body></html>")
                    else:
                        f.write(f"{title}\n" + "="*30 + f"\n\n{content_to_export}")
                QtWidgets.QMessageBox.information(self, "成功", f"导出成功：\n{file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")