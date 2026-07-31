# -*- coding: utf-8 -*-

# -*- coding:utf-8 -*-
"""
knowledge_base.py — 知识库模块
功能：全文搜索(FTS5)、分页浏览、多维筛选、文章详情、收藏标注、统计概览
依赖：PySide2, sqlite3（标准库）
数据库：与爬虫模块共享 articles.db，自动创建 FTS5 索引与扩展表
"""

import os
import re
import sqlite3
import threading
import math
from datetime import datetime

from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QGroupBox, QTabWidget,
    QAbstractItemView, QMenu, QAction, QFileDialog,
    QMessageBox, QFrame, QScrollArea, QSizePolicy,
    QToolButton, QStyle, QCheckBox   # 加上这个
)
from PySide2.QtCore import (
    Qt, QThread, Signal, QTimer, QSize, QSettings
)
from PySide2.QtGui import QFont, QColor, QTextCursor, QPalette

# ==================== 常量 ====================
PAGE_SIZE = 50           # 每页条数
FTS_SNIPPET_LEN = 120    # 搜索摘要长度
APP_NAME = "AI_Assistant_Pro"


# ==================== 数据库层 ====================
class KnowledgeDB:
    """
    知识库数据库操作层
    - 兼容爬虫模块的 articles 表
    - 新增 FTS5 全文索引、favorites 收藏表、tags 标签表
    - 线程安全：每线程独立连接
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_schema()

    # ---------- 连接管理 ----------
    def _conn(self):
        if not hasattr(self._local, 'c') or self._local.c is None:
            c = sqlite3.connect(self.db_path, timeout=30)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA cache_size=-64000")
            c.row_factory = sqlite3.Row
            self._local.c = c
        return self._local.c

    # ---------- 建表 & FTS5 ----------
    def _ensure_schema(self):
        c = self._conn()
        c.executescript("""
            -- 确保主表存在（兼容爬虫模块）
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT NOT NULL UNIQUE,
                title       TEXT NOT NULL DEFAULT '',
                subtitle    TEXT DEFAULT '',
                author      TEXT DEFAULT '',
                pub_date    TEXT DEFAULT '',
                section     TEXT DEFAULT '',
                source      TEXT DEFAULT '',
                content     TEXT DEFAULT '',
                crawled_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            -- 收藏表
            CREATE TABLE IF NOT EXISTS favorites (
                article_id  INTEGER PRIMARY KEY,
                added_at    TEXT DEFAULT (datetime('now','localtime')),
                note        TEXT DEFAULT '',
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            );

            -- 标签表
            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE
            );

            -- 文章-标签关联
            CREATE TABLE IF NOT EXISTS article_tags (
                article_id  INTEGER,
                tag_id      INTEGER,
                PRIMARY KEY (article_id, tag_id),
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_art_section ON articles(section);
            CREATE INDEX IF NOT EXISTS idx_art_date    ON articles(pub_date);
        """)

        # FTS5 全文索引（title + content）
        try:
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
                USING fts5(
                    title, content,
                    content='articles',
                    content_rowid='id',
                    tokenize='unicode61'
                );
            """)
        except sqlite3.OperationalError:
            pass  # FTS5 不可用时降级为 LIKE 搜索

        # 同步 FTS 索引（增量：仅索引尚未收录的行）
        try:
            c.execute("""
                INSERT OR IGNORE INTO articles_fts(rowid, title, content)
                SELECT id, title, content FROM articles
                WHERE id NOT IN (SELECT rowid FROM articles_fts)
            """)
        except sqlite3.OperationalError:
            pass

        c.commit()

    def rebuild_fts(self):
        """全量重建 FTS 索引"""
        c = self._conn()
        try:
            c.execute("DELETE FROM articles_fts")
            c.execute("""
                INSERT INTO articles_fts(rowid, title, content)
                SELECT id, title, content FROM articles
            """)
            c.commit()
            return True
        except sqlite3.OperationalError:
            return False

    # ---------- 查询：分页列表 ----------
    def query_articles(self, page=1, page_size=PAGE_SIZE,
                       section='', date_from='', date_to='',
                       order_by='id DESC', fav_only=False):
        c = self._conn()
        where = []
        params = []

        if section:
            where.append("a.section = ?")
            params.append(section)
        if date_from:
            where.append("a.pub_date >= ?")
            params.append(date_from)
        if date_to:
            where.append("a.pub_date <= ?")
            params.append(date_to)
        if fav_only:
            where.append("a.id IN (SELECT article_id FROM favorites)")

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        # 总数
        cnt_sql = f"SELECT COUNT(*) FROM articles a{where_sql}"
        total = c.execute(cnt_sql, params).fetchone()[0]

        # 分页数据
        offset = (page - 1) * page_size
        data_sql = f"""
            SELECT a.id, a.title, a.subtitle, a.author, a.pub_date,
                   a.section, a.url,
                   CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END AS is_fav,
                   LENGTH(a.content) AS content_len
            FROM articles a
            LEFT JOIN favorites f ON f.article_id = a.id
            {where_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        rows = c.execute(data_sql, params + [page_size, offset]).fetchall()
        return total, [dict(r) for r in rows]

    # ---------- 查询：全文搜索 ----------
    def search_articles(self, keyword, page=1, page_size=PAGE_SIZE):
        c = self._conn()
        offset = (page - 1) * page_size

        # 尝试 FTS5
        try:
            # 转义 FTS5 特殊字符
            safe_kw = keyword.replace('"', '""')
            fts_query = f'"{safe_kw}"'

            cnt_sql = """
                SELECT COUNT(*) FROM articles_fts
                WHERE articles_fts MATCH ?
            """
            total = c.execute(cnt_sql, (fts_query,)).fetchone()[0]

            data_sql = """
                SELECT a.id, a.title, a.subtitle, a.author, a.pub_date,
                       a.section, a.url,
                       snippet(articles_fts, 1, '【', '】', '…', 30) AS snippet,
                       rank,
                       CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END AS is_fav
                FROM articles_fts
                JOIN articles a ON a.id = articles_fts.rowid
                LEFT JOIN favorites f ON f.article_id = a.id
                WHERE articles_fts MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """
            rows = c.execute(
                data_sql, (fts_query, page_size, offset)
            ).fetchall()
            return total, [dict(r) for r in rows], True

        except sqlite3.OperationalError:
            # 降级：LIKE 搜索
            like_kw = f"%{keyword}%"
            cnt_sql = """
                SELECT COUNT(*) FROM articles
                WHERE title LIKE ? OR content LIKE ?
            """
            total = c.execute(cnt_sql, (like_kw, like_kw)).fetchone()[0]

            data_sql = """
                SELECT a.id, a.title, a.subtitle, a.author, a.pub_date,
                       a.section, a.url,
                       '' AS snippet, 0 AS rank,
                       CASE WHEN f.article_id IS NOT NULL THEN 1 ELSE 0 END AS is_fav
                FROM articles a
                LEFT JOIN favorites f ON f.article_id = a.id
                WHERE a.title LIKE ? OR a.content LIKE ?
                ORDER BY a.id DESC
                LIMIT ? OFFSET ?
            """
            rows = c.execute(
                data_sql, (like_kw, like_kw, page_size, offset)
            ).fetchall()
            return total, [dict(r) for r in rows], False

    # ---------- 文章详情 ----------
    def get_article(self, article_id):
        c = self._conn()
        row = c.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        if not row:
            return None
        art = dict(row)

        # 是否收藏
        fav = c.execute(
            "SELECT note FROM favorites WHERE article_id = ?", (article_id,)
        ).fetchone()
        art['is_fav'] = fav is not None
        art['fav_note'] = fav['note'] if fav else ''

        # 标签
        tags = c.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN article_tags at ON at.tag_id = t.id
            WHERE at.article_id = ?
        """, (article_id,)).fetchall()
        art['tags'] = [(t['id'], t['name']) for t in tags]

        return art

    # ---------- 收藏 ----------
    def toggle_favorite(self, article_id, note=''):
        c = self._conn()
        exists = c.execute(
            "SELECT 1 FROM favorites WHERE article_id = ?", (article_id,)
        ).fetchone()
        if exists:
            c.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
            c.commit()
            return False
        else:
            c.execute(
                "INSERT INTO favorites (article_id, note) VALUES (?, ?)",
                (article_id, note)
            )
            c.commit()
            return True

    def update_fav_note(self, article_id, note):
        c = self._conn()
        c.execute(
            "UPDATE favorites SET note = ? WHERE article_id = ?",
            (note, article_id)
        )
        c.commit()

    # ---------- 标签 ----------
    def get_all_tags(self):
        c = self._conn()
        rows = c.execute("SELECT id, name FROM tags ORDER BY name").fetchall()
        return [(r['id'], r['name']) for r in rows]

    def add_tag(self, name):
        c = self._conn()
        c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        c.commit()
        return c.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]

    def tag_article(self, article_id, tag_name):
        tag_id = self.add_tag(tag_name)
        c = self._conn()
        c.execute(
            "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag_id)
        )
        c.commit()

    def untag_article(self, article_id, tag_id):
        c = self._conn()
        c.execute(
            "DELETE FROM article_tags WHERE article_id = ? AND tag_id = ?",
            (article_id, tag_id)
        )
        c.commit()

    # ---------- 筛选选项 ----------
    def get_sections(self):
        c = self._conn()
        rows = c.execute(
            "SELECT DISTINCT section FROM articles WHERE section != '' ORDER BY section"
        ).fetchall()
        return [r['section'] for r in rows]

    def get_date_range(self):
        c = self._conn()
        row = c.execute(
            "SELECT MIN(pub_date), MAX(pub_date) FROM articles WHERE pub_date != ''"
        ).fetchone()
        return row[0] or '', row[1] or ''

    # ---------- 统计 ----------
    def get_stats(self):
        c = self._conn()
        total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        with_content = c.execute(
            "SELECT COUNT(*) FROM articles WHERE content != ''"
        ).fetchone()[0]
        fav_count = c.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
        tag_count = c.execute("SELECT COUNT(*) FROM tags").fetchone()[0]

        by_section = c.execute("""
            SELECT section, COUNT(*) AS cnt
            FROM articles WHERE section != ''
            GROUP BY section ORDER BY cnt DESC LIMIT 20
        """).fetchall()

        by_date = c.execute("""
            SELECT pub_date, COUNT(*) AS cnt
            FROM articles WHERE pub_date != ''
            GROUP BY pub_date ORDER BY pub_date DESC LIMIT 30
        """).fetchall()

        top_authors = c.execute("""
            SELECT author, COUNT(*) AS cnt
            FROM articles WHERE author != ''
            GROUP BY author ORDER BY cnt DESC LIMIT 15
        """).fetchall()

        db_size = 0
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)

        return {
            'total': total,
            'with_content': with_content,
            'fav_count': fav_count,
            'tag_count': tag_count,
            'db_size_mb': db_size / 1024 / 1024,
            'by_section': [(r['section'], r['cnt']) for r in by_section],
            'by_date': [(r['pub_date'], r['cnt']) for r in by_date],
            'top_authors': [(r['author'], r['cnt']) for r in top_authors],
        }

    # ---------- 导出 ----------
    def export_filtered_json(self, path, section='', date_from='', date_to=''):
        c = self._conn()
        where, params = [], []
        if section:
            where.append("section = ?"); params.append(section)
        if date_from:
            where.append("pub_date >= ?"); params.append(date_from)
        if date_to:
            where.append("pub_date <= ?"); params.append(date_to)
        w = (" WHERE " + " AND ".join(where)) if where else ""
        rows = c.execute(f"SELECT * FROM articles{w} ORDER BY id", params).fetchall()
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([dict(r) for r in rows], f, ensure_ascii=False, indent=2)
        return len(rows)

    def close(self):
        if hasattr(self._local, 'c') and self._local.c:
            self._local.c.close()
            self._local.c = None


