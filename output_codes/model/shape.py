from PySide2.QtCore import QPoint, QRect
from PySide2.QtGui import QColor, QPen, QBrush


class Shape:
    def init(self, start_point, end_point=None, color=QColor(0, 0, 0), width=2):
        self.start = start_point
        self.end = end_point if end_point else start_point
        self.color = color
        self.width = width
        self.selected = False

    def rect(self):
        return QRect(self.start, self.end).normalized()

    def draw(self, painter):
        painter.setPen(QPen(self.color, self.width))
        painter.setBrush(QBrush())


class Line(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawLine(self.start, self.end)


class Rect(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawRect(self.rect())


class Circle(Shape):
    def draw(self, painter):
        super().draw(painter)
        center = self.start
        radius = int(((self.end.x() - self.start.x()) ** 2 + (self.end.y() - self.start.y()) ** 2) ** 0.5)
        painter.drawEllipse(center, radius, radius)


class Ellipse(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawEllipse(self.rect())


class Freehand(Shape):
    def init(self, start_point, color=QColor(0, 0, 0), width=2):
        super().init(start_point, start_point, color, width)
        self.points = [start_point]

    def add_point(self, point):
        self.points.append(point)
        self.end = point

    def draw(self, painter):
        super().draw(painter)
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                painter.drawLine(self.points[i], self.points[i + 1])
