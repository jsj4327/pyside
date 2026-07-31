# -*- coding:utf-8 -*-
"""
main.py — 主入口
集成：爬虫模块 + 知识库模块
"""
import sys
import os

from PySide2.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QLabel, QVBoxLayout, QWidget
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont

# 明确导入本地模块
from crawler_tab import CrawlerTab
from knowledge_base import KnowledgeTab

APP_NAME = "AI_Assistant_Pro"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant Pro - 人民日报")
        self.save_dir = os.path.join(os.path.expanduser("~"), "CrawledArticles")
        self.db_path = os.path.join(self.save_dir, "articles.db")
        os.makedirs(self.save_dir, exist_ok=True)
        self._init_ui()
        self._resize(0.85)

    def _resize(self, ratio):
        """根据屏幕比例调整窗口大小"""
        scr = QApplication.primaryScreen()
        if not scr:
            self.resize(1280, 800)
            return
        g = scr.availableGeometry()
        w, h = int(g.width() * ratio), int(g.height() * ratio)
        self.setGeometry(
            g.x() + (g.width() - w) // 2,
            g.y() + (g.height() - h) // 2,
            w, h
        )

    def _init_ui(self):
        self.tabs = QTabWidget()

        # ====== Tab 1: 爬虫 ======
        self.crawler = CrawlerTab()
        self.crawler.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 5000)
        )
        self.tabs.addTab(self.crawler, "🕷️ 文章爬取")

        # ====== Tab 2: 知识库 ======
        self.knowledge = KnowledgeTab(self.db_path)
        self.knowledge.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 5000)
        )
        self.tabs.addTab(self.knowledge, "📚 知识库")

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("就绪")
        self.statusBar().setStyleSheet(
            "QStatusBar { font-size:12px; color:#555; padding:2px 8px; }"
        )

        # 切换到知识库 Tab 时自动刷新
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if widget is self.knowledge:
            self.knowledge.refresh()

    def closeEvent(self, event):
        # 退出时清理爬虫线程
        if hasattr(self.crawler, 'cleanup'):
            self.crawler.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())