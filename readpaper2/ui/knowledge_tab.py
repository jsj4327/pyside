# ui/knowledge_tab.py
"""
知识库视图：包含多条件过滤、FTS5 全文搜索、表格右键上下文菜单与多格式导出。
"""
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                             QLineEdit, QPushButton, QCheckBox, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QMenu)
from PySide2.QtCore import Qt
from db.repositories import ArticleRepository
from services.search import SearchService
from services.exporter import export_json, export_txt, export_csv, export_markdown
from workers.search_worker import QueryThread
from ui.detail_widget import ArticleDetailWidget

class KnowledgeTab(QWidget):
    def __init__(self, repository: ArticleRepository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.search_service = SearchService(self.repo)
        self.current_articles = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎 输入关键字搜索 (支持 FTS5 引擎)...")
        self.search_input.returnPressed.connect(self._execute_search)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self._execute_search)

        self.fav_checkbox = QCheckBox("仅看收藏")
        self.fav_checkbox.stateChanged.connect(self._execute_search)

        self.tag_combo = QComboBox()
        self.tag_combo.addItem("所有标签", None)
        self._reload_tags()
        self.tag_combo.currentIndexChanged.connect(self._execute_search)

        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.search_btn)
        filter_layout.addWidget(self.fav_checkbox)
        filter_layout.addWidget(self.tag_combo)

        export_layout = QHBoxLayout()
        self.export_json_btn = QPushButton("导出 JSON")
        self.export_json_btn.clicked.connect(self._export_json)
        self.export_txt_btn = QPushButton("导出 TXT")
        self.export_txt_btn.clicked.connect(self._export_txt)
        self.export_csv_btn = QPushButton("导出 CSV")
        self.export_csv_btn.clicked.connect(self._export_csv)
        self.export_md_btn = QPushButton("导出 Markdown")
        self.export_md_btn.clicked.connect(self._export_markdown)

        export_layout.addWidget(self.export_json_btn)
        export_layout.addWidget(self.export_txt_btn)
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_md_btn)
        export_layout.addStretch()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "日期", "标题", "作者", "字数"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_select_article)

        left_layout.addLayout(filter_layout)
        left_layout.addLayout(export_layout)
        left_layout.addWidget(self.table)

        self.detail_widget = ArticleDetailWidget(self.repo)
        self.detail_widget.article_updated.connect(self._execute_search)

        splitter.addWidget(left_widget)
        splitter.addWidget(self.detail_widget)
        splitter.setSizes([550, 450])

        main_layout.addWidget(splitter)

        self._execute_search()

    def _reload_tags(self):
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("所有标签", None)
        tags = self.repo.get_all_tags()
        for t in tags:
            self.tag_combo.addItem(t["name"], t["id"])
        self.tag_combo.blockSignals(False)

    def _execute_search(self):
        keyword = self.search_input.text().strip()
        fav_only = self.fav_checkbox.isChecked()
        tag_id = self.tag_combo.currentData()

        self.query_thread = QueryThread(
            search_service=self.search_service,
            keyword=keyword,
            fav_only=fav_only,
            tag_id=tag_id
        )
        self.query_thread.results_signal.connect(self._update_table_data)
        self.query_thread.start()

    def _update_table_data(self, articles: list):
        self.current_articles = articles
        self.table.setRowCount(0)
        for row, art in enumerate(articles):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(art["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(art.get("date", "")))
            self.table.setItem(row, 2, QTableWidgetItem(art.get("title", "")))
            self.table.setItem(row, 3, QTableWidgetItem(art.get("author", "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(art.get("word_count", 0))))

    def _on_select_article(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.current_articles):
            article = self.current_articles[row]
            self.detail_widget.set_article(article)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        article = self.current_articles[row]

        menu = QMenu(self)
        fav_act = menu.addAction("★ 切换收藏")
        del_act = menu.addAction("🗑️ 删除文章")
        
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == fav_act:
            self.repo.toggle_favorite(article["id"])
            self._execute_search()
        elif action == del_act:
            reply = QMessageBox.question(self, "确认删除", "确定要永久删除这篇文章吗？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.repo.delete_article(article["id"])
                self._execute_search()

    def _export_json(self):
        if not self.current_articles:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "articles.json", "JSON Files (*.json)")
        if path:
            export_json(self.current_articles, path)
            QMessageBox.information(self, "成功", "已成功导出 JSON 数据！")

    def _export_txt(self):
        if not self.current_articles:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 TXT", "articles.txt", "Text Files (*.txt)")
        if path:
            export_txt(self.current_articles, path)
            QMessageBox.information(self, "成功", "已成功导出 TXT 数据！")

    def _export_csv(self):
        if not self.current_articles:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "articles.csv", "CSV Files (*.csv)")
        if path:
            export_csv(self.current_articles, path)
            QMessageBox.information(self, "成功", "已成功导出 CSV 数据！")

    def _export_markdown(self):
        if not self.current_articles:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 Markdown", "articles.md", "Markdown Files (*.md)")
        if path:
            export_markdown(self.current_articles, path)
            QMessageBox.information(self, "成功", "已成功导出 Markdown 数据！")