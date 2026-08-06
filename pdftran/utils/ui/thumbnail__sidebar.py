from PySide2.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QListWidget,
                               QListWidgetItem, QAbstractItemView)
from PySide2.QtCore import Signal, QSize, Qt
from core.pdf\u005f\u005fdocument import PdfDocument
from utils.\u005f\u005fimage\u005f\u005fconvert import ImageConvert

class ThumbnailSidebar(QWidget):
    page\u005fselected = Signal(int)
    
    def \u005f\u005finit\u005f\u005f(self, parent=None):
        super().\u005f\u005finit\u005f\u005f(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.list\u005fwidget = QListWidget()
        self.list\u005fwidget.setSpacing(10)
        self.list\u005fwidget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list\u005fwidget.itemClicked.connect(self.\u005f\u005fon\u005f\u005fitem\u005f\u005fclick)
        
        self.layout.addWidget(self.list\u005fwidget)
        self.setLayout(self.layout)
        
        self.pdf\u005fdoc = None
        
        # 监听容器大小变化，动态调整缩略图宽度
        self.list\u005fwidget.resizeEvent = self.\u005f\u005fon\u005f\u005fresize

    def \u005f\u005fon\u005f\u005fresize(self, event):
        """当侧边栏宽度改变时，重新计算并调整缩略图尺寸"""
        # 调用原始的 resizeEvent
        super(QListWidget, self.list\u005fwidget).resizeEvent(event)
        
        if self.pdf\u005fdoc is None or self.pdf\u005fdoc.page\u005fcount == 0:
            return
            
        # 获取当前可用宽度，减去边框和边距
        available\u005fwidth = self.list\u005fwidget.viewport().width() - 20
        if available\u005fwidth < 50:
            available\u005fwidth = 150
            
        # 按照 A4 纸张比例 (1:1.414) 计算高度
        icon\u005fheight = int(available\u005fwidth * 1.414)
        
        # 更新图标大小
        self.list\u005fwidget.setIconSize(QSize(available\u005fwidth, icon\u005fheight))
        
        # 重新加载缩略图以适配新尺寸
        self.load\u005fthumbnails(self.pdf\u005fdoc)

    def load\u005fthumbnails(self, pdf\u005fdoc: PdfDocument):
        self.pdf\u005fdoc = pdf\u005fdoc
        self.list\u005fwidget.clear()
        
        if pdf\u005fdoc.page\u005fcount == 0:
            return
            
        # 获取当前可用宽度
        available\u005fwidth = self.list\u005fwidget.viewport().width() - 20
        if available\u005fwidth < 50:
            available\u005fwidth = 150
        
        for idx in range(pdf\u005fdoc.page\u005fcount):
            page = pdf\u005fdoc.get\u005fpage(idx)
            
            # 核心修复：根据容器宽度动态计算缩放比例 (zoom)
            # 确保缩略图是整页内容的等比例缩小，而不是单个字符
            if page:
                page\u005frect = page.rect
                # 目标宽度 / 页面实际宽度 = 缩放比例
                zoom = available\u005fwidth / page\u005frect.width
                pix = ImageConvert.page\u005fto\u005fpixmap(page, zoom=zoom)
            else:
                pix = None
                
            item = QListWidgetItem(f"Page {idx+1}")
            if pix:
                item.setIcon(pix)
            item.setData(Qt.UserRole, idx)
            item.setTextAlignment(Qt.AlignCenter)
            self.list\u005fwidget.addItem(item)

    def \u005f\u005fon\u005f\u005fitem\u005f\u005fclick(self, item):
        page\u005fidx = item.data(Qt.UserRole)
        if page\u005fidx is not None:
            self.page\u005fselected.emit(page\u005fidx)