# workers/crawl_worker.py
"""
后台爬取 Task (QThread)：解耦 UI 渲染与耗时网络 IO，支持暂停/继续/取消。
"""
import time
import logging
from PySide2.QtCore import QThread, Signal
from db.repositories import ArticleRepository
from services.scraper import fetch_page, generate_layout_urls
from services.parser import parse_layout_page, parse_article_page

logger = logging.getLogger(__name__)

class CrawlerThread(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(int)

    def __init__(self, start_date: str, end_date: str, repository: ArticleRepository, parent=None):
        super().__init__(parent)
        self.start_date = start_date
        self.end_date = end_date
        self.repo = repository
        self._is_running = True
        self._is_paused = False

    def stop(self):
        self._is_running = False

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def run(self):
        self.log_signal.emit(f"🚀 开始生成爬取任务清单: {self.start_date} 至 {self.end_date}")
        layout_urls = generate_layout_urls(self.start_date, self.end_date)
        total_layouts = len(layout_urls)
        
        self.log_signal.emit(f"🔎 评估发现待探测版面页面共计 {total_layouts} 个")
        
        crawled_count = 0
        all_articles = []

        for idx, l_url in enumerate(layout_urls):
            while self._is_paused and self._is_running:
                time.sleep(0.5)

            if not self._is_running:
                self.log_signal.emit("⏹️ 爬取任务已被用户手动取消")
                break

            self.progress_signal.emit(idx + 1, total_layouts)
            html = fetch_page(l_url)
            if not html:
                continue

            articles = parse_layout_page(html, l_url)
            for art in articles:
                if not self._is_running:
                    break

                while self._is_paused and self._is_running:
                    time.sleep(0.5)

                art_html = fetch_page(art["url"])
                if art_html:
                    detail = parse_article_page(art_html)
                    art.update(detail)
                
                all_articles.append(art)
                self.log_signal.emit(f"✅ 抓取成功: [{art.get('date')}] {art.get('title')}")

            # 每攒满 20 篇批量落盘一次
            if len(all_articles) >= 20:
                inserted = self.repo.insert_articles_batch(all_articles)
                crawled_count += inserted
                all_articles.clear()

        # 处理剩余记录
        if all_articles and self._is_running:
            inserted = self.repo.insert_articles_batch(all_articles)
            crawled_count += inserted
            all_articles.clear()

        self.log_signal.emit(f"🎉 爬取任务已完成！本次成功新增入库文章共 {crawled_count} 篇")
        self.finished_signal.emit(crawled_count)