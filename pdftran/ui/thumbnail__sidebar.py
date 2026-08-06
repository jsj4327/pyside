from PySide2.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QListWidget,
                               QListWidgetItem, QAbstractItemView)
from PySide2.QtCore import Signal, QSize, Qt
from core.pdf__document import PdfDocument
from utils.__image__convert import ImageConvert

class SidebarListWidget(QListWidget):
    resized = Signal(QSize)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit(event.size())

class ThumbnailSidebar(QWidget):
    page_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = SidebarListWidget()
        self.list_widget.setSpacing(10)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self.__on__item__click)
        self.list_widget.resized.connect(self.__on__list_resized)
        
        self.layout.addWidget(self.list_widget)
        self.setLayout(self.layout)
        
        self.pdf_doc = None
        self._last_width = 0

    def __on__list_resized(self, size):
        if self.pdf_doc is None or self.pdf_doc.page_count == 0:
            return
            
        available_width = size.width() - 20
        if available_width < 50:
            available_width = 150
            
        if abs(available_width - self._last_width) < 20:
            return
        self._last_width = available_width
        
        icon_height = int(available_width * 1.414)
        self.list_widget.setIconSize(QSize(available_width, icon_height))
        self.load_thumbnails(self.pdf_doc)

    def load_thumbnails(self, pdf_doc: PdfDocument):
        self.pdf_doc = pdf_doc
        self.list_widget.clear()
        
        if pdf_doc.page_count == 0:
            return
            
        available_width = self.list_widget.viewport().width() - 20
        if available_width < 50:
            available_width = 150
        
        for idx in range(pdf_doc.page_count):
            page = pdf_doc.get_page(idx)
            if page:
                page_rect = page.rect
                zoom = available_width / page_rect.width if page_rect.width > 0 else 1.0
                pix = ImageConvert.page_to_pixmap(page, zoom=zoom)
            else:
                pix = None
                
            item = QListWidgetItem(f"Page {idx+1}")
            if pix:
                item.setIcon(pix)
            item.setData(Qt.UserRole, idx)
            item.setTextAlignment(Qt.AlignCenter)
            self.list_widget.addItem(item)

    def __on__item__click(self, item):
        page_idx = item.data(Qt.UserRole)
        if page_idx is not None:
            self.page_selected.emit(page_idx)