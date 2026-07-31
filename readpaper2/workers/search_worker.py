# workers/search_worker.py
"""
异步查询 Task：避免大表检索时阻塞 Qt 主 UI 事件循环。
"""
import logging
from PySide2.QtCore import QThread, Signal
from typing import Optional
from services.search import SearchService

logger = logging.getLogger(__name__)

class SearchThread(QThread):
    results_signal = Signal(list)

    def __init__(self, search_service: SearchService, query: str, parent=None):
        super().__init__(parent)
        self.search_service = search_service
        self.query = query

    def run(self):
        try:
            results = self.search_service.query_articles(keyword=self.query, use_fts=True)
            self.results_signal.emit(results)
        except Exception as e:
            logger.error(f"FTS5 搜索线程执行报错: {str(e)}")
            self.results_signal.emit([])

class QueryThread(QThread):
    results_signal = Signal(list)

    def __init__(self, search_service: SearchService, keyword: str = "",
                 start_date: str = "", end_date: str = "",
                 fav_only: bool = False, tag_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.search_service = search_service
        self.keyword = keyword
        self.start_date = start_date
        self.end_date = end_date
        self.fav_only = fav_only
        self.tag_id = tag_id

    def run(self):
        try:
            results = self.search_service.query_articles(
                keyword=self.keyword,
                start_date=self.start_date,
                end_date=self.end_date,
                fav_only=self.fav_only,
                tag_id=self.tag_id,
                use_fts=False
            )
            self.results_signal.emit(results)
        except Exception as e:
            logger.error(f"常规查询线程执行报错: {str(e)}")
            self.results_signal.emit([])