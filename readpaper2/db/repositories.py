# db/repositories.py
"""
数据访问对象 (DAO)：封装对 SQLite 的数据增删改查操作与事务管理。
"""
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from db.connection import DatabaseConnection
from db.schema import init_database

logger = logging.getLogger(__name__)

class ArticleRepository:
    def __init__(self, db_conn: DatabaseConnection):
        self.db_conn = db_conn
        init_database(self.db_conn.get_connection())

    def get_conn(self) -> sqlite3.Connection:
        return self.db_conn.get_connection()

    def insert_articles_batch(self, articles: List[Dict[str, Any]]) -> int:
        if not articles:
            return 0
        conn = self.get_conn()
        cursor = conn.cursor()
        inserted_count = 0
        try:
            conn.execute("BEGIN TRANSACTION;")
            for item in articles:
                content = item.get("content", "")
                word_count = len(content)
                cursor.execute("""
                    INSERT INTO articles (title, subtitle, author, date, page_num, page_name, url, content, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("title", "").strip(),
                    item.get("subtitle", "").strip(),
                    item.get("author", "").strip(),
                    item.get("date", "").strip(),
                    item.get("page_num", "").strip(),
                    item.get("page_name", "").strip(),
                    item.get("url", "").strip(),
                    content,
                    word_count
                ))
                inserted_count += 1
            conn.commit()
            logger.info(f"批量插入文章成功，成功写入 {inserted_count} 条记录")
        except sqlite3.IntegrityError:
            conn.rollback()
            # 退回到单条容错插入模式
            inserted_count = self._insert_articles_one_by_one(articles)
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"批量插入文章异常，已回滚: {str(e)}")
        return inserted_count

    def _insert_articles_one_by_one(self, articles: List[Dict[str, Any]]) -> int:
        conn = self.get_conn()
        cursor = conn.cursor()
        count = 0
        for item in articles:
            try:
                content = item.get("content", "")
                cursor.execute("""
                    INSERT INTO articles (title, subtitle, author, date, page_num, page_name, url, content, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("title", "").strip(),
                    item.get("subtitle", "").strip(),
                    item.get("author", "").strip(),
                    item.get("date", "").strip(),
                    item.get("page_num", "").strip(),
                    item.get("page_name", "").strip(),
                    item.get("url", "").strip(),
                    content,
                    len(content)
                ))
                conn.commit()
                count += 1
            except sqlite3.IntegrityError:
                pass
            except sqlite3.Error as e:
                logger.warning(f"跳过冲突/异常文章 [{item.get('url')}]: {str(e)}")
        return count

    def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_fts_highlight(self, query_str: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """利用 FTS5 进行关键词高亮与 BM25 相关性得分排序"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # 预处理 FTS 关键字语法，防止语法注入冲突
        safe_query = '"' + query_str.replace('"', '""') + '"'
        sql = """
            SELECT 
                a.id, a.title, a.subtitle, a.author, a.date, a.page_num, a.page_name, a.url, a.word_count,
                snippet(articles_fts, 3, '<font color="#f56c6c"><b>', '</b></font>', '...', 30) AS highlighted_snippet
            FROM articles a
            JOIN articles_fts f ON a.id = f.rowid
            WHERE articles_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        try:
            cursor.execute(sql, (safe_query, limit, offset))
            return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"FTS5 高亮查询失败, 降级至传统 SQL 匹配: {str(e)}")
            return self.search_sql(keyword=query_str, limit=limit, offset=offset)

    def search_sql(self, keyword: str = "", start_date: str = "", end_date: str = "",
                   fav_only: bool = False, tag_id: Optional[int] = None,
                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        conditions = []
        params = []

        sql = "SELECT DISTINCT a.id, a.title, a.subtitle, a.author, a.date, a.page_num, a.page_name, a.url, a.content, a.word_count FROM articles a"

        if fav_only:
            sql += " JOIN favorites f ON a.id = f.article_id"

        if tag_id is not None:
            sql += " JOIN article_tags at ON a.id = at.article_id"
            conditions.append("at.tag_id = ?")
            params.append(tag_id)

        if keyword:
            conditions.append("(a.title LIKE ? OR a.content LIKE ? OR a.author LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])

        if start_date:
            conditions.append("a.date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("a.date <= ?")
            params.append(end_date)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY a.date DESC, a.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def delete_article(self, article_id: int) -> bool:
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"删除文章 [{article_id}] 失败: {str(e)}")
            return False

    def is_favorite(self, article_id: int) -> bool:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM favorites WHERE article_id = ?", (article_id,))
        return cursor.fetchone() is not None

    def toggle_favorite(self, article_id: int) -> bool:
        conn = self.get_conn()
        cursor = conn.cursor()
        if self.is_favorite(article_id):
            cursor.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
            conn.commit()
            return False
        else:
            cursor.execute("INSERT INTO favorites (article_id) VALUES (?)", (article_id,))
            conn.commit()
            return True

    def get_tags_for_article(self, article_id: int) -> List[Dict[str, Any]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name, t.color_code FROM tags t
            JOIN article_tags at ON t.id = at.tag_id
            WHERE at.article_id = ?
        """, (article_id,))
        return [dict(r) for r in cursor.fetchall()]

    def add_tag_to_article(self, article_id: int, tag_name: str):
        conn = self.get_conn()
        cursor = conn.cursor()
        tag_name = tag_name.strip()
        if not tag_name:
            return
        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        row = cursor.fetchone()
        if row:
            tag_id = row["id"]
            cursor.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (article_id, tag_id))
        conn.commit()

    def remove_tag_from_article(self, article_id: int, tag_id: int):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM article_tags WHERE article_id = ? AND tag_id = ?", (article_id, tag_id))
        conn.commit()

    def get_all_tags(self) -> List[Dict[str, Any]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags ORDER BY name ASC")
        return [dict(r) for r in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM articles")
        total_articles = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM favorites")
        total_favs = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM tags")
        total_tags = cursor.fetchone()["total"]

        cursor.execute("SELECT SUM(word_count) as total FROM articles")
        res_words = cursor.fetchone()["total"]
        total_words = res_words if res_words else 0

        return {
            "total_articles": total_articles,
            "total_favs": total_favs,
            "total_tags": total_tags,
            "total_words": total_words
        }