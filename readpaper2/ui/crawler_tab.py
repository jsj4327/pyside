# ui/crawler_tab.py
"""
爬虫控制台界面：提供任务设置、状态监控与实时日志过滤展示。
"""
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QDateEdit, QPushButton, QProgressBar, QTextEdit)
from PySide2.QtCore import QDate, Signal
from db.repositories import ArticleRepository
from workers.crawl_worker import CrawlerThread
from config import MAX_LOG_LINES

class CrawlerTab(QWidget):
    crawl_finished_signal = Signal()

    def __init__(self, repository: ArticleRepository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.crawler_thread = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        config_box = QGroupBox("爬取参数与策略配置")
        config_layout = QHBoxLayout(config_box)

        config_layout.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QDateEdit(QDate.currentDate().addDays(-3))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        config_layout.addWidget(self.start_date_edit)

        config_layout.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        config_layout.addWidget(self.end_date_edit)

        self.start_btn = QPushButton("▶ 开始爬取")
        self.start_btn.clicked.connect(self._start_crawl)
        config_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_crawl)
        config_layout.addWidget(self.stop_btn)

        layout.addWidget(config_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        log_box = QGroupBox("爬虫后台实时执行日志")
        log_layout = QVBoxLayout(log_box)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_box)

    def _start_crawl(self):
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_text.clear()

        self.crawler_thread = CrawlerThread(start_date, end_date, self.repo)
        self.crawler_thread.log_signal.connect(self._append_log)
        self.crawler_thread.progress_signal.connect(self._update_progress)
        self.crawler_thread.finished_signal.connect(self._on_finished)
        self.crawler_thread.start()

    def _stop_crawl(self):
        if self.crawler_thread and self.crawler_thread.isRunning():
            self.crawler_thread.stop()
            self._append_log("⚠️ 收到取消信号，正在等待当前请求结束...")

    def _append_log(self, text: str):
        self.log_text.append(text)
        lines = self.log_text.toPlainText().split("\n")
        if len(lines) > MAX_LOG_LINES:
            self.log_text.setPlainText("\n".join(lines[-MAX_LOG_LINES:]))

    def _update_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_finished(self, count: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._append_log(f"🏁 Task 运行就绪，累积处理写入数据 {count} 篇")
        self.crawl_finished_signal.emit()