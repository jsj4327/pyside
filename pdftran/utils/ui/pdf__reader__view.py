from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QTextEdit
from PySide2.QtCore import Qt
from core.pdf\u005f\u005fdocument import PdfDocument
from utils.\u005f\u005fimage\u005f\u005fconvert import ImageConvert

class PdfReaderView(QWidget):
    def \u005f\u005finit\u005f\u005f(self, parent=None):
        super().\u005f\u005finit\u005f\u005f(parent)
        self.layout = QVBoxLayout(self)
        self.scroll\u005farea = QScrollArea()
        self.image\u005flabel = QLabel()
        self.image\u005flabel.setAlignment(Qt.AlignCenter)
        self.scroll\u005farea.setWidget(self.image\u005flabel)
        self.scroll\u005farea.setWidgetResizable(True)
        self.layout.addWidget(self.scroll\u005farea)
        self.pdf\u005fdoc = None

    def set\u005fdocument(self, pdf\u005fdoc: PdfDocument):
        self.pdf\u005fdoc = pdf\u005fdoc

    def show\u005fpage(self, page\u005findex: int):
        if self.pdf\u005fdoc is None:
            return
        page = self.pdf\u005fdoc.get\u005fpage(page\u005findex)
        if page is None:
            return
        pix = ImageConvert.page\u005fto\u005fpixmap(page, zoom=1.5)
        self.image\u005flabel.setPixmap(pix)