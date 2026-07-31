# db/schema.py
"""
数据库 Schema 初始化、版本迁移与 FTS5 全文索引构建。
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_database(conn: sqlite3.Connection):
    """初始化建表及触发器结构"""
    cursor = conn.cursor()
    try:
        # 1. 文章数据主表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subtitle TEXT,
            author TEXT,
            date TEXT NOT NULL,
            page_num TEXT,
            page_name TEXT,
            url TEXT UNIQUE NOT NULL,
            content TEXT,
            word_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. 索引优化
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);")

        # 3. 爬取日志与会话记录
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawl_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT DEFAULT 'RUNNING',
            total_found INTEGER DEFAULT 0,
            total_downloaded INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. 文章收藏表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL UNIQUE,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
        );
        """)

        # 5. 标签体系
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color_code TEXT DEFAULT '#409EFF'
        );
        """)

        # 6. 文章与标签多对多关联
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (article_id, tag_id),
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );
        """)

        # 7. SQLite FTS5 全文检索虚拟表
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            subtitle,
            author,
            content,
            content='articles',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        """)

        # 8. 同步 FTS 虚拟表数据的自动触发器
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, subtitle, author, content)
            VALUES (new.id, new.title, new.subtitle, new.author, new.content);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, subtitle, author, content)
            VALUES('delete', old.id, old.title, old.subtitle, old.author, old.content);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, subtitle, author, content)
            VALUES('delete', old.id, old.title, old.subtitle, old.author, old.content);
            INSERT INTO articles_fts(rowid, title, subtitle, author, content)
            VALUES (new.id, new.title, new.subtitle, new.author, new.content);
        END;
        """)

        conn.commit()
        logger.info("数据库 Schema 与 FTS5 全文索引引擎校验初始化完毕。")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"初始化 Schema 阶段发生异常: {str(e)}")
        raise e