from PySide2.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QScrollArea
from PySide2.QtCore import Qt
from core.pdf__document import PdfDocument

class PdfReaderView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)
        
        self.pdf_doc = None
        self.page_browsers = []

    def set_document(self, pdf_doc: PdfDocument):
        self.pdf_doc = pdf_doc
        self.reload_document()

    def reload_document(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.page_browsers.clear()

        if self.pdf_doc is None or self.pdf_doc.page_count == 0:
            return

        for idx in range(self.pdf_doc.page_count):
            page = self.pdf_doc.get_page(idx)
            browser = QTextBrowser()
            browser.setReadOnly(True)
            browser.setOpenExternalLinks(False)
            if page:
                # 使用 xhtml 格式以精确保留 PDF 原文的排版、位置与样式，解决格式错乱问题
                xhtml_text = page.get_text("xhtml")
                browser.setHtml(xhtml_text)
            
            browser.setMinimumSize(600, 800)
            self.content_layout.addWidget(browser)
            self.page_browsers.append(browser)

    def show_page(self, page_index: int):
        if self.pdf_doc is None or not self.page_browsers:
            return
        if 0 <= page_index < len(self.page_browsers):
            target_browser = self.page_browsers[page_index]
            self.scroll_area.ensureWidgetVisible(target_browser)