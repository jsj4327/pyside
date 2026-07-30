# -*- coding: utf-8 -*-
import sys
import os
import re
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QGroupBox,
    QMessageBox,
    QInputDialog,
    QMenu,
    QAction,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
)
from PySide2.QtCore import Qt, QThread, Signal, QUrl, QSettings
from PySide2.QtGui import QFont, QDesktopServices


# ==========================================
# 自定义导入文本对话框
# ==========================================
class ImportTextDialog(QDialog):
    def __init__(self, parent=None, default_text=""):
        super().__init__(parent)
        self.setWindowTitle("导入/编辑文本结构")

        if parent:
            parent_size = parent.size()
            self.resize(int(parent_size.width() * 0.8), int(parent_size.height() * 0.8))
        else:
            self.resize(800, 500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请粘贴或编辑目录树文本（导入后将完整覆盖当前树）:"))

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier New", 10))
        self.text_edit.setPlainText(default_text)
        layout.addWidget(self.text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_text(self):
        return self.text_edit.toPlainText()


# ==========================================
# 自定义导出路径对话框 (给 AI 使用)
# ==========================================
class ExportPathsDialog(QDialog):
    def __init__(self, parent=None, paths_text=""):
        super().__init__(parent)
        self.setWindowTitle("导出项目文件路径 (可直接发给 AI)")

        if parent:
            parent_size = parent.size()
            self.resize(int(parent_size.width() * 0.7), int(parent_size.height() * 0.7))
        else:
            self.resize(650, 450)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("已按树状控件顺序遍历生成路径列表（文件夹结尾带 '/'）："))

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier New", 10))
        self.text_edit.setPlainText(paths_text)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("一键复制到剪贴板")
        btn_copy.setFixedHeight(32)
        btn_copy.setStyleSheet("font-weight: bold;")
        btn_copy.clicked.connect(self.copy_to_clipboard)

        btn_close = QPushButton("关闭")
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        QMessageBox.information(
            self, "提示", "所有路径已成功复制到剪贴板！可以直接粘贴给 AI。"
        )


# ==========================================
# 核心逻辑：树结构构建器与解析器
# ==========================================
class TreeStructureHelper:
    @staticmethod
    def parse_text_to_list(text):
        """解析树状文本为扁平列表 [(full_path, is_file), ...]，具备强容错性"""
        lines = text.splitlines()
        structure = []
        path_stack = []  # 保存 (name, depth)

        for line in lines:
            # 1. 过滤注释
            if "#" in line:
                line_content = line.split("#")[0]
            else:
                line_content = line

            # 2. 替换空格和 Tab 键归一化
            line_content = line_content.replace("\xa0", " ").replace("\t", " ")

            # 3. 快速过滤无内容的线条行
            cleaned_test = re.sub(r"[\s│├└─\|\-\\ ]+", "", line_content)
            if not cleaned_test:
                continue

            # 4. 定位有效文件/文件夹名称的起点
            match = re.search(r"[^│├└─\|\-\\ \t]", line_content)
            if not match:
                continue

            start_idx = match.start()
            raw_name = line_content[start_idx:].strip()
            if not raw_name:
                continue

            # 5. 深度计算逻辑
            prefix = line_content[:start_idx]
            clean_prefix = re.sub(r"[│├└─\|\-]", " ", prefix)
            indent_spaces = len(clean_prefix)

            if indent_spaces == 0:
                depth = 0
            else:
                depth = (indent_spaces + 2) // 4
                if depth == 0:
                    depth = 1

            # 6. 判断类型 (文件 vs 文件夹)
            is_file = True
            if raw_name.endswith("/"):
                is_file = False
                raw_name = raw_name.rstrip("/")
            elif "." not in raw_name:
                is_file = False

            # 7. 栈维护全路径
            while path_stack and path_stack[-1][1] >= depth:
                path_stack.pop()

            if path_stack:
                full_path = os.path.join(*[p[0] for p in path_stack], raw_name)
            else:
                full_path = raw_name

            path_stack.append((raw_name, depth))
            structure.append((full_path, is_file))

        return structure

    @staticmethod
    def build_tree_from_structure(structure, tree_widget):
        """清空原有节点，并按传入的结构列表重建 QTreeWidget"""
        tree_widget.clear()

        node_cache = {}
        root = tree_widget.invisibleRootItem()

        for full_path, is_file in structure:
            parts = full_path.replace("/", os.sep).replace("\\", os.sep).split(os.sep)
            current_parent = root

            for i, part in enumerate(parts):
                is_last_part = i == len(parts) - 1
                part_is_file = is_file if is_last_part else False
                current_path_str = os.sep.join(parts[: i + 1])

                if current_path_str in node_cache:
                    current_parent = node_cache[current_path_str]
                    continue

                item = QTreeWidgetItem(current_parent)
                item.setText(0, part)

                if part_is_file:
                    item.setIcon(
                        0, tree_widget.style().standardIcon(tree_widget.style().SP_FileIcon)
                    )
                    item.setData(0, Qt.UserRole, "file")
                else:
                    item.setIcon(
                        0, tree_widget.style().standardIcon(tree_widget.style().SP_DirIcon)
                    )
                    item.setData(0, Qt.UserRole, "folder")

                node_cache[current_path_str] = item
                current_parent = item

        tree_widget.expandAll()

    @staticmethod
    def get_structure_from_tree(tree_widget):
        """提取树中的节点为全路径列表"""
        structure = []

        def recurse(item, current_path_parts):
            name = item.text(0)
            type_role = item.data(0, Qt.UserRole)

            if type_role is None:
                is_file = "." in name and not name.endswith("/")
                type_role = "file" if is_file else "folder"

            new_path_parts = current_path_parts + [name]
            full_path = os.path.join(*new_path_parts)
            is_file = type_role == "file"

            structure.append((full_path, is_file))

            for i in range(item.childCount()):
                recurse(item.child(i), new_path_parts)

        root = tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            recurse(root.child(i), [])

        return structure

    @staticmethod
    def tree_to_text(tree_widget):
        """将当前 QTreeWidget 逆向渲染为标准 ASCII 树状文本"""
        lines = []

        def recurse(item, prefix=""):
            count = item.childCount()
            for i in range(count):
                child = item.child(i)
                is_last = i == count - 1
                connector = "└── " if is_last else "├── "

                name = child.text(0)
                type_role = child.data(0, Qt.UserRole)
                display_name = (
                    name + "/" if type_role == "folder" and not name.endswith("/") else name
                )

                lines.append(prefix + connector + display_name)

                new_prefix = prefix + ("    " if is_last else "│   ")
                recurse(child, new_prefix)

        root = tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            name = item.text(0)
            type_role = item.data(0, Qt.UserRole)
            display_name = (
                name + "/" if type_role == "folder" and not name.endswith("/") else name
            )
            lines.append(display_name)
            recurse(item, "")

        return "\n".join(lines)


# ==========================================
# 文件生成线程
# ==========================================
class GeneratorThread(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(int, int)

    def __init__(self, base_path, structure):
        super().__init__()
        self.base_path = base_path
        self.structure = structure

    def run(self):
        success_count = 0
        total_count = len(self.structure)

        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path)
                self.progress_signal.emit(f"创建根目录: {self.base_path}")
            except Exception as e:
                self.progress_signal.emit(f"错误: 无法创建根目录 - {e}")
                self.finished_signal.emit(0, total_count)
                return

        for path, is_file in self.structure:
            try:
                full_target_path = os.path.join(self.base_path, path)

                if is_file:
                    dir_name = os.path.dirname(full_target_path)
                    if dir_name and not os.path.exists(dir_name):
                        os.makedirs(dir_name)

                    if not os.path.exists(full_target_path):
                        with open(full_target_path, "w", encoding="utf-8") as f:
                            pass
                        self.progress_signal.emit(f"[文件] {path}")
                    else:
                        self.progress_signal.emit(f"[跳过] 文件已存在: {path}")
                    success_count += 1
                else:
                    if not os.path.exists(full_target_path):
                        os.makedirs(full_target_path)
                        self.progress_signal.emit(f"[目录] {path}")
                    else:
                        self.progress_signal.emit(f"[跳过] 目录已存在: {path}")
                    success_count += 1
            except Exception as e:
                self.progress_signal.emit(f"[失败] {path} - {str(e)}")

        self.finished_signal.emit(success_count, total_count)


# ==========================================
# 可嵌入的主界面组件 Widget
# ==========================================
class ArchitectureGeneratorWidget(QWidget):
    generation_started = Signal()
    generation_finished = Signal(int, int)

    def __init__(self, parent=None, default_path=None):
        super().__init__(parent)
        self.custom_initial_path = default_path
        self.init_ui()
        # 不再加载默认架构文本；树保持为空，仅在导入确认后构建
        self.load_settings()
        self.status_label.setText("就绪：请先「从文本导入/编辑」架构后再生成")

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- 左侧：树形结构区域 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        toolbar_layout = QHBoxLayout()
        btn_load_text = QPushButton("从文本导入/编辑")
        btn_load_text.clicked.connect(self.import_from_text_dialog)

        btn_add_file = QPushButton("+ 添加文件")
        btn_add_file.clicked.connect(self.add_file_item)

        btn_add_folder = QPushButton("+ 添加文件夹")
        btn_add_folder.clicked.connect(self.add_folder_item)

        btn_del_item = QPushButton("删除选中")
        btn_del_item.clicked.connect(self.delete_tree_item)

        toolbar_layout.addWidget(btn_load_text)
        toolbar_layout.addWidget(btn_add_file)
        toolbar_layout.addWidget(btn_add_folder)
        toolbar_layout.addWidget(btn_del_item)
        toolbar_layout.addStretch()

        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabel("项目结构预览 (右键可新增/复制)")
        self.structure_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.structure_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.structure_tree.customContextMenuRequested.connect(self.show_context_menu)

        left_layout.addLayout(toolbar_layout)
        left_layout.addWidget(self.structure_tree)

        # --- 右侧：生成设置与日志 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        output_group = QGroupBox("生成设置")
        output_layout = QVBoxLayout()

        path_info_layout = QHBoxLayout()
        path_info_layout.addWidget(QLabel("目标位置:"))
        self.path_label = QLabel(self.custom_initial_path or os.getcwd())
        self.path_label.setWordWrap(True)
        path_info_layout.addWidget(self.path_label, stretch=1)

        path_btns_layout = QHBoxLayout()
        btn_browse = QPushButton("选择目录...")
        btn_browse.clicked.connect(self.browse_folder)

        self.btn_open_folder = QPushButton("打开当前文件夹")
        self.btn_open_folder.clicked.connect(self.open_target_folder)

        path_btns_layout.addWidget(btn_browse)
        path_btns_layout.addWidget(self.btn_open_folder)
        path_btns_layout.addStretch()

        self.btn_generate = QPushButton("一键生成所有文件")
        self.btn_generate.setFixedHeight(40)
        self.btn_generate.setStyleSheet(
            "font-weight: bold; font-size: 14px; background-color: #4CAF50; color: white;"
        )
        self.btn_generate.clicked.connect(self.start_generation)

        output_layout.addLayout(path_info_layout)
        output_layout.addLayout(path_btns_layout)
        output_layout.addWidget(self.btn_generate)
        output_group.setLayout(output_layout)

        log_group = QGroupBox("生成日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet("background-color: #f8f9fa;")
        log_layout.addWidget(self.log_text)

        log_btns_layout = QHBoxLayout()

        self.btn_export_paths = QPushButton("导出所有文件路径")
        self.btn_export_paths.setFixedHeight(30)
        self.btn_export_paths.clicked.connect(self.export_paths_dialog)

        self.btn_clear_log = QPushButton("清空日志")
        self.btn_clear_log.setFixedHeight(30)
        self.btn_clear_log.clicked.connect(self.clear_log)

        log_btns_layout.addWidget(self.btn_export_paths)
        log_btns_layout.addWidget(self.btn_clear_log)

        log_layout.addLayout(log_btns_layout)
        log_group.setLayout(log_layout)

        self.status_label = QLabel("就绪")

        right_layout.addWidget(output_group)
        right_layout.addWidget(log_group, stretch=1)
        right_layout.addWidget(self.status_label)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

    def import_from_text_dialog(self):
        """导入处理：仅在用户确定后解析并重建树；无默认内置架构文本"""
        if self.structure_tree.topLevelItemCount() > 0:
            initial_text = TreeStructureHelper.tree_to_text(self.structure_tree)
        else:
            initial_text = ""  # 空树时对话框也为空，由用户粘贴

        dialog = ImportTextDialog(self, initial_text)
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text()
            if not text or not text.strip():
                QMessageBox.warning(self, "提示", "导入文本为空，未执行任何改变。")
                return

            structure = TreeStructureHelper.parse_text_to_list(text)
            if not structure:
                QMessageBox.warning(
                    self, "解析失败", "未能从文本中识别出有效的文件/目录结构！"
                )
                return

            self.structure_tree.clear()
            TreeStructureHelper.build_tree_from_structure(structure, self.structure_tree)
            self.status_label.setText("已根据导入文本构建架构树")

    def export_paths_dialog(self):
        if self.structure_tree.topLevelItemCount() == 0:
            QMessageBox.warning(self, "提示", "架构树为空，没有可导出的路径。")
            return

        structure = TreeStructureHelper.get_structure_from_tree(self.structure_tree)

        lines = []
        for full_path, is_file in structure:
            clean_path = full_path.replace("\\", "/")
            if not is_file and not clean_path.endswith("/"):
                clean_path += "/"
            lines.append(clean_path)

        paths_text = "\n".join(lines)

        dialog = ExportPathsDialog(self, paths_text)
        dialog.exec_()

    def load_settings(self):
        settings = QSettings("BigShrimpApp", "ArchitectureGenerator")
        saved_path = settings.value("target_path", "")
        saved_log = settings.value("log_content", "")

        if not self.custom_initial_path:
            if saved_path and os.path.exists(saved_path):
                self.path_label.setText(saved_path)
            else:
                self.path_label.setText(os.getcwd())

        if saved_log:
            self.log_text.setPlainText(saved_log)

    def save_settings(self):
        settings = QSettings("BigShrimpApp", "ArchitectureGenerator")
        settings.setValue("target_path", self.path_label.text())
        settings.setValue("log_content", self.log_text.toPlainText())

    def clear_log(self):
        self.log_text.clear()
        self.save_settings()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择生成目录", self.path_label.text()
        )
        if folder:
            self.path_label.setText(folder)
            self.save_settings()

    def open_target_folder(self):
        folder_path = self.path_label.text().strip()
        if os.path.exists(folder_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        else:
            QMessageBox.warning(
                self,
                "提示",
                f"目标路径尚不存在：\n{folder_path}\n\n请先点击“一键生成所有文件”或选择有效路径。",
            )

    def add_file_item(self):
        self._create_node(is_file=True)

    def add_folder_item(self):
        self._create_node(is_file=False)

    def _create_node(self, is_file=True):
        item = self.structure_tree.currentItem()

        if not item:
            target_parent = self.structure_tree.invisibleRootItem()
            parent_text = "根目录"
            is_root = True
        elif item.data(0, Qt.UserRole) == "file":
            parent_item = item.parent()
            if parent_item is None:
                target_parent = self.structure_tree.invisibleRootItem()
                parent_text = "根目录"
                is_root = True
            else:
                target_parent = parent_item
                parent_text = parent_item.text(0)
                is_root = False
        else:
            target_parent = item
            parent_text = item.text(0)
            is_root = False

        node_type_str = "文件" if is_file else "文件夹"
        default_name = "new_file.py" if is_file else "new_folder"

        name, ok = QInputDialog.getText(
            self, f"新建{node_type_str}", f"在 '{parent_text}' 下创建:", text=default_name
        )
        if ok and name:
            new_item = QTreeWidgetItem(target_parent)
            new_item.setText(0, name)

            if is_file:
                new_item.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))
                new_item.setData(0, Qt.UserRole, "file")
            else:
                new_item.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))
                new_item.setData(0, Qt.UserRole, "folder")

            if not is_root:
                self.structure_tree.expandItem(target_parent)
            self.structure_tree.setCurrentItem(new_item)

    def copy_tree_item(self):
        item = self.structure_tree.currentItem()
        if not item:
            return

        parent = item.parent()
        target_parent = (
            parent if parent is not None else self.structure_tree.invisibleRootItem()
        )

        def clone_item(source_item, parent_node):
            new_node = QTreeWidgetItem(parent_node)
            new_node.setText(0, source_item.text(0))
            new_node.setIcon(0, source_item.icon(0))
            new_node.setData(0, Qt.UserRole, source_item.data(0, Qt.UserRole))

            for i in range(source_item.childCount()):
                clone_item(source_item.child(i), new_node)
            return new_node

        copied_item = clone_item(item, target_parent)

        old_name = item.text(0)
        is_file = item.data(0, Qt.UserRole) == "file"

        if is_file and "." in old_name:
            name, ext = os.path.splitext(old_name)
            copied_item.setText(0, f"{name}_copy{ext}")
        else:
            copied_item.setText(0, f"{old_name}_copy")

        self.structure_tree.setCurrentItem(copied_item)

    def delete_tree_item(self):
        item = self.structure_tree.currentItem()
        if item:
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除 '{item.text(0)}' 及其所有子项吗？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.structure_tree.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.structure_tree.takeTopLevelItem(index)

    def rename_tree_item(self):
        item = self.structure_tree.currentItem()
        if item:
            old_name = item.text(0)
            new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
            if ok and new_name:
                item.setText(0, new_name)

    def show_context_menu(self, position):
        item = self.structure_tree.itemAt(position)
        menu = QMenu()

        act_add_file = QAction("添加文件", self)
        act_add_file.triggered.connect(self.add_file_item)
        menu.addAction(act_add_file)

        act_add_folder = QAction("添加文件夹", self)
        act_add_folder.triggered.connect(self.add_folder_item)
        menu.addAction(act_add_folder)

        if item:
            menu.addSeparator()

            act_copy = QAction("复制文件/节点", self)
            act_copy.triggered.connect(self.copy_tree_item)
            menu.addAction(act_copy)

            act_rename = QAction("重命名", self)
            act_rename.triggered.connect(self.rename_tree_item)
            menu.addAction(act_rename)

            act_del = QAction("删除", self)
            act_del.triggered.connect(self.delete_tree_item)
            menu.addAction(act_del)

        menu.exec_(self.structure_tree.viewport().mapToGlobal(position))

    def start_generation(self):
        base_path = self.path_label.text()
        if not os.path.isdir(base_path):
            QMessageBox.warning(self, "错误", "请选择有效的目标目录！")
            return

        if self.structure_tree.topLevelItemCount() == 0:
            QMessageBox.warning(
                self, "错误", "架构树为空，请先通过「从文本导入/编辑」导入结构后再生成。"
            )
            return

        structure = TreeStructureHelper.get_structure_from_tree(self.structure_tree)

        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要在 {base_path} 下生成所有文件和文件夹吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.log_text.clear()
            self.btn_generate.setEnabled(False)
            self.status_label.setText("正在生成...")
            self.generation_started.emit()

            self.worker = GeneratorThread(base_path, structure)
            self.worker.progress_signal.connect(self.append_log)
            self.worker.finished_signal.connect(self.on_finished)
            self.worker.start()

    def append_log(self, message):
        self.log_text.append(message)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_finished(self, success, total):
        self.btn_generate.setEnabled(True)
        self.status_label.setText(f"完成: {success}/{total} 个对象创建成功")
        self.append_log("----------------------------")
        self.append_log(f"任务结束。成功: {success}, 总计: {total}")
        self.save_settings()
        self.generation_finished.emit(success, total)
        QMessageBox.information(
            self, "完成", f"架构生成完毕！\n成功: {success}\n总计: {total}"
        )


# ==========================================
# 独立运行的主窗口
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BigShrimp 架构生成器")
        self.resize(1100, 700)

        self.center_on_screen()

        self.generator_widget = ArchitectureGeneratorWidget(self)
        self.setCentralWidget(self.generator_widget)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def closeEvent(self, event):
        self.generator_widget.save_settings()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())