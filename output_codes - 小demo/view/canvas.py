from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt
from PySide2.QtGui import QPainter


class CanvasWidget(QWidget):
    def init(self, controller, parent=None):
        super().init(parent)
        self.controller = controller
        self.setMinimumSize(400, 400)
        self.setStyleSheet('background-color: white;')
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.current_tool = 'line'

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.current_tool = self.controller.get_model().tool
            self.controller.start_shape(self.start_point)

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            if self.current_tool == 'freehand':
                self.controller.update_shape(self.end_point, is_freehand=True)
            else:
                self.controller.update_shape(self.end_point)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_point = event.pos()
            self.controller.commit_shape()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        model = self.controller.get_model()
        for shape in model.get_shapes():
            shape.draw(painter)
        current = model.current_shape
        if current:
            current.draw(painter)
