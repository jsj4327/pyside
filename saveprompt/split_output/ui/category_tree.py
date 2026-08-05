"""
分类导航树组件
封装右键菜单、增删改操作信号及选中状态管理。
"""
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMenu, QAction, QMessageBox,
    QInputDialog
)
from PySide2.QtCore import Qt, Signal

from config import ALL_CATEGORY_KEY, UNCATEGORIZED
from services._filter_service import count_by_category


class CategoryTree(QWidget):
    """分类导航树组件，提供分类浏览与右键管理功能。"""

    category_selected = Signal(str)
    categories_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = []
        self.prompts = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>分类导航</b>"))
        self.btn_add = QPushButton("+ 新增分类")
        self.btn_add.setFixedHeight(24)
        self.btn_add.clicked.connect(self.add_category_dialog)
        header.addWidget(self.btn_add)
        layout.addLayout(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree)

    def refresh(self, categories: list, prompts: list):
        """刷新分类树数据并保持当前选中项。"""
        self.categories = categories
        self.prompts = prompts

        current = self.tree.currentItem()
        selected = current.data(0, Qt.UserRole) if current else ALL_CATEGORY_KEY

        self.tree.clear()

        total = len(prompts)
        all_item = QTreeWidgetItem([f"全部分类 ({total})"])
        all_item.setData(0, Qt.UserRole, ALL_CATEGORY_KEY)
        self.tree.addTopLevelItem(all_item)

        for cat in categories:
            cnt = count_by_category(prompts, cat)
            item = QTreeWidgetItem([f"{cat} ({cnt})"])
            item.setData(0, Qt.UserRole, cat)
            self.tree.addTopLevelItem(item)

        self.tree.expandAll()

        # 恢复之前选中
        target = all_item
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.data(0, Qt.UserRole) == selected:
                target = it
                break
        self.tree.setCurrentItem(target)

    def get_selected_category(self) -> str:
        """获取当前选中的分类标识。"""
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) if item else ALL_CATEGORY_KEY

    def on_item_clicked(self, item, column):
        self.category_selected.emit(item.data(0, Qt.UserRole))

    # ---- 右键菜单 ----
    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self)

        act_add = QAction("新增分类", self)
        act_add.triggered.connect(self.add_category_dialog)
        menu.addAction(act_add)

        if item:
            name = item.data(0, Qt.UserRole)
            if name and name != ALL_CATEGORY_KEY:
                menu.addSeparator()
                act_rename = QAction(f"重命名 '{name}'", self)
                act_rename.triggered.connect(lambda: self.rename_category_dialog(name))
                menu.addAction(act_rename)

                act_del = QAction(f"删除分类 '{name}'", self)
                act_del.triggered.connect(lambda: self.delete_category_dialog(name))
                menu.addAction(act_del)

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    # ---- 分类 CRUD 对话框 ----
    def add_category_dialog(self):
        name, ok = QInputDialog.getText(self, "新增分类", "请输入新分类名称:")
        if ok and name.strip():
            cat = name.strip()
            if cat in self.categories:
                QMessageBox.warning(self, "提示", f"分类 [{cat}] 已存在！")
                return
            self.categories.append(cat)
            self.categories_changed.emit()

    def rename_category_dialog(self, old_name: str):
        if not old_name or old_name == ALL_CATEGORY_KEY:
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名分类", f"请输入 [{old_name}] 的新名称:", text=old_name
        )
        if ok and new_name.strip():
            new_name = new_name.strip()
            if new_name == old_name:
                return
            if new_name in self.categories:
                QMessageBox.warning(self, "提示", f"分类名称 [{new_name}] 已存在！")
                return
            idx = self.categories.index(old_name)
            self.categories[idx] = new_name
            for p in self.prompts:
                if p.get("category") == old_name:
                    p["category"] = new_name
            self.categories_changed.emit()

    def delete_category_dialog(self, cat_name: str):
        if not cat_name or cat_name == ALL_CATEGORY_KEY:
            return
        cnt = count_by_category(self.prompts, cat_name)
        msg = f"确定要删除分类 [{cat_name}] 吗？"
        if cnt > 0:
            msg += f"\n\n注意：该分类下存在 {cnt} 条 Prompt，删除后它们将被重定向为 '{UNCATEGORIZED}'。"
        reply = QMessageBox.question(
            self, "确认删除分类", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if cat_name in self.categories:
                self.categories.remove(cat_name)
            if cnt > 0:
                if UNCATEGORIZED not in self.categories:
                    self.categories.append(UNCATEGORIZED)
                for p in self.prompts:
                    if p.get("category") == cat_name:
                        p["category"] = UNCATEGORIZED
            self.categories_changed.emit()
