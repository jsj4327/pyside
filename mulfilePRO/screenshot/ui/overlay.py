from PySide2.QtCore import Qt, QRect, QPoint
from PySide2.QtGui import QPainter, QPen, QColor, QGuiApplication
from PySide2.QtWidgets import QWidget

class ScreenshotOverlay(QWidget):
    """矩形选区划定遮罩层（用于第一步划定截取区域）"""
    def __init__(self, mode="rect", enable_border=False, border_width=2, enable_shadow=True, callback=None):
        super().__init__()
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        screen = QGuiApplication.primaryScreen()
        self.pixmap = screen.grabWindow(0)
        self.resize(self.pixmap.size())
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False

        self.mode = mode
        self.callback = callback
        self.parent_panel = None

        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if not self.start_point.isNull() and not self.end_point.isNull():
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawPixmap(rect, self.pixmap, rect)
            
            border_color = QColor(0, 120, 215) if self.mode == "rect" else QColor(0, 200, 100)
            pen = QPen(border_color, 1 if self.mode == "rect" else 2, Qt.DashLine if self.mode == "rect" else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            rect = QRect(self.start_point, self.end_point).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.close()
                if self.callback:
                    self.callback(rect, self.pixmap)
            else:
                self.close()
                if self.parent_panel:
                    self.parent_panel.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            if self.parent_panel:
                self.parent_panel.show()