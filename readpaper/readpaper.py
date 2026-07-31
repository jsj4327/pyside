# -*- coding:utf-8 -*-
"""
人民日报爬虫 - 万级数据高性能版
存储引擎：SQLite (WAL模式 + 批量事务 + 唯一索引)
"""
import sys
import os
import json
import re
import time
import random
import sqlite3
import threading
from datetime import datetime
from urllib.parse import urljoin, urlparse

from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit,
    QProgressBar, QTabWidget, QSplitter, QGroupBox, QGridLayout,
    QCheckBox, QComboBox, QSpinBox
)
from PySide2.QtCore import QThread, Signal, Qt, QSettings, QTimer
from PySide2.QtGui import QFont
import requests
from bs4 import BeautifulSoup

# ==================== 配置 ====================
APP_NAME = "AI_Assistant_Pro"
DEFAULT_URL = "http://paper.people.com.cn/rmrb/html/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
BATCH_SIZE = 50          # 每批提交事务的条数
MAX_LOG_LINES = 500      # 日志面板最大保留行数


# ==================== 数据库管理层 ====================
class ArticleDB:
    """SQLite 存储引擎，线程安全，支持万级+数据"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        """每线程独立连接（SQLite 不允许跨线程共享连接）"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")        # 写前日志，读写并发
            conn.execute("PRAGMA synchronous=NORMAL")      # 平衡性能与安全
            conn.execute("PRAGMA cache_size=-64000")       # 64MB 缓存
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
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

            CREATE INDEX IF NOT EXISTS idx_section  ON articles(section);
            CREATE INDEX IF NOT EXISTS idx_date     ON articles(pub_date);
            CREATE INDEX IF NOT EXISTS idx_crawled  ON articles(crawled_at);

            CREATE TABLE IF NOT EXISTS crawl_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                start_url   TEXT,
                started_at  TEXT DEFAULT (datetime('now','localtime')),
                finished_at TEXT,
                total_found INTEGER DEFAULT 0,
                total_saved INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'running'
            );
        """)
        conn.commit()

    def create_session(self, start_url):
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO crawl_sessions (start_url) VALUES (?)",
            (start_url,)
        )
        conn.commit()
        return cur.lastrowid

    def finish_session(self, session_id, total_found, total_saved, status='done'):
        conn = self._get_conn()
        conn.execute(
            """UPDATE crawl_sessions
               SET finished_at=datetime('now','localtime'),
                   total_found=?, total_saved=?, status=?
               WHERE id=?""",
            (total_found, total_saved, status, session_id)
        )
        conn.commit()

    def batch_insert(self, articles):
        """
        批量插入，返回 (新增数, 跳过数)
        使用 INSERT OR IGNORE 自动去重
        """
        conn = self._get_conn()
        rows = [
            (
                a['url'], a.get('title', ''), a.get('subtitle', ''),
                a.get('author', ''), a.get('date', ''),
                a.get('section', ''), a.get('source', ''),
                a.get('content', '')
            )
            for a in articles
        ]
        before = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        conn.executemany(
            """INSERT OR IGNORE INTO articles
               (url, title, subtitle, author, pub_date, section, source, content)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows
        )
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        inserted = after - before
        skipped = len(rows) - inserted
        return inserted, skipped

    def get_total_count(self):
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    def get_recent(self, limit=50):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self):
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        by_section = conn.execute(
            "SELECT section, COUNT(*) as cnt FROM articles GROUP BY section ORDER BY cnt DESC"
        ).fetchall()
        by_date = conn.execute(
            "SELECT pub_date, COUNT(*) as cnt FROM articles GROUP BY pub_date ORDER BY pub_date DESC LIMIT 10"
        ).fetchall()
        return {
            'total': total,
            'by_section': [(r['section'], r['cnt']) for r in by_section],
            'by_date': [(r['pub_date'], r['cnt']) for r in by_date]
        }

    def export_json(self, output_path, limit=None):
        conn = self._get_conn()
        if limit:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM articles ORDER BY id").fetchall()
        data = [dict(r) for r in rows]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return len(data)

    def export_txt(self, output_path, limit=None):
        conn = self._get_conn()
        if limit:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY section, id LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY section, id"
            ).fetchall()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"导出时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"总计: {len(rows)} 篇\n")
            f.write("=" * 60 + "\n")
            current_sec = None
            for i, r in enumerate(rows, 1):
                if r['section'] != current_sec:
                    current_sec = r['section']
                    f.write(f"\n{'─'*40}\n📌 {current_sec}\n{'─'*40}\n")
                f.write(f"  {i}. {r['title']}\n")
                f.write(f"     🔗 {r['url']}\n")
                f.write(f"     📅 {r['pub_date']}  ✍️ {r['author']}\n\n")
        return len(rows)

    def export_single_txt(self, output_dir, limit=None):
        """导出每篇文章为独立TXT（按需调用，非默认）"""
        conn = self._get_conn()
        if limit:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM articles ORDER BY id").fetchall()
        os.makedirs(output_dir, exist_ok=True)
        count = 0
        for i, r in enumerate(rows, 1):
            if not r['content']:
                continue
            name = re.sub(r'[\\/:*?"<>|]', '', r['title'])[:80]
            filepath = os.path.join(output_dir, f"{i:05d}_{name}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"标题：{r['title']}\n")
                if r['subtitle']:
                    f.write(f"引题：{r['subtitle']}\n")
                f.write(f"作者：{r['author']}\n")
                f.write(f"日期：{r['pub_date']}\n")
                f.write(f"版面：{r['section']}\n")
                f.write(f"链接：{r['url']}\n")
                f.write("=" * 60 + "\n\n")
                f.write(r['content'])
            count += 1
        return count

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ==================== 爬虫工作线程 ====================
class CrawlerThread(QThread):
    log_signal = Signal(str, str)
    progress_signal = Signal(int, int, str)   # current, total, phase
    finished_signal = Signal(dict)
    batch_saved_signal = Signal(int, int)     # inserted, skipped

    def __init__(self, url, db_path, fetch_content=True):
        super().__init__()
        self.url = url
        self.db_path = db_path
        self.fetch_content = fetch_content
        self._is_cancelled = False
        self._db = None

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self._db = ArticleDB(self.db_path)
            session_id = self._db.create_session(self.url)
            self.log_signal.emit(f"🚀 开始爬取: {self.url}", "info")
            self.log_signal.emit(f"💾 数据库: {self.db_path}", "info")
            self.log_signal.emit(
                f"📊 库中已有: {self._db.get_total_count()} 条", "info"
            )

            # ===== 第一 + 第二阶段 =====
            articles = self._crawl_articles()

            if self._is_cancelled:
                self._db.finish_session(session_id, len(articles), 0, 'cancelled')
                self.finished_signal.emit({"status": "cancelled"})
                return

            if not articles:
                self._db.finish_session(session_id, 0, 0, 'empty')
                self.finished_signal.emit({"status": "empty"})
                return

            # 先批量写入列表数据（即使不抓正文也保存）
            total_inserted, total_skipped = self._batch_save(articles)
            self.log_signal.emit(
                f"💾 列表写入完成: 新增 {total_inserted}, 跳过 {total_skipped}",
                "success"
            )

            # ===== 第三阶段：抓取正文 =====
            if self.fetch_content:
                self.log_signal.emit(f"\n{'='*50}", "info")
                self.log_signal.emit(
                    f"📖 第三阶段：抓取 {len(articles)} 篇文章正文", "info"
                )
                self.log_signal.emit(f"{'='*50}", "info")
                content_ok = self._crawl_contents(articles)
                self.log_signal.emit(
                    f"✅ 正文抓取完成: {content_ok}/{len(articles)} 篇成功",
                    "success"
                )

            if self._is_cancelled:
                self._db.finish_session(
                    session_id, len(articles), total_inserted, 'cancelled'
                )
                self.finished_signal.emit({"status": "cancelled"})
                return

            self._db.finish_session(
                session_id, len(articles), total_inserted, 'done'
            )

            stats = self._db.get_stats()
            self.finished_signal.emit({
                "status": "success",
                "count": len(articles),
                "inserted": total_inserted,
                "skipped": total_skipped,
                "db_total": stats['total']
            })

        except Exception as e:
            self.finished_signal.emit({"status": "error", "message": str(e)})
        finally:
            if self._db:
                self._db.close()

    # ---------- 批量写入 ----------
    def _batch_save(self, articles):
        """分批写入数据库，每 BATCH_SIZE 条提交一次事务"""
        total_ins, total_skip = 0, 0
        for i in range(0, len(articles), BATCH_SIZE):
            if self._is_cancelled:
                break
            batch = articles[i:i + BATCH_SIZE]
            ins, skip = self._db.batch_insert(batch)
            total_ins += ins
            total_skip += skip
            self.batch_saved_signal.emit(ins, skip)
        return total_ins, total_skip

    # ---------- 网络请求 ----------
    def _fetch_page(self, url, retries=2):
        headers = {"User-Agent": USER_AGENT}
        for attempt in range(retries + 1):
            if self._is_cancelled:
                return None
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                if resp.encoding and resp.encoding.lower() == 'iso-8859-1':
                    resp.encoding = resp.apparent_encoding
                return resp.text
            except requests.RequestException as e:
                if attempt < retries:
                    self.log_signal.emit(
                        f"⏳ 重试({attempt+1}/{retries}): {e}", "warn"
                    )
                    time.sleep(1)
                else:
                    self.log_signal.emit(f"❌ 失败: {url}", "error")
                    return None
        return None

    def _extract_date_from_url(self, url):
        m = re.search(r'/(\d{4})(\d{2})/(\d{2})/', url)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return datetime.now().strftime("%Y-%m-%d")

    # ---------- 第一 + 第二阶段 ----------
    def _crawl_articles(self):
        index_html = self._fetch_page(self.url)
        if not index_html:
            return []

        soup = BeautifulSoup(index_html, 'html.parser')
        sections = []
        for a in soup.select('div.swiper-slide a#pageLink[href]'):
            href = a.get('href', '')
            name = a.get_text(strip=True)
            if not href or not name or '广告' in name:
                continue
            sections.append({'name': name, 'url': urljoin(self.url, href)})

        self.log_signal.emit(
            f"📰 第一阶段: {len(sections)} 个版面", "info"
        )
        if not sections:
            return []

        all_articles = []
        seen = set()
        for idx, sec in enumerate(sections):
            if self._is_cancelled:
                break
            self.progress_signal.emit(idx, len(sections), "版面解析")
            self.log_signal.emit(
                f"📄 [{idx+1}/{len(sections)}] {sec['name']}", "info"
            )
            html = self._fetch_page(sec['url'])
            if not html:
                continue
            page_soup = BeautifulSoup(html, 'html.parser')
            links = page_soup.select('div.news ul.news-list li a[href]')
            self.log_signal.emit(f"   📝 {len(links)} 篇", "info")

            for a in links:
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if not title or not href:
                    continue
                full_url = urljoin(sec['url'], href)
                norm = urlparse(full_url)._replace(fragment='').geturl()
                if norm in seen:
                    continue
                seen.add(norm)
                all_articles.append({
                    'title': title,
                    'url': full_url,
                    'subtitle': '',
                    'author': '',
                    'date': self._extract_date_from_url(full_url),
                    'section': sec['name'],
                    'source': urlparse(full_url).netloc,
                    'content': ''
                })
            time.sleep(random.uniform(0.3, 0.8))

        self.log_signal.emit(
            f"✅ 第二阶段: {len(all_articles)} 篇文章", "success"
        )
        return all_articles

    # ---------- 第三阶段 ----------
    def _crawl_contents(self, articles):
        total = len(articles)
        ok = 0
        pending_updates = []

        for idx, art in enumerate(articles):
            if self._is_cancelled:
                break
            self.progress_signal.emit(idx, total, "正文抓取")
            self.log_signal.emit(
                f"📖 [{idx+1}/{total}] {art['title'][:35]}...", "info"
            )

            html = self._fetch_page(art['url'])
            if not html:
                continue

            parsed = self._parse_article_page(html)
            if parsed and parsed.get('content'):
                art.update(parsed)
                pending_updates.append(art)
                ok += 1
                self.log_signal.emit(
                    f"   ✅ {len(art['content'])} 字", "success"
                )
            else:
                self.log_signal.emit("   ⚠️ 解析失败", "warn")

            # 批量回写正文到数据库
            if len(pending_updates) >= BATCH_SIZE:
                self._update_contents_in_db(pending_updates)
                pending_updates.clear()

            time.sleep(random.uniform(0.3, 1.0))

        # 写入剩余
        if pending_updates:
            self._update_contents_in_db(pending_updates)

        self.progress_signal.emit(total, total, "正文抓取")
        return ok

    def _update_contents_in_db(self, articles):
        """批量更新正文到已有记录"""
        conn = self._db._get_conn()
        conn.executemany(
            """UPDATE articles
               SET title=?, subtitle=?, author=?, pub_date=?, content=?
               WHERE url=?""",
            [
                (
                    a.get('title', ''), a.get('subtitle', ''),
                    a.get('author', ''), a.get('date', ''),
                    a.get('content', ''), a['url']
                )
                for a in articles
            ]
        )
        conn.commit()

    def _parse_article_page(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        result = {}

        # 标题
        h1 = soup.select_one('div.article h1') or soup.find('h1')
        result['title'] = h1.get_text(strip=True) if h1 else ''

        # 副标题
        h3 = soup.select_one('div.article h3')
        result['subtitle'] = h3.get_text(strip=True) if h3 else ''

        # 作者 + 日期
        sec_p = soup.select_one('p.sec')
        if sec_p:
            sec_text = sec_p.get_text(strip=True)
            result['author'] = re.sub(r'《人民日报》.*$', '', sec_text).strip()
            date_span = sec_p.select_one('span.newstime')
            if date_span:
                result['date'] = date_span.get_text(strip=True)
            else:
                dm = re.search(r'(\d{4})年(\d{2})月(\d{2})日', sec_text)
                if dm:
                    result['date'] = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"

        # 正文
        body_tag = soup.find('body')
        if body_tag:
            paras = []
            for p in body_tag.find_all('p'):
                if 'sec' in (p.get('class') or []):
                    continue
                t = p.get_text(strip=True)
                if t:
                    paras.append(t)
            result['content'] = '\n\n'.join(paras)
        else:
            result['content'] = ''

        # enpproperty 注释补充
        for comment in soup.find_all(string=lambda t: t and 'enpproperty' in t):
            ct = str(comment)
            if not result.get('author'):
                m = re.search(r'<author>(.*?)</author>', ct)
                if m:
                    result['author'] = m.group(1).strip()
            if not result.get('title'):
                m = re.search(r'<title><p>(.*?)</p></title>', ct, re.DOTALL)
                if m:
                    result['title'] = m.group(1).strip()
            if not result.get('subtitle'):
                m = re.search(r'<introtitle><p>(.*?)</p></introtitle>', ct, re.DOTALL)
                if m:
                    result['subtitle'] = m.group(1).strip()

        return result


# ==================== 爬虫 Tab ====================
class CrawlerTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings(APP_NAME, "Crawler")
        self.save_dir = self.settings.value(
            "save_dir",
            os.path.join(os.path.expanduser("~"), "CrawledArticles")
        )
        self.db_path = os.path.join(self.save_dir, "articles.db")
        self.thread = None
        self._log_count = 0
        self.init_ui()

    def init_ui(self):
        main_splitter = QSplitter(Qt.Vertical)

        # ===== 控制面板 =====
        ctrl = QWidget()
        ctrl_layout = QVBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)

        # URL + 目录
        url_group = QGroupBox("🌐 目标设置")
        gl = QGridLayout(url_group)
        gl.addWidget(QLabel("网址:"), 0, 0)
        self.url_edit = QLineEdit(DEFAULT_URL)
        gl.addWidget(self.url_edit, 0, 1)
        btn_def = QPushButton("默认")
        btn_def.setFixedWidth(60)
        btn_def.clicked.connect(lambda: self.url_edit.setText(DEFAULT_URL))
        gl.addWidget(btn_def, 0, 2)

        gl.addWidget(QLabel("目录:"), 1, 0)
        self.path_edit = QLineEdit(self.save_dir)
        self.path_edit.setReadOnly(True)
        gl.addWidget(self.path_edit, 1, 1)
        btn_br = QPushButton("浏览...")
        btn_br.setFixedWidth(60)
        btn_br.clicked.connect(self.browse_folder)
        gl.addWidget(btn_br, 1, 2)
        ctrl_layout.addWidget(url_group)

        # 选项行
        opt = QHBoxLayout()
        self.chk_content = QCheckBox("📖 抓取正文")
        self.chk_content.setChecked(True)
        opt.addWidget(self.chk_content)

        opt.addWidget(QLabel("  批次大小:"))
        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(10, 500)
        self.spin_batch.setValue(BATCH_SIZE)
        self.spin_batch.setSuffix(" 条/批")
        opt.addWidget(self.spin_batch)
        opt.addStretch()

        # 数据库信息
        self.lbl_db_info = QLabel("📊 数据库: --")
        self.lbl_db_info.setStyleSheet("color:#666; font-size:11px;")
        opt.addWidget(self.lbl_db_info)
        ctrl_layout.addLayout(opt)

        # 按钮行
        act = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始爬取")
        self.btn_start.setStyleSheet("""
            QPushButton { background:#1976D2; color:white; font-weight:bold;
                          padding:8px 20px; border-radius:4px; font-size:13px; }
            QPushButton:hover { background:#1565C0; }
            QPushButton:disabled { background:#BDBDBD; }""")
        self.btn_start.clicked.connect(self.start_crawl)

        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_crawl)

        self.btn_export = QPushButton("📤 导出")
        self.btn_export.clicked.connect(self.show_export_menu)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.lbl_phase = QLabel("")
        self.lbl_phase.setStyleSheet("color:#1976D2; font-size:11px;")

        act.addWidget(self.btn_start)
        act.addWidget(self.btn_stop)
        act.addWidget(self.btn_export)
        act.addWidget(self.progress_bar, 1)
        act.addWidget(self.lbl_phase)
        ctrl_layout.addLayout(act)

        # ===== 日志 + 预览 =====
        bottom = QSplitter(Qt.Horizontal)

        log_w = QWidget()
        ll = QVBoxLayout(log_w)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("<b>📋 运行日志</b>"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit { background:#FAFAFA; font-family:'Consolas','Microsoft YaHei';
                        font-size:12px; border:1px solid #E0E0E0; border-radius:4px;
                        padding:6px; }""")
        ll.addWidget(self.log_text)

        pv_w = QWidget()
        pl = QVBoxLayout(pv_w)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(QLabel("<b>📊 数据库统计</b>"))
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("""
            QTextEdit { background:#F5F5F5; font-size:12px;
                        border:1px solid #E0E0E0; border-radius:4px; padding:6px; }""")
        pl.addWidget(self.stats_text)

        bottom.addWidget(log_w)
        bottom.addWidget(pv_w)
        bottom.setStretchFactor(0, 3)
        bottom.setStretchFactor(1, 2)

        main_splitter.addWidget(ctrl)
        main_splitter.addWidget(bottom)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(main_splitter)

        # 定时刷新数据库统计
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_db_stats)
        self._timer.start(5000)
        self.refresh_db_stats()

    # ---------- 数据库统计 ----------
    def refresh_db_stats(self):
        try:
            if not os.path.exists(self.db_path):
                self.lbl_db_info.setText("📊 数据库: 尚未创建")
                return
            db = ArticleDB(self.db_path)
            stats = db.get_stats()
            db.close()

            self.lbl_db_info.setText(
                f"📊 数据库: {stats['total']} 条 | "
                f"{os.path.getsize(self.db_path) / 1024 / 1024:.1f} MB"
            )

            lines = [f"<b>总计: {stats['total']} 篇</b><br><br>"]
            lines.append("<b>按版面:</b><br>")
            for sec, cnt in stats['by_section'][:15]:
                lines.append(f"&nbsp;&nbsp;{sec}: {cnt}<br>")
            lines.append("<br><b>按日期:</b><br>")
            for dt, cnt in stats['by_date']:
                lines.append(f"&nbsp;&nbsp;{dt}: {cnt}<br>")
            self.stats_text.setHtml("".join(lines))
        except Exception:
            pass

    # ---------- 导出 ----------
    def show_export_menu(self):
        from PySide2.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        a1 = menu.addAction("导出 JSON（全部）")
        a2 = menu.addAction("导出 TXT 索引（全部）")
        a3 = menu.addAction("导出单篇 TXT（全部）")
        a4 = menu.addAction("导出 JSON（最近100条）")
        action = menu.exec_(self.btn_export.mapToGlobal(
            self.btn_export.rect().bottomLeft()
        ))
        if not action:
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            db = ArticleDB(self.db_path)
            if action == a1:
                p = os.path.join(self.save_dir, f"export_{ts}.json")
                n = db.export_json(p)
                self.status_message.emit(f"✅ 导出 {n} 条 → {p}")
            elif action == a2:
                p = os.path.join(self.save_dir, f"export_{ts}.txt")
                n = db.export_txt(p)
                self.status_message.emit(f"✅ 导出 {n} 条 → {p}")
            elif action == a3:
                d = os.path.join(self.save_dir, f"export_{ts}")
                n = db.export_single_txt(d)
                self.status_message.emit(f"✅ 导出 {n} 篇 → {d}/")
            elif action == a4:
                p = os.path.join(self.save_dir, f"export_recent_{ts}.json")
                n = db.export_json(p, limit=100)
                self.status_message.emit(f"✅ 导出 {n} 条 → {p}")
            db.close()
        except Exception as e:
            self.status_message.emit(f"❌ 导出失败: {e}")

    # ---------- 爬取控制 ----------
    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录", self.save_dir)
        if d:
            self.save_dir = d
            self.db_path = os.path.join(d, "articles.db")
            self.path_edit.setText(d)
            self.settings.setValue("save_dir", d)
            self.refresh_db_stats()

    def start_crawl(self):
        global BATCH_SIZE
        url = self.url_edit.text().strip()
        if not url:
            self.status_message.emit("⚠️ 请输入网址")
            return

        os.makedirs(self.save_dir, exist_ok=True)
        BATCH_SIZE = self.spin_batch.value()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_text.clear()
        self._log_count = 0
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.thread = CrawlerThread(
            url, self.db_path, self.chk_content.isChecked()
        )
        self.thread.log_signal.connect(self.append_log)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.batch_saved_signal.connect(self.on_batch_saved)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def stop_crawl(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.append_log("⏹ 正在停止...", "warn")

    def append_log(self, msg, level="info"):
        self._log_count += 1
        # 日志超限清理，防止万级操作时内存膨胀
        if self._log_count > MAX_LOG_LINES:
            self.log_text.clear()
            self._log_count = 0
            self.log_text.append(
                '<span style="color:#999">--- 日志已截断 ---</span>'
            )
        colors = {
            "info": "#333", "success": "#2E7D32",
            "error": "#C62828", "warn": "#E65100"
        }
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(
            f'<span style="color:#999">[{ts}]</span> '
            f'<span style="color:{colors.get(level,"#333")}">{msg}</span>'
        )
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_progress(self, cur, total, phase):
        self.lbl_phase.setText(f"[{phase}]")
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(cur)
            self.progress_bar.setFormat(f"{cur}/{total} ({phase})")

    def on_batch_saved(self, ins, skip):
        self.append_log(
            f"💾 批次写入: +{ins} 新增, {skip} 跳过(重复)", "info"
        )

    def on_finished(self, result):
        self.progress_bar.setVisible(False)
        self.lbl_phase.setText("")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.refresh_db_stats()

        s = result.get("status")
        if s == "success":
            self.status_message.emit(
                f"✅ 完成: 发现 {result['count']} 篇, "
                f"新增 {result['inserted']}, "
                f"跳过 {result['skipped']}, "
                f"库中共 {result['db_total']} 条"
            )
        elif s == "empty":
            self.status_message.emit("⚠️ 未找到文章")
        elif s == "cancelled":
            self.status_message.emit("⏹ 已取消（已保存部分数据）")
        else:
            self.status_message.emit(f"❌ {result.get('message','未知错误')}")

    def cleanup(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.thread.wait(3000)


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Assistant Pro - 万级数据版")
        self.init_ui()
        self._resize(0.85)

    def _resize(self, ratio):
        scr = QApplication.primaryScreen()
        if not scr:
            self.resize(1280, 800)
            return
        g = scr.availableGeometry()
        w, h = int(g.width()*ratio), int(g.height()*ratio)
        self.setGeometry(
            g.x()+(g.width()-w)//2, g.y()+(g.height()-h)//2, w, h
        )

    def init_ui(self):
        self.tabs = QTabWidget()
        self.crawler = CrawlerTab()
        self.crawler.status_message.connect(
            lambda m: self.statusBar().showMessage(m, 5000)
        )
        self.tabs.addTab(self.crawler, "🕷️ 文章爬取")

        ph = QWidget()
        vl = QVBoxLayout(ph)
        vl.setAlignment(Qt.AlignCenter)
        vl.addWidget(QLabel("<h2 style='color:#aaa'>🚧 开发中</h2>"))
        self.tabs.addTab(ph, "📚 知识库")

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("就绪")

    def closeEvent(self, e):
        self.crawler.cleanup()
        super().closeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())