# ==================== 异步搜索线程 ====================
class SearchThread(QThread):
    result_signal = Signal(int, list, bool)   # total, rows, is_fts
    error_signal = Signal(str)

    def __init__(self, db_path, keyword, page, page_size):
        super().__init__()
        self.db_path = db_path
        self.keyword = keyword
        self.page = page
        self.page_size = page_size

    def run(self):
        try:
            db = KnowledgeDB(self.db_path)
            total, rows, is_fts = db.search_articles(
                self.keyword, self.page, self.page_size
            )
            db.close()
            self.result_signal.emit(total, rows, is_fts)
        except Exception as e:
            self.error_signal.emit(str(e))


class QueryThread(QThread):
    result_signal = Signal(int, list)   # total, rows

    def __init__(self, db_path, page, page_size, section, date_from, date_to,
                 order_by, fav_only):
        super().__init__()
        self.db_path = db_path
        self.page = page
        self.page_size = page_size
        self.section = section
        self.date_from = date_from
        self.date_to = date_to
        self.order_by = order_by
        self.fav_only = fav_only

    def run(self):
        try:
            db = KnowledgeDB(self.db_path)
            total, rows = db.query_articles(
                self.page, self.page_size,
                self.section, self.date_from, self.date_to,
                self.order_by, self.fav_only
            )
            db.close()
            self.result_signal.emit(total, rows)
        except Exception as e:
            self.result_signal.emit(0, [])


