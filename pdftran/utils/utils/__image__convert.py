import fitz
from PySide2.QtGui import QPixmap, QImage
from PySide2.QtCore import QByteArray

class ImageConvert:
    @staticmethod
    def page\u005fto\u005fpixmap(page: fitz.Page, zoom: float = 1.0) -> QPixmap:
        if page is None:
            return QPixmap()
        try:
            mat = fitz.Matrix(zoom, zoom)
            # alpha\u005fFalse 确保生成纯 RGB 数据
            pix = page.get\u005fpixmap(matrix=mat, alpha=False)
            
            # 使用 QByteArray 包装原始数据，确保内存安全
            data = QByteArray(pix.samples)
            qimg = QImage(data, pix.width, pix.height, pix.stride, QImage.Format\u005fRGB888)
            
            # 必须 copy()，防止局部变量 data 被回收导致图像变白
            return QPixmap.fromImage(qimg.copy())
        except Exception as e:
            print(f"Error rendering page: {e}")
            return QPixmap()