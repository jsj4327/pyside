"""threads.py — 后台异步任务线程模块（包含数据库查询、搜索与爬虫线程）"""

import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from PySide2.QtCore import QThread, Signal

from database import DatabaseManager


class QueryThread(QThread):
    """数据库分页与条件查询线程"""
    result_signal = Signal(int, list)  # (total_count, article_list)

    def __init__(
        self,
        db_path,
        page=1,
        page_size=20,
        section="",
        author="",
        keyword="",
        order_by="id DESC",
        fav_only=False,
        parent=None,
    ):
        super().__init__(parent)
        self.db_path = db_path
        self.page = page
        self.page_size = page_size
        self.section = section
        self.author = author
        self.keyword = keyword
        self.order_by = order_by
        self.fav_only = fav_only

    def run(self):
        if not os.path.exists(self.db_path):
            self.result_signal.emit(0, [])
            return

        try:
            db = DatabaseManager(self.db_path)
            total, rows = db.get_articles(
                page=self.page,
                page_size=self.page_size,
                section=self.section,
                author=self.author,
                keyword=self.keyword,
                order_by=self.order_by,
                fav_only=self.fav_only,
            )
            db.close()
            self.result_signal.emit(total, rows)
        except Exception:
            self.result_signal.emit(0, [])


class SearchThread(QThread):
    """数据库全文/关键词搜索线程"""
    result_signal = Signal(int, list, str)  # (total_count, article_list, keyword)

    def __init__(self, db_path, keyword, page=1, page_size=20, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.keyword = keyword
        self.page = page
        self.page_size = page_size

    def run(self):
        if not os.path.exists(self.db_path):
            self.result_signal.emit(0, [], self.keyword)
            return

        try:
            db = DatabaseManager(self.db_path)
            total, rows = db.search_articles(
                self.keyword, page=self.page, page_size=self.page_size
            )
            db.close()
            self.result_signal.emit(total, rows, self.keyword)
        except Exception:
            self.result_signal.emit(0, [], self.keyword)


class CrawlerThread(QThread):
    """双占位符范围爬虫后台线程"""
    progress_signal = Signal(int, int, str)  # (current, total, message)
    batch_saved_signal = Signal(int, int)    # (inserted, skipped)
    finished_signal = Signal(dict)          # result summary dict

    def __init__(
        self,
        url_template,
        p1_cfg,
        p2_cfg,
        db_path,
        fetch_content=True,
        batch_size=50,
        parent=None,
    ):
        super().__init__(parent)
        self.url_template = url_template
        self.p1_cfg = p1_cfg
        self.p2_cfg = p2_cfg
        self.db_path = db_path
        self.fetch_content = fetch_content
        self.batch_size = batch_size
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        urls = self._generate_urls()
        total_urls = len(urls)

        if total_urls == 0:
            self.finished_signal.emit({"status": "empty", "message": "未生成有效 URL"})
            return

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        articles_batch = []
        total_fetched = 0
        total_inserted = 0
        total_skipped = 0
        content_ok_count = 0

        session = requests.Session()
        session.headers.update(headers)

        for idx, url in enumerate(urls, 1):
            if self._is_cancelled:
                self.finished_signal.emit({"status": "cancelled"})
                return

            self.progress_signal.emit(idx, total_urls, f"正在请求页面: {url}")

            try:
                resp = session.get(url, timeout=8)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    parsed_items = self._parse_page(url, resp.text)

                    for item in parsed_items:
                        if self.fetch_content and item.get("url"):
                            content = self._fetch_article_content(
                                session, item["url"]
                            )
                            if content:
                                item["content"] = content
                                content_ok_count += 1

                        articles_batch.append(item)
                        total_fetched += 1

                        if len(articles_batch) >= self.batch_size:
                            inserted, skipped = self._save_batch(articles_batch)
                            total_inserted += inserted
                            total_skipped += skipped
                            self.batch_saved_signal.emit(inserted, skipped)
                            articles_batch.clear()

            except Exception as e:
                # 忽略单个页面的抓取错误，继续处理下一个
                pass

        # 刷新剩余批次
        if articles_batch:
            inserted, skipped = self._save_batch(articles_batch)
            total_inserted += inserted
            total_skipped += skipped
            self.batch_saved_signal.emit(inserted, skipped)

        self.finished_signal.emit(
            {
                "status": "success",
                "count": total_fetched,
                "inserted": total_inserted,
                "skipped": total_skipped,
                "content_ok": content_ok_count,
            }
        )

    def _generate_urls(self):
        p1_list = (
            [
                str(i).zfill(self.p1_cfg.get("pad", 1))
                for i in range(self.p1_cfg["start"], self.p1_cfg["end"] + 1)
            ]
            if self.p1_cfg.get("enabled", True)
            else [""]
        )

        p2_list = (
            [
                str(i).zfill(self.p2_cfg.get("pad", 1))
                for i in range(self.p2_cfg["start"], self.p2_cfg["end"] + 1)
            ]
            if self.p2_cfg.get("enabled", True)
            else [""]
        )

        urls = []
        for p1 in p1_list:
            for p2 in p2_list:
                try:
                    urls.append(self.url_template.format(p1, p2))
                except Exception:
                    urls.append(self.url_template)
        return urls

    def _parse_page(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        # 示例通用解析：针对链接列表进行抽取
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a["href"]
            if title and len(title) > 4 and not href.startswith("javascript"):
                full_url = urllib.parse.urljoin(base_url, href)
                articles.append(
                    {
                        "title": title,
                        "url": full_url,
                        "section": "",
                        "author": "",
                        "pub_date": "",
                        "subtitle": "",
                        "content": "",
                    }
                )
        return articles

    def _fetch_article_content(self, session, url):
        try:
            resp = session.get(url, timeout=5)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")
                paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
                return "\n\n".join(p for p in paragraphs if p)
        except Exception:
            pass
        return ""

    def _save_batch(self, batch):
        db = DatabaseManager(self.db_path)
        inserted, skipped = db.add_articles_batch(batch)
        db.close()
        return inserted, skipped