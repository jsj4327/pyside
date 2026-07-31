"""ui/article_detail.py — 文章详情展示与交互组件"""

import webbrowser
from PySide2.QtCore import Signal
from PySide2.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from database import DatabaseManager


class ArticleDetailWidget(QWidget):
    fav_changed = Signal()

    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_title = QLabel("选择一篇文章查看详情")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#1a1a1a;"
        )
        layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel("")
        self.lbl_subtitle.setStyleSheet("font-size:13px; color:#555;")
        layout.addWidget(self.lbl_subtitle)

        meta_layout = QHBoxLayout()
        self.lbl_author = QLabel("")
        self.lbl_author.setStyleSheet("color:#1976D2; font-size:12px;")
        self.lbl_date = QLabel("")
        self.lbl_date.setStyleSheet("color:#888; font-size:12px;")
        self.lbl_section = QLabel("")
        self.lbl_section.setStyleSheet(
            "color:#fff; background:#78909C; border-radius:3px; padding:1px 6px; font-size:11px;"
        )
        meta_layout.addWidget(self.lbl_author)
        meta_layout.addWidget(self.lbl_date)
        meta_layout.addStretch()
        meta_layout.addWidget(self.lbl_section)
        layout.addLayout(meta_layout)

        btn_layout = QHBoxLayout()
        self.btn_fav = QPushButton("☆ 收藏")
        self.btn_fav.setCheckable(True)
        self.btn_fav.clicked.connect(self._on_fav_click)

        self.btn_tag = QPushButton("🏷️ 标签")
        self.btn_tag.clicked.connect(self._on_tag_click)

        self.btn_open = QPushButton("🔗 原文")
        self.btn_open.clicked.connect(self._on_open_url)

        self.lbl_tags = QLabel("")
        self.lbl_tags.setStyleSheet("font-size:11px; color:#00695C;")

        btn_layout.addWidget(self.btn_fav)
        btn_layout.addWidget(self.btn_tag)
        btn_layout.addWidget(self.btn_open)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.lbl_tags)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        self.txt_content = QPlainTextEdit()
        self.txt_content.setReadOnly(True)
        layout.addWidget(self.txt_content, 1)

    def load_article(self, article_id):
        self.current_id = article_id
        db = DatabaseManager(self.db_path)
        art = db.get_article_detail(article_id)
        db.close()

        if not art:
            return
        self.lbl_title.setText(art["title"])
        self.lbl_subtitle.setText(art.get("subtitle", ""))
        self.lbl_author.setText(f"✍️ {art.get('author', '未知')}")
        self.lbl_date.setText(f"📅 {art.get('pub_date', '')}")
        self.lbl_section.setText(art.get("section", ""))
        self.txt_content.setPlainText(art.get("content", ""))

        is_fav = art.get("is_fav", False)
        self.btn_fav.setChecked(is_fav)
        self.btn_fav.setText("★ 已收藏" if is_fav else "☆ 收藏")

        tags = art.get("tags", [])
        self.lbl_tags.setText(
            "🏷️ " + " ".join(f"[{n}]" for _, n in tags) if tags else ""
        )

    def _on_fav_click(self):
        if self.current_id is None:
            return
        db = DatabaseManager(self.db_path)
        added = db.toggle_favorite(self.current_id)
        db.close()
        self.btn_fav.setText("★ 已收藏" if added else "☆ 收藏")
        self.fav_changed.emit()

    def _on_tag_click(self):
        if self.current_id is None:
            return
        name, ok = QInputDialog.getText(self, "添加标签", "标签名称:")
        if ok and name.strip():
            db = DatabaseManager(self.db_path)
            db.tag_article(self.current_id, name.strip())
            db.close()
            self.load_article(self.current_id)

    def _on_open_url(self):
        if self.current_id is None:
            return
        db = DatabaseManager(self.db_path)
        art = db.get_article_detail(self.current_id)
        db.close()
        if art and art.get("url"):
            webbrowser.open(art["url"])