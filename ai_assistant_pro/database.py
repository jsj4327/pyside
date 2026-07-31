"""database.py — SQLite 数据库管理模块"""

import os
import sqlite3


class DatabaseManager:

    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_session(self):
        """兼容层：防止第三方逻辑或旧代码调用 create_session() 抛出 AttributeError"""
        return self

    def init_db(self):
        """初始化数据库结构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT,
                author TEXT,
                date TEXT,
                pub_date TEXT,
                section TEXT,
                source TEXT,
                content TEXT,
                url TEXT UNIQUE,
                is_fav INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_tags (
                article_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (article_id, tag_id),
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        conn.close()

    def save_articles(self, articles_list):
        """批量写入文章数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        inserted = 0
        skipped = 0

        for art in articles_list:
            try:
                cursor.execute(
                    """
                    INSERT INTO articles (title, subtitle, author, date, pub_date, section, source, content, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        art.get("title", ""),
                        art.get("subtitle", ""),
                        art.get("author", ""),
                        art.get("date", ""),
                        art.get("pub_date") or art.get("date", ""),
                        art.get("section", ""),
                        art.get("source", ""),
                        art.get("content", ""),
                        art.get("url", ""),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
            except Exception as e:
                print(f"[DatabaseManager] 插入数据失败: {e}")

        conn.commit()
        conn.close()
        return inserted, skipped

    def get_stats(self):
        """获取统计数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        conn.close()

        db_size_mb = 0.0
        if os.path.exists(self.db_path):
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)

        return {"total": total, "db_size_mb": db_size_mb}

    def get_sections(self):
        """获取已有文章的版面列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT section FROM articles WHERE section IS NOT NULL AND section != '' ORDER BY section"
        )
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def query_articles(
        self,
        page=1,
        page_size=20,
        section="",
        keyword="",
        kw="",
        is_fav=False,
        **kwargs,
    ):
        """分页与条件检索"""
        search_kw = (keyword or kw or "").strip()
        conn = self.get_connection()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if section and section.strip():
            where_clauses.append("section = ?")
            params.append(section.strip())

        if is_fav:
            where_clauses.append("is_fav = 1")

        if search_kw:
            like_kw = f"%{search_kw}%"
            where_clauses.append(
                "(title LIKE ? OR content LIKE ? OR author LIKE ?)"
            )
            params.extend([like_kw, like_kw, like_kw])

        where_sql = (
            f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        )

        try:
            cursor.execute(
                f"SELECT COUNT(*) FROM articles {where_sql}", params
            )
            total = cursor.fetchone()[0]

            offset = (max(1, page) - 1) * page_size
            cursor.execute(
                f"""
                SELECT id, title, subtitle, author, date, pub_date, section, source, content, url, is_fav
                FROM articles
                {where_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """,
                params + [page_size, offset],
            )

            rows = [dict(r) for r in cursor.fetchall()]
            return total, rows
        except Exception as e:
            print(f"[DatabaseManager] query_articles 失败: {e}")
            return 0, []
        finally:
            conn.close()

    def get_article_detail(self, article_id):
        """获取详细内容与关联标签"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        article = dict(row)

        cursor.execute(
            """
            SELECT t.id, t.name FROM tags t
            JOIN article_tags at ON t.id = at.tag_id
            WHERE at.article_id = ?
        """,
            (article_id,),
        )
        article["tags"] = [(r["id"], r["name"]) for r in cursor.fetchall()]

        conn.close()
        return article

    def toggle_favorite(self, article_id):
        """切换收藏"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT is_fav FROM articles WHERE id = ?", (article_id,)
        )
        row = cursor.fetchone()
        new_status = 1 if (row and not row["is_fav"]) else 0

        cursor.execute(
            "UPDATE articles SET is_fav = ? WHERE id = ?",
            (new_status, article_id),
        )
        conn.commit()
        conn.close()
        return bool(new_status)

    def tag_article(self, article_id, tag_name):
        """关联标签"""
        if not tag_name or not tag_name.strip():
            return
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name.strip(),)
        )
        cursor.execute(
            "SELECT id FROM tags WHERE name = ?", (tag_name.strip(),)
        )
        tag_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag_id),
        )
        conn.commit()
        conn.close()

    def close(self):
        pass