# ==================== 文章详情面板 ====================
class ArticleDetailWidget(QWidget):
    """右侧文章详情：正文 + 元数据 + 收藏/标签操作"""
    fav_changed = Signal()

    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题区
        self.lbl_title = QLabel("选择一篇文章查看详情")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#1a1a1a; padding:4px 0;"
        )
        layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel("")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setStyleSheet("font-size:13px; color:#555;")
        layout.addWidget(self.lbl_subtitle)

        # 元数据行
        meta_layout = QHBoxLayout()
        self.lbl_author = QLabel("")
        self.lbl_author.setStyleSheet("color:#1976D2; font-size:12px;")
        self.lbl_date = QLabel("")
        self.lbl_date.setStyleSheet("color:#888; font-size:12px;")
        self.lbl_section = QLabel("")
        self.lbl_section.setStyleSheet(
            "color:#fff; background:#78909C; border-radius:3px; "
            "padding:1px 6px; font-size:11px;"
        )
        meta_layout.addWidget(self.lbl_author)
        meta_layout.addWidget(self.lbl_date)
        meta_layout.addStretch()
        meta_layout.addWidget(self.lbl_section)
        layout.addLayout(meta_layout)

        # 操作按钮行
        btn_layout = QHBoxLayout()
        self.btn_fav = QPushButton("☆ 收藏")
        self.btn_fav.setCheckable(True)
        self.btn_fav.setStyleSheet("""
            QPushButton { border:1px solid #FFB300; border-radius:4px;
                          padding:4px 12px; font-size:12px; background:#FFFDE7; }
            QPushButton:checked { background:#FFB300; color:#fff; }
        """)
        self.btn_fav.clicked.connect(self._on_fav_click)

        self.btn_tag = QPushButton("🏷️ 标签")
        self.btn_tag.setStyleSheet(
            "border:1px solid #90A4AE; border-radius:4px; "
            "padding:4px 12px; font-size:12px;"
        )
        self.btn_tag.clicked.connect(self._on_tag_click)

        self.btn_open = QPushButton("🔗 原文")
        self.btn_open.setStyleSheet(
            "border:1px solid #90A4AE; border-radius:4px; "
            "padding:4px 12px; font-size:12px;"
        )
        self.btn_open.clicked.connect(self._on_open_url)

        self.lbl_tags = QLabel("")
        self.lbl_tags.setWordWrap(True)
        self.lbl_tags.setStyleSheet("font-size:11px; color:#00695C;")

        btn_layout.addWidget(self.btn_fav)
        btn_layout.addWidget(self.btn_tag)
        btn_layout.addWidget(self.btn_open)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.lbl_tags)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#E0E0E0;")
        layout.addWidget(line)

        # 正文
        self.txt_content = QPlainTextEdit()
        self.txt_content.setReadOnly(True)
        self.txt_content.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.txt_content.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Microsoft YaHei', 'SimSun', serif;
                font-size: 14px; line-height: 1.8;
                background: #FEFEFE; color: #333;
                border: 1px solid #E0E0E0; border-radius: 4px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.txt_content, 1)

        # 字数统计
        self.lbl_word_count = QLabel("")
        self.lbl_word_count.setStyleSheet("color:#999; font-size:11px;")
        layout.addWidget(self.lbl_word_count)

    # ---------- 加载文章 ----------
    def load_article(self, article_id):
        self.current_id = article_id
        db = KnowledgeDB(self.db_path)
        art = db.get_article(article_id)
        db.close()

        if not art:
            self.lbl_title.setText("文章不存在")
            return

        self.lbl_title.setText(art['title'])
        self.lbl_subtitle.setText(art.get('subtitle', ''))
        self.lbl_author.setText(f"✍️ {art.get('author', '未知')}")
        self.lbl_date.setText(f"📅 {art.get('pub_date', '')}")
        self.lbl_section.setText(art.get('section', ''))

        content = art.get('content', '')
        self.txt_content.setPlainText(content)
        self.lbl_word_count.setText(
            f"正文 {len(content)} 字 | 链接: {art.get('url', '')}"
        )

        # 收藏状态
        is_fav = art.get('is_fav', False)
        self.btn_fav.setChecked(is_fav)
        self.btn_fav.setText("★ 已收藏" if is_fav else "☆ 收藏")

        # 标签
        tags = art.get('tags', [])
        if tags:
            self.lbl_tags.setText(
                "🏷️ " + "  ".join(f"[{name}]" for _, name in tags)
            )
        else:
            self.lbl_tags.setText("")

    # ---------- 收藏 ----------
    def _on_fav_click(self):
        if self.current_id is None:
            return
        db = KnowledgeDB(self.db_path)
        added = db.toggle_favorite(self.current_id)
        db.close()
        self.btn_fav.setText("★ 已收藏" if added else "☆ 收藏")
        self.fav_changed.emit()

    # ---------- 标签 ----------
    def _on_tag_click(self):
        if self.current_id is None:
            return
        from PySide2.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "添加标签", "标签名称:")
        if ok and name.strip():
            db = KnowledgeDB(self.db_path)
            db.tag_article(self.current_id, name.strip())
            art = db.get_article(self.current_id)
            db.close()
            tags = art.get('tags', []) if art else []
            self.lbl_tags.setText(
                "🏷️ " + "  ".join(f"[{n}]" for _, n in tags)
            )

    # ---------- 打开原文 ----------
    def _on_open_url(self):
        if self.current_id is None:
            return
        db = KnowledgeDB(self.db_path)
        art = db.get_article(self.current_id)
        db.close()
        if art and art.get('url'):
            import webbrowser
            webbrowser.open(art['url'])


