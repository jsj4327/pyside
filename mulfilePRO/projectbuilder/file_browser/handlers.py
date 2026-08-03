# file_browser/handlers.py
import os
from PySide2.QtWidgets import (
    QMenu, QAction, QMessageBox, QApplication, QDialog,
    QVBoxLayout, QTextEdit, QDialogButtonBox, QLabel, QTreeWidgetItem
)
from PySide2.QtCore import Qt, QEvent
from PySide2.QtGui import QFont

from run_manager import RunManager


class EventHandlers:
    def __init__(self, parent):
        self.parent = parent
        self.ui = parent.ui
        self.ops = parent.ops

    def event_filter(self, obj, event):
        if obj == self.ui.tree and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                current = self.ui.tree.currentItem()
                if current:
                    self.on_item_double_clicked(current, 0)
                return True
            elif key == Qt.Key_Backspace:
                self.parent._go_up()
                return True
            elif key == Qt.Key_F5:
                self.parent.refresh()
                return True
            elif key == Qt.Key_Delete:
                self.ops.delete_selected_items()
                return True
        return False

    def on_item_double_clicked(self, item, column):
        path = item.data(0, Qt.UserRole + 1)
        if not path:
            return
        if os.path.isdir(path):
            self.parent.load_directory(path)
        else:
            self.parent.file_double_clicked.emit(path)

    def on_item_clicked(self, item, column):
        path = item.data(0, Qt.UserRole + 1)
        if path:
            self.parent.file_selected.emit(path)

    def show_context_menu(self, position):
        selected_items = self.ui.tree.selectedItems()
        item_at_pos = self.ui.tree.itemAt(position)

        if item_at_pos:
            if item_at_pos not in selected_items:
                self.ui.tree.clearSelection()
                item_at_pos.setSelected(True)
                selected_items = [item_at_pos]
        else:
            self.ui.tree.clearSelection()
            selected_items = []

        target_path = item_at_pos.data(0, Qt.UserRole + 1) if item_at_pos else self.parent.current_path
        is_dir = os.path.isdir(target_path) if target_path else True

        menu = QMenu(self.parent)

        if item_at_pos:
            action_open = QAction("📂 在文件管理器中打开", self.parent)
            action_open.triggered.connect(lambda: self.ops.open_in_file_manager(target_path))
            menu.addAction(action_open)

            action_copy = QAction("📋 复制绝对路径", self.parent)
            action_copy.triggered.connect(lambda: self.ops.copy_path(target_path))
            menu.addAction(action_copy)
            menu.addSeparator()

        parent_dir = target_path if (is_dir and target_path) else os.path.dirname(target_path or self.parent.current_path)

        action_new_folder = QAction("📁 新建文件夹...", self.parent)
        action_new_folder.triggered.connect(lambda: self.ops.create_folder(parent_dir))
        menu.addAction(action_new_folder)

        action_new_file = QAction("📄 新建文件...", self.parent)
        action_new_file.triggered.connect(lambda: self.ops.create_file(parent_dir))
        menu.addAction(action_new_file)

        if selected_items:
            menu.addSeparator()
            count = len(selected_items)
            if count > 1:
                action_delete = QAction(f"🗑 删除选中的 {count} 个项目", self.parent)
            else:
                name = os.path.basename(selected_items[0].data(0, Qt.UserRole + 1))
                action_delete = QAction(f"🗑 删除 '{name}'", self.parent)
            action_delete.triggered.connect(self.ops.delete_selected_items)
            menu.addAction(action_delete)

            if count == 1:
                action_rename = QAction("✏️ 重命名", self.parent)
                action_rename.triggered.connect(lambda: self.ops.rename_item(selected_items[0], target_path))
                menu.addAction(action_rename)

                menu.addSeparator()
                action_props = QAction("ℹ️ 属性", self.parent)
                action_props.triggered.connect(lambda: self.ops.show_properties(target_path))
                menu.addAction(action_props)

        global_pos = self.ui.tree.viewport().mapToGlobal(position)
        menu.exec_(global_pos)

    # ---------- 运行按钮逻辑 ----------
    def on_run_clicked(self):
        """运行逻辑：优先运行选中的py文件，若无选中则查找main.py"""
        path = self.parent.current_path
        if not os.path.isdir(path):
            self.ui.status_label.setText("❌ 当前路径无效")
            return

        self.ui.output_text.clear()
        self.ui.output_text.append(f"🚀 运行项目: {path}")
        self.ui.output_text.append("-" * 60)

        selected_item = self.ui.tree.currentItem()
        selected_path = selected_item.data(0, Qt.UserRole + 1) if selected_item else None

        target_file = None

        if selected_path and os.path.isfile(selected_path):
            if selected_path.lower().endswith('.py'):
                target_file = selected_path
                self.ui.output_text.append(f"📄 运行选中文件: {os.path.basename(selected_path)}")
            else:
                msg = f"❌ 选中的文件不是 Python 文件: {os.path.basename(selected_path)}"
                self.ui.output_text.append(msg)
                self.ui.status_label.setText("❌ 不是 Python 文件")
                return
        else:
            self.ui.output_text.append("📄 未选中文件，自动查找 main.py")
            main_file = RunManager.find_main_py(path)
            if main_file is None:
                msg = "❌ 未找到 main.py（忽略大小写）"
                self.ui.output_text.append(msg)
                self.ui.status_label.setText(msg)
                return
            target_file = main_file
            self.ui.output_text.append(f"📄 入口文件: {os.path.basename(main_file)}")

        self.ui.output_text.append("⏳ 运行中...\n")

        success, stdout, stderr = RunManager.run_python_file(target_file, capture_output=True)

        if stdout:
            self.ui.output_text.append("【标准输出】")
            self.ui.output_text.append(stdout)
        if stderr:
            self.ui.output_text.append("【错误输出】")
            self.ui.output_text.append(stderr)

        if success:
            self.ui.output_text.append("\n✅ 运行完成 (退出码 0)")
            self.ui.status_label.setText("✅ 运行成功")
        else:
            self.ui.output_text.append("\n❌ 运行失败")
            self.ui.status_label.setText("❌ 运行失败")

        self.ui.output_text.verticalScrollBar().setValue(
            self.ui.output_text.verticalScrollBar().maximum()
        )

    # ---------- 架构文本生成 ----------
    def show_text_architecture_dialog(self):
        if not self.parent.current_path or not os.path.exists(self.parent.current_path):
            QMessageBox.warning(self.parent, "错误", "当前路径无效！")
            return

        dialog = QDialog(self.parent)
        dialog.setWindowTitle("根据树状文本架构生成文件和文件夹")
        dialog.resize(650, 500)

        layout = QVBoxLayout(dialog)
        tip_label = QLabel("请在下方粘贴您的树状目录结构文本（支持顶级根目录、缩进层级、│ 及 # 注释）：")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Consolas", 10))
        text_edit.setPlaceholderText(
            "例如：\n"
            "ProjectBuilder/\n"
            "│\n"
            "├── app.py                            # 程序入口\n"
            "├── main_window.py                    # 主窗口\n"
            "└── file_manager.py                   # 文件管理器"
        )
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("开始生成")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")

        def parse_and_create():
            raw_text = text_edit.toPlainText()
            if not raw_text.strip():
                QMessageBox.warning(dialog, "提示", "请输入有效的架构文本！")
                return

            lines = raw_text.splitlines()
            stack = []
            try:
                for line in lines:
                    stripped_full = line.strip()
                    if not stripped_full or stripped_full in ['│', '|']:
                        continue

                    line_without_comment = line.split('#')[0]
                    if not line_without_comment.strip():
                        continue

                    indent_level = 0
                    for char in line:
                        if char in [' ', '\t', '│', '├', '└', '─']:
                            indent_level += 1
                        else:
                            break

                    cleaned = line_without_comment.strip()
                    for prefix in ['├──', '└──', '│', '|', '─']:
                        cleaned = cleaned.replace(prefix, '')
                    cleaned = cleaned.strip()

                    if not cleaned:
                        continue

                    is_dir = cleaned.endswith('/') or ('.' not in cleaned and not cleaned.startswith('.'))
                    if cleaned.endswith('/'):
                        cleaned = cleaned.rstrip('/')

                    if not cleaned:
                        continue

                    while stack and stack[-1][0] >= indent_level:
                        stack.pop()

                    parent_dir = stack[-1][1] if stack else self.parent.current_path
                    current_path = os.path.join(parent_dir, cleaned)

                    if is_dir:
                        os.makedirs(current_path, exist_ok=True)
                        stack.append((indent_level, current_path))
                    else:
                        dir_name = os.path.dirname(current_path)
                        if dir_name and not os.path.exists(dir_name):
                            os.makedirs(dir_name, exist_ok=True)
                        if not os.path.exists(current_path):
                            with open(current_path, 'w', encoding='utf-8') as f:
                                f.write("")

                self.parent.refresh()
                QMessageBox.information(dialog, "成功", "已成功生成嵌套文件与目录！")
                self.ui.status_label.setText("📁 架构解析与生成成功")
                dialog.accept()

            except Exception as e:
                QMessageBox.warning(dialog, "错误", f"解析或生成文件时出错:\n{str(e)}")

        button_box.accepted.connect(parse_and_create)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(button_box)
        dialog.exec_()

    # ---------- 导出目录树 ----------
    def export_directory_tree(self):
        if not self.parent.current_path or not os.path.exists(self.parent.current_path):
            QMessageBox.warning(self.parent, "错误", "当前路径无效！")
            return

        def generate_tree(dir_path, prefix=""):
            tree_str = ""
            try:
                entries = sorted(os.listdir(dir_path))
                if not self.parent.show_hidden:
                    entries = [e for e in entries if not e.startswith('.')]

                filtered_entries = []
                for entry in entries:
                    excluded = False
                    for pattern in self.parent.exclude_patterns:
                        if pattern in entry or (pattern.startswith('*') and entry.endswith(pattern[1:])):
                            excluded = True
                            break
                    if not excluded:
                        filtered_entries.append(entry)
                entries = filtered_entries

                count = len(entries)
                for i, entry in enumerate(entries):
                    connector = "└── " if i == count - 1 else "├── "
                    path = os.path.join(dir_path, entry)
                    is_dir = os.path.isdir(path)
                    display_name = entry + "/" if is_dir else entry
                    tree_str += f"{prefix}{connector}{display_name}\n"
                    if is_dir:
                        extension = "    " if i == count - 1 else "│   "
                        tree_str += generate_tree(path, prefix + extension)
            except Exception:
                pass
            return tree_str

        root_name = os.path.basename(self.parent.current_path) or self.parent.current_path
        result_text = f"项目路径: {self.parent.current_path}\n\n{root_name}/\n" + generate_tree(self.parent.current_path)

        dialog = QDialog(self.parent)
        dialog.setWindowTitle("导出目录结构")
        dialog.resize(650, 500)

        dialog_layout = QVBoxLayout(dialog)
        tip_label = QLabel("您可以直接在此对话框中查看、全选、复制生成的项目目录树结构：")
        dialog_layout.addWidget(tip_label)

        text_edit = QTextEdit()
        text_edit.setFont(QFont("Consolas", 10))
        text_edit.setText(result_text)
        dialog_layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn = button_box.button(QDialogButtonBox.Ok)
        ok_btn.setText("关闭")

        btn_copy_all = button_box.addButton("复制全部", QDialogButtonBox.ActionRole)

        def handle_copy():
            text_edit.selectAll()
            text_edit.copy()
            self.ui.status_label.setText("📋 目录树结构已成功复制到剪贴板！")
            QMessageBox.information(dialog, "成功", "已成功将目录结构复制到剪贴板！")

        btn_copy_all.clicked.connect(handle_copy)
        button_box.accepted.connect(dialog.accept)

        dialog_layout.addWidget(button_box)
        dialog.exec_()