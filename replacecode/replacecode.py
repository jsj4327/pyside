import sys
import ast
import difflib
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPlainTextEdit, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QLabel, QAction,
    QTabWidget, QTextEdit
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeySequence, QTextCursor, QColor, QTextFormat


class CodeRefactorTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Git 风格局部精准重构工具")
        self.resize(1200, 750)

        # 存储解析出来的待应用补丁任务：[(start_line, end_line, patch_lines, description), ...]
        self.pending_patches = []

        self.init_ui()
        self.init_menu()
        self.parse_outline()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # ================= 左侧：源代码编辑器 =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("Python 源代码 (左侧基准)")
        self.editor = QPlainTextEdit()
        default_code = (
            "class MyTool:\n"
            "    def __init__(self):\n"
            "        self.status = True\n\n"
            "    def open_file(self):\n"
            "        print('Open')\n\n"
            "    def save_file(self):\n"
            "        print('Save')\n"
        )
        self.editor.setPlainText(default_code)
        self.editor.textChanged.connect(self.clear_preview_state)

        left_layout.addWidget(left_label)
        left_layout.addWidget(self.editor)

        # ================= 右侧：使用 QTabWidget =================
        self.right_tabs = QTabWidget()

        # --- Tab 1: 局部结构补丁分析 ---
        self.tab_diff = QWidget()
        diff_layout = QVBoxLayout(self.tab_diff)

        diff_label = QLabel("在此粘贴修改后的函数或类代码:")
        self.paste_editor = QPlainTextEdit()
        self.paste_editor.setPlaceholderText("粘贴你需要更新的特定函数或类片段...")
        self.paste_editor.textChanged.connect(self.clear_preview_state)

        btn_layout = QHBoxLayout()
        self.btn_analyze = QPushButton("🔍 1. 分析局部补丁并预览")
        self.btn_analyze.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.btn_analyze.clicked.connect(self.analyze_patch_and_preview)

        self.btn_confirm = QPushButton("✅ 2. 应用补丁 (Commit)")
        self.btn_confirm.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.apply_patches)

        btn_layout.addWidget(self.btn_analyze)
        btn_layout.addWidget(self.btn_confirm)

        self.diff_display = QTextEdit()
        self.diff_display.setReadOnly(True)
        self.diff_display.setPlaceholderText("这里将展示 Git 风格的函数级 Diff 预览...")

        diff_layout.addWidget(diff_label)
        diff_layout.addWidget(self.paste_editor, stretch=2)
        diff_layout.addLayout(btn_layout)
        diff_layout.addWidget(self.diff_display, stretch=3)

        # --- Tab 2: 代码大纲 ---
        self.tab_ast = QWidget()
        ast_layout = QVBoxLayout(self.tab_ast)
        self.btn_refresh = QPushButton("刷新结构树")
        self.btn_refresh.clicked.connect(self.parse_outline)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["代码大纲速览"])
        self.tree_widget.itemDoubleClicked.connect(self.insert_snippet_from_tree)
        ast_layout.addWidget(self.btn_refresh)
        ast_layout.addWidget(self.tree_widget)

        self.right_tabs.addTab(self.tab_diff, "Git 局部补丁合并")
        self.right_tabs.addTab(self.tab_ast, "代码大纲")

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.right_tabs)
        self.splitter.setSizes([650, 550])

    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件(&F)")
        open_action = QAction("打开源文件(&O)", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)

    def clear_preview_state(self):
        """清除高亮状态和待处理补丁"""
        self.editor.setExtraSelections([])
        self.pending_patches.clear()
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setText("✅ 2. 应用补丁 (Commit)")

    @staticmethod
    def get_source_segment(code, node):
        if hasattr(ast, 'get_source_segment'):
            return ast.get_source_segment(code, node)
        else:
            lines = code.splitlines(keepends=True)
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', start + 1)
            return ''.join(lines[start:end])

    # ---------- 核心：Git 风格的局部函数/类补丁匹配与合并 ----------
    def analyze_patch_and_preview(self):
        self.clear_preview_state()
        new_code = self.paste_editor.toPlainText().strip()
        base_code = self.editor.toPlainText()

        if not new_code:
            QMessageBox.warning(self, "提示", "请先在右侧粘贴需要修改的代码。")
            return

        try:
            new_tree = ast.parse(new_code)
            base_tree = ast.parse(base_code)
        except SyntaxError as e:
            QMessageBox.warning(self, "语法错误", f"代码存在语法错误，无法解析:\n{e}")
            return

        base_lines = base_code.splitlines(keepends=True)

        # 辅助函数：通过递归扫描子节点确保完整包裹，解决高亮行偏差问题
        def get_node_exact_range(node):
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line)
            for child in ast.walk(node):
                if hasattr(child, 'end_lineno') and child.end_lineno:
                    if child.end_lineno > end_line:
                        end_line = child.end_lineno
            return start_line, end_line

        def get_node_map(tree):
            node_map = {}
            def walk(node, prefix=""):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.ClassDef):
                        name = f"{prefix}.{child.name}" if prefix else child.name
                        node_map[name] = child
                        walk(child, name)
                    elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        name = f"{prefix}.{child.name}" if prefix else child.name
                        node_map[name] = child
                        walk(child, name)
            walk(tree)
            return node_map

        base_map = get_node_map(base_tree)
        new_map = get_node_map(new_tree)

        highlight_regions = []
        log_html = "<div style='font-family: Consolas, monospace;'>"
        self.pending_patches = []

        for path_name, new_node in new_map.items():
            new_segment = self.get_source_segment(new_code, new_node)
            if not new_segment:
                continue

            target_node = None
            match_desc = ""

            if path_name in base_map:
                target_node = base_map[path_name]
                match_desc = f"精准匹配: {path_name}"
            else:
                short_name = path_name.split('.')[-1]
                for b_name, b_node in base_map.items():
                    if b_name.split('.')[-1] == short_name and type(b_node) == type(new_node):
                        target_node = b_node
                        match_desc = f"降级匹配: {short_name} (对应左侧 {b_name})"
                        break

            if target_node:
                start_line, end_line = get_node_exact_range(target_node)
                base_segment = ''.join(base_lines[start_line-1:end_line])

                if base_segment:
                    new_lines_list = new_segment.splitlines(keepends=True)
                    if new_lines_list and not new_lines_list[-1].endswith('\n'):
                        new_lines_list[-1] += '\n'

                    self.pending_patches.append((start_line, end_line, new_lines_list, path_name))
                    highlight_regions.append((start_line, end_line))

                    diff = list(difflib.unified_diff(
                        base_segment.splitlines(),
                        new_segment.splitlines(),
                        fromfile=f"a/{path_name}",
                        tofile=f"b/{path_name}",
                        lineterm=''
                    ))

                    log_html += f"<h3>{match_desc}</h3>"
                    if not diff:
                        log_html += "<span style='color: gray;'>内容完全一致，无变更。</span><br>"
                    else:
                        log_html += "<div style='background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 6px; border-radius: 4px;'>"
                        for line in diff:
                            safe_line = line.replace('<', '&lt;').replace('>', '&gt;')
                            if line.startswith('+') and not line.startswith('+++'):
                                log_html += f"<span style='color: #28a745; font-weight: bold;'>{safe_line}</span><br>"
                            elif line.startswith('-') and not line.startswith('---'):
                                log_html += f"<span style='color: #dc3545; font-weight: bold;'>{safe_line}</span><br>"
                            elif line.startswith('@@'):
                                log_html += f"<span style='color: #6c757d; font-style: italic;'>{safe_line}</span><br>"
                            else:
                                log_html += f"<span style='color: #495057;'>{safe_line}</span><br>"
                        log_html += "</div><br>"
            else:
                log_html += f"<h3>跳过: {path_name}</h3>"
                log_html += f"<span style='color: #dc3545;'>左侧未找到对应的结构。</span><br><br>"

        log_html += "</div>"
        self.diff_display.setHtml(log_html)

        if highlight_regions:
            self.highlight_and_scroll_to_regions(highlight_regions)
            self.btn_confirm.setEnabled(True)
            self.btn_confirm.setText(f"✅ 2. 应用补丁 ({len(self.pending_patches)} 个变更)")

    def highlight_and_scroll_to_regions(self, regions):
        extra_selections = []
        highlight_color = QColor("#FFF9C4")
        if not regions:
            return

        first_line = regions[0][0]

        for start_line, end_line in regions:
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(highlight_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)

            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, start_line - 1)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, max(1, end_line - start_line))

            selection.cursor = cursor
            extra_selections.append(selection)

        self.editor.setExtraSelections(extra_selections)

        scroll_cursor = self.editor.textCursor()
        scroll_cursor.movePosition(QTextCursor.Start)
        scroll_cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, first_line - 1)
        self.editor.setTextCursor(scroll_cursor)
        self.editor.centerCursor()

    def apply_patches(self):
        """严格受控的边界切片替换，杜绝新代码长于旧代码时的越界风险"""
        if not self.pending_patches:
            return

        base_text = self.editor.toPlainText()
        lines = base_text.splitlines(keepends=True)

        # 核心：按起始行号倒序排列，防止前面补丁的行数伸缩影响后面补丁的坐标
        sorted_patches = sorted(self.pending_patches, key=lambda x: x[0], reverse=True)

        for start_line, end_line, new_lines, path_name in sorted_patches:
            start_idx = start_line - 1
            end_idx = end_line
            
            if start_idx < 0 or start_idx > len(lines):
                continue
            end_idx = min(end_idx, len(lines))

            # 固定槽位精确替换，绝不波及后续代码
            lines[start_idx:end_idx] = new_lines

        self.editor.setPlainText(''.join(lines))
        self.clear_preview_state()
        self.diff_display.setHtml("<span style='color: green; font-weight: bold;'>补丁已安全提交并完美合并！</span>")
        QMessageBox.information(self, "成功", "局部补丁已成功合并，未产生越界覆盖。")
        self.parse_outline()

    # ---------- 辅助：大纲树 ----------
    def parse_outline(self):
        self.tree_widget.clear()
        source_code = self.editor.toPlainText()
        try:
            tree = ast.parse(source_code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    c_item = QTreeWidgetItem(self.tree_widget, [f"class {node.name}"])
                    c_item.setData(0, Qt.UserRole, self.get_source_segment(source_code, node))
                    for sub in node.body:
                        if isinstance(sub, ast.FunctionDef):
                            m_item = QTreeWidgetItem(c_item, [f"def {sub.name}()"])
                            m_item.setData(0, Qt.UserRole, self.get_source_segment(source_code, sub))
                elif isinstance(node, ast.FunctionDef):
                    f_item = QTreeWidgetItem(self.tree_widget, [f"def {node.name}()"])
                    f_item.setData(0, Qt.UserRole, self.get_source_segment(source_code, node))
            self.tree_widget.expandAll()
        except Exception:
            pass

    def insert_snippet_from_tree(self, item):
        snippet = item.data(0, Qt.UserRole)
        if snippet:
            cursor = self.editor.textCursor()
            cursor.insertText(snippet)
            self.editor.setFocus()

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开 Python 文件", "", "Python Files (*.py);;All Files (*)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self.parse_outline()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件失败：{e}")

    def save_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "Python Files (*.py);;All Files (*)")
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeRefactorTool()
    window.show()
    sys.exit(app.exec_())