# ==================== 知识库主 Tab ====================
class KnowledgeTab(QWidget):
    status_message = Signal(str)

    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_page = 1
        self.total_count = 0
        self.search_mode = False
        self._search_thread = None
        self._query_thread = None
        self._init_ui()
        self._load_filters()

    # ==================== UI 构建 ====================
    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        # ===== 左侧：搜索 + 列表 =====
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # -- 搜索栏 --
        search_box = QGroupBox("🔍 搜索与筛选")
        sg = QGridLayout(search_box)

        sg.addWidget(QLabel("关键词:"), 0, 0)
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("输入关键词，回车搜索...")
        self.edit_search.returnPressed.connect(self._do_search)
        sg.addWidget(self.edit_search, 0, 1)
        btn_search = QPushButton("搜索")
        btn_search.setFixedWidth(60)
        btn_search.clicked.connect(self._do_search)
        sg.addWidget(btn_search, 0, 2)
        btn_clear = QPushButton("清除")
        btn_clear.setFixedWidth(60)
        btn_clear.clicked.connect(self._clear_search)
        sg.addWidget(btn_clear, 0, 3)

        sg.addWidget(QLabel("版面:"), 1, 0)
        self.cmb_section = QComboBox()
        self.cmb_section.addItem("全部版面", "")
        sg.addWidget(self.cmb_section, 1, 1)

        sg.addWidget(QLabel("排序:"), 1, 2)
        self.cmb_order = QComboBox()
        self.cmb_order.addItems([
            "最新优先", "最早优先", "标题排序"
        ])
        sg.addWidget(self.cmb_order, 1, 3)

        sg.addWidget(QLabel("日期从:"), 2, 0)
        self.edit_date_from = QLineEdit()
        self.edit_date_from.setPlaceholderText("2026-01-01")
        sg.addWidget(self.edit_date_from, 2, 1)
        sg.addWidget(QLabel("到:"), 2, 2)
        self.edit_date_to = QLineEdit()
        self.edit_date_to.setPlaceholderText("2026-12-31")
        sg.addWidget(self.edit_date_to, 2, 3)

        chk_fav = QHBoxLayout()
        self.chk_fav_only = QCheckBox("仅收藏")
        self.chk_fav_only.stateChanged.connect(lambda: self._goto_page(1))
        chk_fav.addWidget(self.chk_fav_only)
        chk_fav.addStretch()
        btn_apply = QPushButton("应用筛选")
        btn_apply.clicked.connect(lambda: self._goto_page(1))
        chk_fav.addWidget(btn_apply)
        sg.addLayout(chk_fav, 3, 0, 1, 4)

        left_layout.addWidget(search_box)

        # -- 结果统计 --
        self.lbl_result_info = QLabel("共 0 条结果")
        self.lbl_result_info.setStyleSheet("color:#666; font-size:12px; padding:2px 0;")
        left_layout.addWidget(self.lbl_result_info)

        # -- 文章列表表格 --
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "标题", "版面", "作者", "日期", "★"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget { font-size: 12px; gridline-color: #E0E0E0; }
            QTableWidget::item:selected { background: #E3F2FD; color: #1a1a1a; }
            QHeaderView::section { background: #F5F5F5; padding: 4px;
                                   border: 1px solid #E0E0E0; font-weight: bold; }
        """)
        self.table.cellClicked.connect(self._on_row_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.table, 1)

        # -- 分页控制 --
        page_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_prev.clicked.connect(lambda: self._goto_page(self.current_page - 1))
        self.lbl_page = QLabel("第 1 页")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("下一页 ▶")
        self.btn_next.clicked.connect(lambda: self._goto_page(self.current_page + 1))

        self.spin_page_size = QSpinBox()
        self.spin_page_size.setRange(20, 200)
        self.spin_page_size.setValue(PAGE_SIZE)
        self.spin_page_size.setSuffix(" 条/页")
        self.spin_page_size.valueChanged.connect(lambda: self._goto_page(1))

        page_layout.addWidget(self.btn_prev)
        page_layout.addWidget(self.lbl_page)
        page_layout.addWidget(self.btn_next)
        page_layout.addStretch()
        page_layout.addWidget(QLabel("每页:"))
        page_layout.addWidget(self.spin_page_size)
        left_layout.addLayout(page_layout)

        # ===== 右侧：详情 + 统计 =====
        right_tabs = QTabWidget()

        # Tab1: 文章详情
        self.detail = ArticleDetailWidget(self.db_path)
        self.detail.fav_changed.connect(lambda: self._refresh_current_page())
        right_tabs.addTab(self.detail, "📄 文章详情")

        # Tab2: 统计概览
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        self.txt_stats = QTextEdit()
        self.txt_stats.setReadOnly(True)
        self.txt_stats.setStyleSheet("font-size:12px; background:#FAFAFA;")
        stats_layout.addWidget(self.txt_stats)
        btn_refresh_stats = QPushButton("🔄 刷新统计")
        btn_refresh_stats.clicked.connect(self._refresh_stats)
        stats_layout.addWidget(btn_refresh_stats)
        right_tabs.addTab(stats_widget, "📊 统计概览")

        splitter.addWidget(left)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter)

    # ==================== 数据加载 ====================
    def _load_filters(self):
        """加载版面列表和日期范围"""
        if not os.path.exists(self.db_path):
            return
        try:
            db = KnowledgeDB(self.db_path)
            sections = db.get_sections()
            db.close()
            self.cmb_section.clear()
            self.cmb_section.addItem("全部版面", "")
            for s in sections:
                self.cmb_section.addItem(s, s)
        except Exception:
            pass

    def _get_order_sql(self):
        idx = self.cmb_order.currentIndex()
        return ["id DESC", "id ASC", "title ASC"][idx]

    def _goto_page(self, page):
        if page < 1:
            return
        self.current_page = page
        page_size = self.spin_page_size.value()

        if self.search_mode and self.edit_search.text().strip():
            self._do_search(page)
        else:
            self._do_query(page)

    def _do_query(self, page=None):
        if page is None:
            page = self.current_page
        self.search_mode = False
        page_size = self.spin_page_size.value()

        self._query_thread = QueryThread(
            self.db_path, page, page_size,
            self.cmb_section.currentData(),
            self.edit_date_from.text().strip(),
            self.edit_date_to.text().strip(),
            self._get_order_sql(),
            self.chk_fav_only.isChecked()
        )
        self._query_thread.result_signal.connect(self._on_query_result)
        self._query_thread.start()

    def _do_search(self, page=None):
        keyword = self.edit_search.text().strip()
        if not keyword:
            self._clear_search()
            return
        if page is None:
            page = 1
        self.search_mode = True
        self.current_page = page
        page_size = self.spin_page_size.value()

        self._search_thread = SearchThread(
            self.db_path, keyword, page, page_size
        )
        self._search_thread.result_signal.connect(self._on_search_result)
        self._search_thread.error_signal.connect(
            lambda e: self.status_message.emit(f"❌ 搜索失败: {e}")
        )
        self._search_thread.start()

    def _clear_search(self):
        self.edit_search.clear()
        self.search_mode = False
        self._goto_page(1)

    # ==================== 结果渲染 ====================
    def _on_query_result(self, total, rows):
        self.total_count = total
        self._render_table(total, rows)

    def _on_search_result(self, total, rows, is_fts):
        self.total_count = total
        engine = "FTS5" if is_fts else "LIKE"
        self.lbl_result_info.setText(
            f"🔍 搜索 \"{self.edit_search.text().strip()}\" — "
            f"{total} 条结果 (引擎: {engine})"
        )
        self._render_table(total, rows)

    def _render_table(self, total, rows):
        page_size = self.spin_page_size.value()
        total_pages = max(1, math.ceil(total / page_size))
        self.current_page = min(self.current_page, total_pages)

        self.lbl_result_info.setText(
            f"共 {total} 条结果 | 第 {self.current_page}/{total_pages} 页"
        )
        self.lbl_page.setText(f"第 {self.current_page}/{total_pages} 页")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        self.table.setRowCount(len(rows))
        for i, art in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(art['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(art['title']))
            self.table.setItem(i, 2, QTableWidgetItem(art.get('section', '')))
            self.table.setItem(i, 3, QTableWidgetItem(art.get('author', '')))
            self.table.setItem(i, 4, QTableWidgetItem(art.get('pub_date', '')))

            fav_item = QTableWidgetItem("★" if art.get('is_fav') else "")
            fav_item.setTextAlignment(Qt.AlignCenter)
            if art.get('is_fav'):
                fav_item.setForeground(QColor("#FFB300"))
            self.table.setItem(i, 5, fav_item)

            # 存储 id 到行
            self.table.item(i, 0).setData(Qt.UserRole, art['id'])

    def _on_row_click(self, row, col):
        item = self.table.item(row, 0)
        if item:
            article_id = item.data(Qt.UserRole)
            self.detail.load_article(article_id)

    def _refresh_current_page(self):
        self._goto_page(self.current_page)

    # ==================== 右键菜单 ====================
    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        article_id = item.data(Qt.UserRole)

        menu = QMenu(self)
        act_view = menu.addAction("📄 查看详情")
        act_fav = menu.addAction("★ 切换收藏")
        act_tag = menu.addAction("🏷️ 添加标签")
        act_copy = menu.addAction("📋 复制标题")
        act_open = menu.addAction("🔗 打开原文")

        action = menu.exec_(self.table.mapToGlobal(pos))
        if not action:
            return

        db = KnowledgeDB(self.db_path)
        if action == act_view:
            self.detail.load_article(article_id)
        elif action == act_fav:
            db.toggle_favorite(article_id)
            self._refresh_current_page()
        elif action == act_tag:
            from PySide2.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "添加标签", "标签名称:")
            if ok and name.strip():
                db.tag_article(article_id, name.strip())
                self.status_message.emit(f"✅ 已添加标签: {name.strip()}")
        elif action == act_copy:
            from PySide2.QtWidgets import QApplication
            title_item = self.table.item(row, 1)
            if title_item:
                QApplication.clipboard().setText(title_item.text())
                self.status_message.emit("📋 标题已复制")
        elif action == act_open:
            art = db.get_article(article_id)
            if art and art.get('url'):
                import webbrowser
                webbrowser.open(art['url'])
        db.close()

    # ==================== 统计 ====================
    def _refresh_stats(self):
        if not os.path.exists(self.db_path):
            self.txt_stats.setHtml("<p style='color:#999'>数据库尚未创建</p>")
            return
        try:
            db = KnowledgeDB(self.db_path)
            s = db.get_stats()
            db.close()

            lines = []
            lines.append(f"<h3>📊 数据库概览</h3>")
            lines.append(f"<p>文章总数: <b>{s['total']}</b></p>")
            lines.append(f"<p>含正文: <b>{s['with_content']}</b></p>")
            lines.append(f"<p>收藏: <b>{s['fav_count']}</b> | 标签: <b>{s['tag_count']}</b></p>")
            lines.append(f"<p>数据库大小: <b>{s['db_size_mb']:.1f} MB</b></p>")
            lines.append("<hr>")

            lines.append("<h4>📰 按版面</h4><table border='1' cellpadding='3' style='border-collapse:collapse;font-size:12px;'>")
            lines.append("<tr><th>版面</th><th>数量</th></tr>")
            for sec, cnt in s['by_section']:
                lines.append(f"<tr><td>{sec}</td><td>{cnt}</td></tr>")
            lines.append("</table><br>")

            lines.append("<h4>📅 按日期 (近30天)</h4><table border='1' cellpadding='3' style='border-collapse:collapse;font-size:12px;'>")
            lines.append("<tr><th>日期</th><th>数量</th></tr>")
            for dt, cnt in s['by_date']:
                lines.append(f"<tr><td>{dt}</td><td>{cnt}</td></tr>")
            lines.append("</table><br>")

            lines.append("<h4>✍️ 高频作者</h4><table border='1' cellpadding='3' style='border-collapse:collapse;font-size:12px;'>")
            lines.append("<tr><th>作者</th><th>篇数</th></tr>")
            for author, cnt in s['top_authors']:
                lines.append(f"<tr><td>{author}</td><td>{cnt}</td></tr>")
            lines.append("</table>")

            self.txt_stats.setHtml("".join(lines))
        except Exception as e:
            self.txt_stats.setHtml(f"<p style='color:red'>加载失败: {e}</p>")

    # ==================== 公共接口 ====================
    def refresh(self):
        """外部调用：刷新数据（如爬虫完成后）"""
        self._load_filters()
        self._goto_page(1)
        self._refresh_stats()