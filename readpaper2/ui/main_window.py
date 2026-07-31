# ui/main_window.py
"""
应用主窗口：包含 Tab 视图容器、状态栏与菜单栏绑定。
"""
from PySide2.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QAction, QMessageBox, QFileDialog
from db.repositories import ArticleRepository
from ui.crawler_tab import CrawlerTab
from ui.knowledge_tab import KnowledgeTab
from config import APP_NAME, VERSION

class MainWindow(QMainWindow):
    def __init__(self, repository: ArticleRepository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1200, 800)
        self._init_ui()

    def _init_ui(self):
        self._create_menus()

        self.tabs = QTabWidget()

        self.knowledge_tab = KnowledgeTab(self.repo)
        self.crawler_tab = CrawlerTab(self.repo)

        self.crawler_tab.crawl_finished_signal.connect(self._on_crawl_finished)

        self.tabs.addTab(self.knowledge_tab, "📚 新闻知识库")
        self.tabs.addTab(self.crawler_tab, "🕷️ 爬虫控制台")

        self.setCentralWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar()

    def _create_menus(self):
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("文件 (&F)")
        backup_act = QAction("备份数据库...", self)
        backup_act.triggered.connect(self._backup_db)
        exit_act = QAction("退出系统", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(backup_act)
        file_menu.addSeparator()
        file_menu.addAction(exit_act)

        help_menu = menu_bar.addMenu("帮助 (&H)")
        about_act = QAction("关于 ReadPaper", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _backup_db(self):
        path, _ = QFileDialog.getSaveFileName(self, "备份数据库", "readpaper_backup.db", "SQLite DB (*.db)")
        if path:
            self.repo.db_conn.execute_backup(path)
            QMessageBox.information(self, "成功", f"数据库已成功热备份至:\n{path}")

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于 ReadPaper",
            f"<h3>{APP_NAME}</h3>"
            f"<p>版本: v{VERSION}</p>"
            "<p>一个基于 PySide2 与 SQLite FTS5 全文索引构建的高性能离线新闻数据采集与检索知识库。</p>"
        )

    def _on_crawl_finished(self):
        self.knowledge_tab._execute_search()
        self.knowledge_tab._reload_tags()
        self._update_status_bar()

    def _update_status_bar(self):
        stats = self.repo.get_stats()
        msg = f"📊 数据库概览：总文章数: {stats['total_articles']} 篇 | 收藏文章: {stats['total_favs']} 篇 | 标签数: {stats['total_tags']} 个 | 总字数: {stats['total_words']} 字"
        self.status_bar.showMessage(msg)