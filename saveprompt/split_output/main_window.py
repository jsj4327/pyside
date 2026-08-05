"""
主窗口模块
组合各UI子组件，协调Repository与FilterService完成业务流转。
"""
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QSplitter, QStackedWidget, QMessageBox, QDialog,
    QApplication
)
from PySide2.QtCore import Qt

from config import STYLE_BTN_SUCCESS
from repository import DataLoaderThread, save_data
from services._filter_service import filter_prompts
from ui.loading_screen import LoadingScreen
from ui.category_tree import CategoryTree
from ui.prompt_table import PromptTable
from ui.edit_dialog import PromptEditDialog
from models import validate_prompt


class PromptManagerApp(QMainWindow):
    """Prompt 提示词分类与搜索管理主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prompt 提示词分类与搜索管理")

        self.categories = []
        self.prompts = []

        self._init_ui()
        self.center_on_screen()
        self.load_data_async()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        w = int(geo.width() * 0.85)
        h = int(geo.height() * 0.85)
        x = geo.x() + (geo.width() - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        self.setGeometry(x, y, w, h)

    # ========== UI 初始化 ==========
    def _init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 页面0: 加载屏
        self.loading_screen = LoadingScreen()
        self.stack.addWidget(self.loading_screen)

        # 页面1: 主界面
        main = QWidget()
        main_layout = QHBoxLayout(main)
        splitter = QSplitter(Qt.Horizontal)

        # 左侧分类树
        self.cat_tree = CategoryTree()
        self.cat_tree.category_selected.connect(self.on_filter_changed)
        self.cat_tree.categories_changed.connect(self.on_categories_modified)
        splitter.addWidget(self.cat_tree)

        # 右侧搜索+表格
        right = QWidget()
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        top.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("实时搜索标题、标签、Prompt 或备注...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        top.addWidget(self.search_input)

        btn_add = QPushButton("+ 新增 Prompt")
        btn_add.setStyleSheet(STYLE_BTN_SUCCESS)
        btn_add.clicked.connect(self.add_prompt)
        top.addWidget(btn_add)
        r_layout.addLayout(top)

        self.prompt_table = PromptTable()
        self.prompt_table.copy_requested.connect(self.copy_to_clipboard)
        self.prompt_table.edit_requested.connect(self.edit_prompt)
        self.prompt_table.delete_requested.connect(self.delete_prompt)
        r_layout.addWidget(self.prompt_table)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

        self.stack.addWidget(main)

    # ========== 数据加载 ==========
    def load_data_async(self):
        self.stack.setCurrentIndex(0)
        self.loader = DataLoaderThread()
        self.loader.loaded_signal.connect(self.on_data_loaded)
        self.loader.error_signal.connect(self.on_load_error)
        self.loader.start()

    def on_data_loaded(self, data):
        self.categories = data.get("categories", [])
        self.prompts = data.get("prompts", [])
        self.stack.setCurrentIndex(1)
        self.refresh_all()

    def on_load_error(self, msg):
        self.stack.setCurrentIndex(1)
        QMessageBox.critical(self, "数据加载错误", f"读取数据文件失败: {msg}")

    def save(self):
        try:
            save_data(self.categories, self.prompts)
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存数据失败: {e}")

    # ========== 刷新与过滤 ==========
    def refresh_all(self):
        self.cat_tree.refresh(self.categories, self.prompts)
        self.on_filter_changed()

    def on_filter_changed(self, _=None):
        cat = self.cat_tree.get_selected_category()
        kw = self.search_input.text()
        filtered = filter_prompts(self.prompts, cat, kw)
        self.prompt_table.render(filtered)

    def on_categories_modified(self):
        self.save()
        self.refresh_all()

    # ========== Prompt CRUD ==========
    def add_prompt(self):
        dlg = PromptEditDialog(self, categories=self.categories)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not validate_prompt(data):
                QMessageBox.warning(self, "错误", "标题和 Prompt 内容不能为空！")
                return
            if data["category"] not in self.categories:
                self.categories.append(data["category"])
            self.prompts.insert(0, data)
            self.save()
            self.refresh_all()

    def edit_prompt(self, prompt_data):
        dlg = PromptEditDialog(self, categories=self.categories, prompt_data=prompt_data)
        if dlg.exec_() == QDialog.Accepted:
            updated = dlg.get_data()
            if not validate_prompt(updated):
                QMessageBox.warning(self, "错误", "标题和 Prompt 内容不能为空！")
                return
            if updated["category"] not in self.categories:
                self.categories.append(updated["category"])
            for i, p in enumerate(self.prompts):
                if p["id"] == updated["id"]:
                    self.prompts[i] = updated
                    break
            self.save()
            self.refresh_all()

    def delete_prompt(self, prompt_data):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 Prompt '{prompt_data.get('title')}' 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            tid = prompt_data["id"]
            self.prompts = [p for p in self.prompts if p["id"] != tid]
            self.save()
            self.refresh_all()

    def copy_to_clipboard(self, prompt_data):
        clipboard = QApplication.clipboard()
        clipboard.setText(prompt_data.get("prompt", ""))
        QMessageBox.information(self, "成功", "Prompt 内容已复制到剪贴板！")
