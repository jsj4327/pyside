from .shape import Line, Rect, Circle, Ellipse, Freehand
from PySide2.QtGui import QColor


class DrawingModel:
    def init(self):
        super().init()
        self.shapes = []
        self.undo_stack = []
        self.redo_stack = []
        self.current_shape = None
        self.tool = 'line'
        self.color = QColor(0, 0, 0)
        self.width = 2

    def add_shape(self, shape):
        self.shapes.append(shape)
        self.undo_stack.append(('add', shape))
        self.redo_stack.clear()

    def remove_shape(self, shape):
        if shape in self.shapes:
            self.shapes.remove(shape)
            self.undo_stack.append(('remove', shape))
            self.redo_stack.clear()

    def clear_all(self):
        if self.shapes:
            self.undo_stack.append(('clear', self.shapes.copy()))
            self.shapes.clear()
            self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return False
        action, data = self.undo_stack.pop()
        if action == 'add':
            self.shapes.remove(data)
            self.redo_stack.append(('add_undo', data))
        elif action == 'remove':
            self.shapes.append(data)
            self.redo_stack.append(('remove_undo', data))
        elif action == 'clear':
            self.shapes = data
            self.redo_stack.append(('clear_undo', data))
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        action, data = self.redo_stack.pop()
        if action == 'add_undo':
            self.shapes.append(data)
            self.undo_stack.append(('add', data))
        elif action == 'remove_undo':
            self.shapes.remove(data)
            self.undo_stack.append(('remove', data))
        elif action == 'clear_undo':
            self.clear_all()
        return True

    def set_tool(self, tool):
        self.tool = tool

    def set_color(self, color):
        self.color = color

    def set_width(self, width):
        self.width = width

    def create_shape(self, start, end):
        if self.tool == 'line':
            return Line(start, end, self.color, self.width)
        elif self.tool == 'rect':
            return Rect(start, end, self.color, self.width)
        elif self.tool == 'circle':
            return Circle(start, end, self.color, self.width)
        elif self.tool == 'ellipse':
            return Ellipse(start, end, self.color, self.width)
        elif self.tool == 'freehand':
            return Freehand(start, self.color, self.width)
        return None

    def get_shapes(self):
        return self.shapes
