# -*- coding: utf-8 -*-
"""main.py — 程序组装主入口"""

import os
import sys
from PySide2.QtGui import QFont
from PySide2.QtWidgets import QApplication, QMainWindow, QTabWidget

from config import DEFAULT_SAVE_DIR
from ui.crawler_tab import CrawlerTab
from ui.knowledge_tab import KnowledgeTab


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant Pro - 人民日报")
        self.save_dir = DEFAULT_SAVE_DIR
        self.db_path = os.path.join(self.save_dir, "articles.db")
        os.makedirs(self.save_dir, exist_ok=True)
        self._init_ui()

    def _init_ui(self):
        self.tabs = QTabWidget()

        self.crawler = CrawlerTab()
        self.crawler.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 5000)
        )
        self.tabs.addTab(self.crawler, "🕷️ 文章爬取")

        self.knowledge = KnowledgeTab(self.db_path)
        self.knowledge.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 5000)
        )
        self.tabs.addTab(self.knowledge, "📚 知识库")

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("就绪")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.resize(1280, 800)

    def _on_tab_changed(self, index):
        if self.tabs.widget(index) is self.knowledge:
            self.knowledge.refresh()

    def closeEvent(self, event):
        if hasattr(self.crawler, "cleanup"):
            self.crawler.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())