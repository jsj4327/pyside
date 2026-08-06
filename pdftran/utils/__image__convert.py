import fitz
from PySide2.QtGui import QPixmap, QImage
from PySide2.QtCore import QByteArray

class ImageConvert:
    @staticmethod
    def page_to_pixmap(page: fitz.Page, zoom: float = 1.0) -> QPixmap:
        if page is None:
            return QPixmap()
        try:
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            data = QByteArray(pix.samples)
            qimg = QImage(data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception as e:
            print(f"Error rendering page: {e}")
            return QPixmap()