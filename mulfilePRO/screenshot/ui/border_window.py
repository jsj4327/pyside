# -*- coding: utf-8 -*-
# 文件: border_window.py

from PySide2.QtCore import Qt
from PySide2.QtGui import QPainter, QPen, QColor
from PySide2.QtWidgets import QWidget

class PersistentBorderWindow(QWidget):
    """极其轻量的常驻边框窗口：只在选区四周画绿线，完美穿透鼠标滚动"""
    def __init__(self, rect):
        super().__init__()
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  
        
        self.setGeometry(rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(0, 200, 100), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        draw_rect = self.rect().adjusted(0, 0, -1, -1)
        painter.drawRect(draw_rect)