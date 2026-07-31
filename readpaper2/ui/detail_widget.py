# ui/detail_widget.py
"""
文章详情展示组件：支持 QSS 定制、字体放大缩小、标签管理与高亮渲染。
"""
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextBrowser, QPushButton, QInputDialog, QMessageBox, QFileDialog, QMenu)
from PySide2.QtCore import Signal, Qt
from db.repositories import ArticleRepository
from services.exporter import export_single_txt

class ArticleDetailWidget(QWidget):
    article_updated = Signal()

    def __init__(self, repository: ArticleRepository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.current_article = None
        self.font_size = 14
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.title_label = QLabel("请在左侧列表中选择一篇文章查看详情")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2d3d;")
        self.title_label.setWordWrap(True)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #8492a6; font-size: 12px; margin-bottom: 5px;")

        btn_layout = QHBoxLayout()
        self.fav_btn = QPushButton("☆ 收藏文章")
        self.fav_btn.setObjectName("favBtn")
        self.fav_btn.setCheckable(True)
        self.fav_btn.clicked.connect(self._toggle_fav)

        self.add_tag_btn = QPushButton("+ 添加标签")
        self.add_tag_btn.clicked.connect(self._add_tag)

        self.zoom_in_btn = QPushButton("A+")
        self.zoom_in_btn.setFixedWidth(40)
        self.zoom_in_btn.clicked.connect(self._zoom_in)

        self.zoom_out_btn = QPushButton("A-")
        self.zoom_out_btn.setFixedWidth(40)
        self.zoom_out_btn.clicked.connect(self._zoom_out)

        self.export_btn = QPushButton("导出单篇")
        self.export_btn.clicked.connect(self._export_article)

        btn_layout.addWidget(self.fav_btn)
        btn_layout.addWidget(self.add_tag_btn)
        btn_layout.addWidget(self.zoom_in_btn)
        btn_layout.addWidget(self.zoom_out_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()

        self.tags_label = QLabel("标签: 无")
        self.tags_label.setStyleSheet("color: #409eff; font-weight: bold;")

        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        layout.addLayout(btn_layout)
        layout.addWidget(self.tags_label)
        layout.addWidget(self.content_browser)

    def set_article(self, article: dict):
        self.current_article = article
        if not article:
            self.title_label.setText("请选择一篇文章查看详情")
            self.meta_label.setText("")
            self.content_browser.clear()
            self.tags_label.setText("标签: 无")
            return

        self.title_label.setText(article.get("title", ""))
        sub = article.get("subtitle")
        meta = f"📅 日期: {article.get('date', '')} | 📰 版面: {article.get('page_num', '')} {article.get('page_name', '')} | ✍️ 作者: {article.get('author') or '未知'} | 📝 字数: {article.get('word_count', 0)} 字"
        if sub:
            meta = f"📌 副标题: {sub}\n" + meta
        self.meta_label.setText(meta)

        # 渲染 HTML 版面正文
        raw_content = article.get("content", "").replace("\n", "<br><br>")
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Microsoft YaHei', sans-serif; font-size: {self.font_size}px; line-height: 1.8; color: #2c3e50; }}
            </style>
        </head>
        <body>
            {raw_content}
        </body>
        </html>
        """
        self.content_browser.setHtml(html_body)

        is_fav = self.repo.is_favorite(article["id"])
        self.fav_btn.setChecked(is_fav)
        self.fav_btn.setText("★ 已收藏" if is_fav else "☆ 收藏文章")

        self._refresh_tags()

    def _refresh_tags(self):
        if not self.current_article:
            return
        tags = self.repo.get_tags_for_article(self.current_article["id"])
        if tags:
            tag_names = [t["name"] for t in tags]
            self.tags_label.setText("🏷️ 标签: " + ", ".join(tag_names))
        else:
            self.tags_label.setText("🏷️ 标签: 无")

    def _toggle_fav(self):
        if not self.current_article:
            return
        is_fav = self.repo.toggle_favorite(self.current_article["id"])
        self.fav_btn.setChecked(is_fav)
        self.fav_btn.setText("★ 已收藏" if is_fav else "☆ 收藏文章")
        self.article_updated.emit()

    def _add_tag(self):
        if not self.current_article:
            return
        tag_name, ok = QInputDialog.getText(self, "添加标签", "请输入自定义标签名称:")
        if ok and tag_name:
            self.repo.add_tag_to_article(self.current_article["id"], tag_name)
            self._refresh_tags()
            self.article_updated.emit()

    def _zoom_in(self):
        if self.font_size < 28:
            self.font_size += 2
            if self.current_article:
                self.set_article(self.current_article)

    def _zoom_out(self):
        if self.font_size > 10:
            self.font_size -= 2
            if self.current_article:
                self.set_article(self.current_article)

    def _export_article(self):
        if not self.current_article:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出单篇文章", f"{self.current_article.get('title', 'article')}.txt", "Text Files (*.txt)")
        if file_path:
            export_single_txt(self.current_article, file_path)
            QMessageBox.information(self, "提示", "单篇文章导出成功！")