"""ui/knowledge_tab.py — 知识库模块 View 界面"""

import math
import os
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor
from PySide2.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import PAGE_SIZE
from database import DatabaseManager
from threads import QueryThread, SearchThread
from ui.article_detail import ArticleDetailWidget


class KnowledgeTab(QWidget):
    status_message = Signal(str)

    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_page = 1
        self.search_mode = False
        self._search_thread = None
        self._query_thread = None
        self._init_ui()
        self._load_filters()

    def _init_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        search_box = QGroupBox("🔍 搜索与筛选")
        sg = QGridLayout(search_box)
        self.edit_search = QLineEdit()
        self.edit_search.returnPressed.connect(self._do_search)
        sg.addWidget(QLabel("关键词:"), 0, 0)
        sg.addWidget(self.edit_search, 0, 1)

        btn_search = QPushButton("搜索")
        btn_search.clicked.connect(self._do_search)
        sg.addWidget(btn_search, 0, 2)

        self.cmb_section = QComboBox()
        sg.addWidget(QLabel("版面:"), 1, 0)
        sg.addWidget(self.cmb_section, 1, 1)

        self.chk_fav_only = QCheckBox("仅收藏")
        self.chk_fav_only.stateChanged.connect(lambda: self._goto_page(1))
        sg.addWidget(self.chk_fav_only, 2, 0, 1, 2)

        left_layout.addWidget(search_box)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "标题", "版面", "作者", "日期", "★"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self._on_row_click)
        left_layout.addWidget(self.table, 1)

        page_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_prev.clicked.connect(
            lambda: self._goto_page(self.current_page - 1)
        )
        self.btn_next = QPushButton("下一页 ▶")
        self.btn_next.clicked.connect(
            lambda: self._goto_page(self.current_page + 1)
        )
        page_layout.addWidget(self.btn_prev)
        page_layout.addWidget(self.btn_next)
        left_layout.addLayout(page_layout)

        right_tabs = QTabWidget()
        self.detail = ArticleDetailWidget(self.db_path)
        right_tabs.addTab(self.detail, "📄 文章详情")

        splitter.addWidget(left)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

    def _load_filters(self):
        if os.path.exists(self.db_path):
            db = DatabaseManager(self.db_path)
            sections = db.get_sections()
            db.close()
            self.cmb_section.clear()
            self.cmb_section.addItem("全部版面", "")
            for s in sections:
                self.cmb_section.addItem(s, s)

    def _goto_page(self, page):
        if page < 1:
            return
        self.current_page = page
        if self.search_mode and self.edit_search.text().strip():
            self._do_search(page)
        else:
            self._do_query(page)

    def _do_query(self, page=1):
        self.search_mode = False
        self._query_thread = QueryThread(
            self.db_path,
            page,
            PAGE_SIZE,
            self.cmb_section.currentData(),
            "",
            "",
            "id DESC",
            self.chk_fav_only.isChecked(),
        )
        self._query_thread.result_signal.connect(self._render_table)
        self._query_thread.start()

    def _do_search(self, page=1):
        kw = self.edit_search.text().strip()
        if not kw:
            self._do_query(1)
            return
        self.search_mode = True
        self._search_thread = SearchThread(self.db_path, kw, page, PAGE_SIZE)
        self._search_thread.result_signal.connect(
            lambda t, r, f: self._render_table(t, r)
        )
        self._search_thread.start()

    def _render_table(self, total, rows):
        self.table.setRowCount(len(rows))
        for i, art in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(art["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(art["title"]))
            self.table.setItem(i, 2, QTableWidgetItem(art.get("section", "")))
            self.table.setItem(i, 3, QTableWidgetItem(art.get("author", "")))
            self.table.setItem(i, 4, QTableWidgetItem(art.get("pub_date", "")))

            fav_item = QTableWidgetItem("★" if art.get("is_fav") else "")
            if art.get("is_fav"):
                fav_item.setForeground(QColor("#FFB300"))
            self.table.setItem(i, 5, fav_item)
            self.table.item(i, 0).setData(Qt.UserRole, art["id"])

    def _on_row_click(self, row, col):
        item = self.table.item(row, 0)
        if item:
            self.detail.load_article(item.data(Qt.UserRole))

    def refresh(self):
        self._load_filters()
        self._goto_page(1)