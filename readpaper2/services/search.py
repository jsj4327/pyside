# services/search.py
"""
搜索业务服务：屏蔽底层 SQL 与 FTS 差异，提供多维查询抽象接口。
"""
from typing import List, Dict, Any, Optional
from db.repositories import ArticleRepository

class SearchService:
    def __init__(self, repository: ArticleRepository):
        self.repo = repository

    def query_articles(self, keyword: str = "", start_date: str = "", end_date: str = "",
                       fav_only: bool = False, tag_id: Optional[int] = None,
                       use_fts: bool = False, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        # 当纯关键字搜索时优先启用 FTS5 引擎，组合搜索使用标准条件查询
        if use_fts and keyword and not start_date and not end_date and not fav_only and tag_id is None:
            return self.repo.search_fts_highlight(query_str=keyword, limit=limit, offset=offset)
        else:
            return self.repo.search_sql(
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                fav_only=fav_only,
                tag_id=tag_id,
                limit=limit,
                offset=offset
            )