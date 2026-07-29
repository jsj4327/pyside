from PySide2.QtCore import QObject, Signal


class DrawingController(QObject):
    view_updated = Signal()

    def init(self, model):
        super().init()
        self.model = model

    def get_model(self):
        return self.model

    def set_tool(self, tool_name):
        self.model.set_tool(tool_name)

    def set_color(self, color):
        self.model.set_color(color)

    def get_color(self):
        return self.model.color

    def set_width(self, width):
        self.model.set_width(width)

    def start_shape(self, start_point):
        self.model.current_shape = self.model.create_shape(start_point, start_point)

    def update_shape(self, end_point, is_freehand=False):
        if self.model.current_shape:
            if is_freehand:
                self.model.current_shape.add_point(end_point)
            else:
                start = self.model.current_shape.start
                self.model.current_shape = self.model.create_shape(start, end_point)
            self.view_updated.emit()

    def commit_shape(self):
        if self.model.current_shape:
            if hasattr(self.model.current_shape, 'points') and len(self.model.current_shape.points) < 2:
                self.model.current_shape = None
                return
            self.model.add_shape(self.model.current_shape)
            self.model.current_shape = None
            self.view_updated.emit()

    def undo(self):
        if self.model.undo():
            self.view_updated.emit()

    def redo(self):
        if self.model.redo():
            self.view_updated.emit()

    def clear_all(self):
        self.model.clear_all()
        self.view_updated.emit()
