import sys
import os
from PySide2.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QObject, Signal
from PySide2.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath, QPixmap, QIcon
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar, QFrame, QToolButton,
    QColorDialog, QSpinBox
)

# ==========================================
# PATH & HELPER FUNCTIONS
# ==========================================
def get_icon_pixmap():
    """获取 projectbuilder.png 路径与 QPixmap，若不存在则自动生成默认图标降级"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(script_dir, 'projectbuilder.png')

    if os.path.exists(target_path):
        pix = QPixmap(target_path)
        if not pix.isNull():
            return pix, target_path

    # 当前工作目录备选查找
    if os.path.exists('projectbuilder.png'):
        pix = QPixmap('projectbuilder.png')
        if not pix.isNull():
            return pix, 'projectbuilder.png'

    # 若没有找到文件，生成一个漂亮的默认矢量图标，防止界面报错
    fallback_pix = QPixmap(64, 64)
    fallback_pix.fill(Qt.transparent)
    painter = QPainter(fallback_pix)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # 画背景小圆角矩形
    painter.setBrush(QBrush(QColor(0, 120, 215)))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 10, 10)

    # 画房子/建筑图标形状
    painter.setPen(QPen(Qt.white, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawRect(20, 26, 24, 22)
    path = QPainterPath()
    path.moveTo(16, 26)
    path.lineTo(32, 14)
    path.lineTo(48, 26)
    painter.drawPath(path)
    painter.end()

    return fallback_pix, target_path


# ==========================================
# MODEL: Shapes
# ==========================================
class Shape:
    def __init__(self, start_point, end_point=None, color=QColor(0, 0, 0), width=2):
        self.start = QPoint(start_point)
        self.end = QPoint(end_point) if end_point else QPoint(start_point)
        self.color = color
        self.width = width
        self.selected = False

    def rect(self):
        return QRect(self.start, self.end).normalized()

    def contains(self, point):
        return self.rect().adjusted(-4, -4, 4, 4).contains(point)

    def move_by(self, delta):
        self.start += delta
        self.end += delta

    def get_handles(self):
        r = self.rect()
        return {
            'tl': r.topLeft(),
            'tr': r.topRight(),
            'bl': r.bottomLeft(),
            'br': r.bottomRight()
        }

    def get_handle_at(self, point, threshold=8):
        for name, h_pos in self.get_handles().items():
            if (QPointF(h_pos) - QPointF(point)).manhattanLength() <= threshold:
                return name
        return None

    def resize_handle(self, handle_name, new_pos):
        r = QRect(self.start, self.end)
        if handle_name == 'tl':
            r.setTopLeft(new_pos)
        elif handle_name == 'tr':
            r.setTopRight(new_pos)
        elif handle_name == 'bl':
            r.setBottomLeft(new_pos)
        elif handle_name == 'br':
            r.setBottomRight(new_pos)
        self.start = r.topLeft()
        self.end = r.bottomRight()

    def draw(self, painter):
        painter.setPen(QPen(self.color, self.width))
        painter.setBrush(QBrush())

    def draw_selection(self, painter):
        if not self.selected:
            return
        painter.save()
        r = self.rect()
        painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(r)

        # 绘制4个角落的缩放手柄
        handle_size = 8
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 120, 215), 1.5))
        for h in self.get_handles().values():
            painter.drawRect(QRectF(h.x() - handle_size / 2, h.y() - handle_size / 2, handle_size, handle_size))
        painter.restore()


class Line(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawLine(self.start, self.end)
        self.draw_selection(painter)


class Rect(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawRect(self.rect())
        self.draw_selection(painter)


class Circle(Shape):
    def draw(self, painter):
        super().draw(painter)
        center = self.start
        radius = int(((self.end.x() - self.start.x()) ** 2 + (self.end.y() - self.start.y()) ** 2) ** 0.5)
        painter.drawEllipse(center, radius, radius)
        self.draw_selection(painter)


class Ellipse(Shape):
    def draw(self, painter):
        super().draw(painter)
        painter.drawEllipse(self.rect())
        self.draw_selection(painter)


class Freehand(Shape):
    def __init__(self, start_point, color=QColor(0, 0, 0), width=2):
        super().__init__(start_point, start_point, color, width)
        self.points = [start_point]

    def add_point(self, point):
        self.points.append(point)
        self.end = point

    def move_by(self, delta):
        super().move_by(delta)
        self.points = [p + delta for p in self.points]

    def rect(self):
        if not self.points:
            return super().rect()
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        return QRect(QPoint(min(xs), min(ys)), QPoint(max(xs), max(ys)))

    def draw(self, painter):
        super().draw(painter)
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                painter.drawLine(self.points[i], self.points[i + 1])
        self.draw_selection(painter)


class Pen(Shape):
    """钢笔工具（贝塞尔曲线）"""
    def __init__(self, start_point, color=QColor(0, 0, 0), width=2):
        super().__init__(start_point, start_point, color, width)
        p = QPointF(start_point)
        self.nodes = [{
            'anchor': QPointF(p),
            'handle_in': QPointF(p),
            'handle_out': QPointF(p)
        }]
        self.preview_point = QPointF(p)
        self.finished = False

    def add_node(self, point):
        p = QPointF(point)
        self.nodes.append({
            'anchor': QPointF(p),
            'handle_in': QPointF(p),
            'handle_out': QPointF(p)
        })
        self.preview_point = QPointF(p)

    def update_last_handle(self, handle_pos):
        if not self.nodes:
            return
        hp = QPointF(handle_pos)
        last = self.nodes[-1]
        last['handle_out'] = hp
        anchor = last['anchor']
        diff = hp - anchor
        last['handle_in'] = anchor - diff

    def update_preview(self, preview_pos):
        self.preview_point = QPointF(preview_pos)

    def move_by(self, delta):
        super().move_by(delta)
        d = QPointF(delta)
        for node in self.nodes:
            node['anchor'] += d
            node['handle_in'] += d
            node['handle_out'] += d

    def rect(self):
        if not self.nodes:
            return super().rect()
        xs = [n['anchor'].x() for n in self.nodes]
        ys = [n['anchor'].y() for n in self.nodes]
        return QRect(QPoint(int(min(xs)), int(min(ys))), QPoint(int(max(xs)), int(max(ys))))

    def draw(self, painter):
        if not self.nodes:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)

        path = QPainterPath()
        path.moveTo(self.nodes[0]['anchor'])

        for i in range(1, len(self.nodes)):
            prev = self.nodes[i - 1]
            curr = self.nodes[i]
            path.cubicTo(prev['handle_out'], curr['handle_in'], curr['anchor'])

        if not self.finished and len(self.nodes) > 0:
            prev = self.nodes[-1]
            path.cubicTo(prev['handle_out'], self.preview_point, self.preview_point)

        painter.drawPath(path)

        if not self.finished:
            painter.setPen(QPen(QColor(100, 150, 255), 1, Qt.DashLine))
            for node in self.nodes:
                anc = node['anchor']
                hin = node['handle_in']
                hout = node['handle_out']
                if anc != hin:
                    painter.drawLine(anc, hin)
                    painter.setBrush(QBrush(QColor(100, 150, 255)))
                    painter.drawEllipse(hin, 3, 3)
                if anc != hout:
                    painter.drawLine(anc, hout)
                    painter.setBrush(QBrush(QColor(100, 150, 255)))
                    painter.drawEllipse(hout, 3, 3)
                painter.setBrush(QBrush(Qt.white))
                painter.setPen(QPen(QColor(50, 50, 200), 1.5))
                painter.drawRect(QRectF(anc.x() - 3, anc.y() - 3, 6, 6))

        painter.restore()
        self.draw_selection(painter)


class ImageShape(Shape):
    """同目录 projectbuilder.png 图标对象"""
    def __init__(self, start_point, end_point=None, color=QColor(0, 0, 0), width=2):
        super().__init__(start_point, end_point, color, width)
        self.pixmap, self.icon_path = get_icon_pixmap()

    def draw(self, painter):
        r = self.rect()
        if not self.pixmap.isNull():
            painter.drawPixmap(r, self.pixmap)
        self.draw_selection(painter)


# ==========================================
# MODEL: Drawing Model
# ==========================================
class DrawingModel:
    def __init__(self):
        self.shapes = []
        self.undo_stack = []
        self.redo_stack = []
        self.current_shape = None
        self.selected_shape = None
        self.tool = 'select'
        self.color = QColor(0, 0, 0)
        self.width = 2

    def add_shape(self, shape):
        self.shapes.append(shape)
        self.undo_stack.append(('add', shape))
        self.redo_stack.clear()

    def remove_shape(self, shape):
        if shape in self.shapes:
            if self.selected_shape == shape:
                self.selected_shape = None
            self.shapes.remove(shape)
            self.undo_stack.append(('remove', shape))
            self.redo_stack.clear()

    def delete_selected(self):
        if self.selected_shape:
            target = self.selected_shape
            self.remove_shape(target)
            return True
        return False

    def select_shape(self, shape):
        self.deselect_all()
        if shape in self.shapes:
            shape.selected = True
            self.selected_shape = shape

    def deselect_all(self):
        for s in self.shapes:
            s.selected = False
        self.selected_shape = None

    def clear_all(self):
        if self.shapes:
            self.undo_stack.append(('clear', self.shapes.copy()))
            self.shapes.clear()
            self.selected_shape = None
            self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return False
        action, data = self.undo_stack.pop()
        if action == 'add':
            if data in self.shapes:
                self.shapes.remove(data)
            self.redo_stack.append(('add_undo', data))
        elif action == 'remove':
            self.shapes.append(data)
            self.redo_stack.append(('remove_undo', data))
        elif action == 'clear':
            self.shapes = data
            self.redo_stack.append(('clear_undo', data))
        self.deselect_all()
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        action, data = self.redo_stack.pop()
        if action == 'add_undo':
            self.shapes.append(data)
            self.undo_stack.append(('add', data))
        elif action == 'remove_undo':
            if data in self.shapes:
                self.shapes.remove(data)
            self.undo_stack.append(('remove', data))
        elif action == 'clear_undo':
            self.clear_all()
        self.deselect_all()
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
        elif self.tool == 'pen':
            return Pen(start, self.color, self.width)
        elif self.tool == 'image':
            return ImageShape(start, end, self.color, self.width)
        return None

    def get_shapes(self):
        return self.shapes


# ==========================================
# CONTROLLER: Drawing Controller
# ==========================================
class DrawingController(QObject):
    view_updated = Signal()

    def __init__(self, model):
        super().__init__()
        self.model = model

    def get_model(self):
        return self.model

    def set_tool(self, tool_name):
        if self.is_pen_active():
            self.finish_pen()
        self.model.set_tool(tool_name)
        if tool_name != 'select':
            self.model.deselect_all()
        self.view_updated.emit()

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
        shape = self.model.current_shape
        if shape:
            if hasattr(shape, 'points') and len(shape.points) < 2:
                self.model.current_shape = None
                return

            # 如果点击直接创建图标而未拉出尺寸，设为默认像素大小
            if isinstance(shape, ImageShape):
                r = shape.rect()
                if r.width() < 5 or r.height() < 5:
                    w = shape.pixmap.width() if not shape.pixmap.isNull() else 64
                    h = shape.pixmap.height() if not shape.pixmap.isNull() else 64
                    shape.end = QPoint(shape.start.x() + w, shape.start.y() + h)

            self.model.add_shape(shape)
            self.model.current_shape = None
            self.model.select_shape(shape)
            self.view_updated.emit()

    def hit_test(self, point):
        for shape in reversed(self.model.get_shapes()):
            if shape.contains(point):
                return shape
        return None

    def select_shape(self, shape):
        self.model.select_shape(shape)
        self.view_updated.emit()

    def deselect_all(self):
        self.model.deselect_all()
        self.view_updated.emit()

    def delete_selected(self):
        if self.model.delete_selected():
            self.view_updated.emit()

    # ---------------- 钢笔工具逻辑 ----------------
    def is_pen_active(self):
        current = self.model.current_shape
        return isinstance(current, Pen) and not current.finished

    def start_pen(self, point):
        pen_shape = Pen(point, self.model.color, self.model.width)
        self.model.current_shape = pen_shape
        self.view_updated.emit()

    def add_pen_node(self, point):
        if self.is_pen_active():
            self.model.current_shape.add_node(point)
            self.view_updated.emit()

    def update_pen_handle(self, point):
        if self.is_pen_active():
            self.model.current_shape.update_last_handle(point)
            self.view_updated.emit()

    def update_pen_preview(self, point):
        if self.is_pen_active():
            self.model.current_shape.update_preview(point)
            self.view_updated.emit()

    def finish_pen(self):
        if self.is_pen_active():
            pen_shape = self.model.current_shape
            pen_shape.finished = True
            if len(pen_shape.nodes) < 2 and pen_shape.nodes[0]['anchor'] == pen_shape.nodes[0]['handle_out']:
                self.model.current_shape = None
            else:
                self.model.add_shape(pen_shape)
                self.model.select_shape(pen_shape)
                self.model.current_shape = None
            self.view_updated.emit()

    # ---------------- 撤销重做 ----------------
    def undo(self):
        if self.is_pen_active():
            self.finish_pen()
        if self.model.undo():
            self.view_updated.emit()

    def redo(self):
        if self.is_pen_active():
            self.finish_pen()
        if self.model.redo():
            self.view_updated.emit()

    def clear_all(self):
        if self.is_pen_active():
            self.finish_pen()
        self.model.clear_all()
        self.view_updated.emit()


# ==========================================
# VIEW: Canvas Widget
# ==========================================
class CanvasWidget(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMinimumSize(400, 400)
        self.setStyleSheet('background-color: white;')
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.interaction_state = 'none'
        self.active_handle = None
        self.last_mouse_pos = QPoint()
        self.start_point = QPoint()
        self.dragging_pen_handle = False

    def mousePressEvent(self, event):
        self.setFocus()
        tool = self.controller.get_model().tool
        pos = event.pos()

        if tool == 'select':
            if event.button() == Qt.LeftButton:
                selected = self.controller.get_model().selected_shape
                if selected:
                    handle = selected.get_handle_at(pos)
                    if handle:
                        self.interaction_state = 'resizing'
                        self.active_handle = handle
                        self.last_mouse_pos = pos
                        return

                shape = self.controller.hit_test(pos)
                if shape:
                    self.controller.select_shape(shape)
                    self.interaction_state = 'moving'
                    self.last_mouse_pos = pos
                else:
                    self.controller.deselect_all()
                    self.interaction_state = 'none'
            return

        if tool == 'pen':
            if event.button() == Qt.LeftButton:
                if not self.controller.is_pen_active():
                    self.controller.start_pen(pos)
                else:
                    self.controller.add_pen_node(pos)
                self.dragging_pen_handle = True
                self.update()
            elif event.button() == Qt.RightButton:
                self.controller.finish_pen()
                self.dragging_pen_handle = False
                self.update()
            return

        if event.button() == Qt.LeftButton:
            self.controller.deselect_all()
            self.interaction_state = 'creating'
            self.start_point = pos
            self.controller.start_shape(self.start_point)

    def mouseMoveEvent(self, event):
        tool = self.controller.get_model().tool
        pos = event.pos()

        if self.interaction_state == 'resizing':
            selected = self.controller.get_model().selected_shape
            if selected and self.active_handle:
                selected.resize_handle(self.active_handle, pos)
                self.controller.view_updated.emit()
            return

        if self.interaction_state == 'moving':
            selected = self.controller.get_model().selected_shape
            if selected:
                delta = pos - self.last_mouse_pos
                selected.move_by(delta)
                self.last_mouse_pos = pos
                self.controller.view_updated.emit()
            return

        if tool == 'pen':
            if self.controller.is_pen_active():
                if self.dragging_pen_handle:
                    self.controller.update_pen_handle(pos)
                else:
                    self.controller.update_pen_preview(pos)
                self.update()
            return

        if self.interaction_state == 'creating':
            if tool == 'freehand':
                self.controller.update_shape(pos, is_freehand=True)
            else:
                self.controller.update_shape(pos)
            self.update()

    def mouseReleaseEvent(self, event):
        tool = self.controller.get_model().tool

        if self.interaction_state in ('moving', 'resizing'):
            self.interaction_state = 'none'
            self.active_handle = None
            return

        if tool == 'pen':
            if event.button() == Qt.LeftButton:
                self.dragging_pen_handle = False
            return

        if event.button() == Qt.LeftButton and self.interaction_state == 'creating':
            self.interaction_state = 'none'
            self.controller.commit_shape()
            self.update()

    def mouseDoubleClickEvent(self, event):
        if self.controller.get_model().tool == 'pen':
            if event.button() == Qt.LeftButton:
                self.controller.finish_pen()
                self.dragging_pen_handle = False
                self.update()
                return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.controller.delete_selected()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        model = self.controller.get_model()
        for shape in model.get_shapes():
            shape.draw(painter)
        current = model.current_shape
        if current:
            current.draw(painter)


# ==========================================
# VIEW: Right Sidebar (Icon Toolbox)
# ==========================================
class IconSidebarWidget(QFrame):
    """右侧图标库栏目"""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setFixedWidth(140)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #f7f7f7;")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        title = QLabel("<b>图标库</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        pix, path = get_icon_pixmap()

        self.icon_btn = QToolButton()
        self.icon_btn.setText("projectbuilder")
        self.icon_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.icon_btn.setIconSize(QSize(48, 48))
        self.icon_btn.setIcon(QIcon(pix))
        self.icon_btn.setCheckable(True)

        self.icon_btn.setStyleSheet("""
            QToolButton { border: 1px solid #ccc; border-radius: 4px; padding: 6px; background: white; }
            QToolButton:checked { border: 2px solid #0078d7; background: #e5f3ff; }
        """)
        self.icon_btn.clicked.connect(self.on_icon_clicked)
        layout.addWidget(self.icon_btn)

        layout.addSpacing(15)

        self.select_btn = QPushButton("选择 / 编辑")
        self.select_btn.clicked.connect(lambda: self.controller.set_tool('select'))
        layout.addWidget(self.select_btn)

        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.setStyleSheet("background-color: #ff4d4f; color: white; border-radius: 3px; padding: 5px;")
        self.delete_btn.clicked.connect(self.controller.delete_selected)
        layout.addWidget(self.delete_btn)

        layout.addStretch()

    def on_icon_clicked(self):
        self.icon_btn.setChecked(True)
        self.controller.set_tool('image')


# ==========================================
# VIEW: Main Window
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle('标图软件 - Linux 版')
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(['select', 'line', 'rect', 'circle', 'ellipse', 'freehand', 'pen', 'image'])
        self.tool_combo.currentTextChanged.connect(self.on_tool_changed)
        toolbar.addWidget(QLabel('工具:'))
        toolbar.addWidget(self.tool_combo)

        self.color_btn = QPushButton('颜色')
        self.color_btn.setStyleSheet('background-color: black;')
        self.color_btn.clicked.connect(self.choose_color)
        toolbar.addWidget(self.color_btn)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(self.controller.set_width)
        toolbar.addWidget(QLabel('线宽:'))
        toolbar.addWidget(self.width_spin)

        self.undo_btn = QPushButton('撤销')
        self.undo_btn.clicked.connect(self.controller.undo)
        toolbar.addWidget(self.undo_btn)
        self.redo_btn = QPushButton('重做')
        self.redo_btn.clicked.connect(self.controller.redo)
        toolbar.addWidget(self.redo_btn)

        self.clear_btn = QPushButton('清除')
        self.clear_btn.clicked.connect(self.controller.clear_all)
        toolbar.addWidget(self.clear_btn)

        main_layout.addLayout(toolbar)

        # 中间内容区域：左侧画布 + 右侧图标库侧边栏
        content_layout = QHBoxLayout()
        self.canvas = CanvasWidget(controller, self)
        self.sidebar = IconSidebarWidget(controller, self)

        content_layout.addWidget(self.canvas, stretch=1)
        content_layout.addWidget(self.sidebar, stretch=0)
        main_layout.addLayout(content_layout)

        self.statusBar().showMessage('就绪')
        controller.view_updated.connect(self.canvas.update)

    def on_tool_changed(self, tool_name):
        self.controller.set_tool(tool_name)
        if tool_name == 'select':
            self.statusBar().showMessage('选择工具：点击选中图形/图标，可进行拖动移动、控制柄缩放以及 Delete 删除')
        elif tool_name == 'image':
            self.sidebar.icon_btn.setChecked(True)
            self.statusBar().showMessage('图标工具：在画板上拖拽可按指定大小拉出图标')
        elif tool_name == 'pen':
            self.sidebar.icon_btn.setChecked(False)
            self.statusBar().showMessage('钢笔工具：左键放置节点与控制柄，右键或双击结束绘制')
        else:
            self.sidebar.icon_btn.setChecked(False)
            self.statusBar().showMessage(f'已选择工具: {tool_name}')

    def choose_color(self):
        color = QColorDialog.getColor(self.controller.get_color(), self, '选择颜色')
        if color.isValid():
            self.controller.set_color(color)
            self.color_btn.setStyleSheet(f'background-color: {color.name()};')


# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    app = QApplication(sys.argv)
    model = DrawingModel()
    controller = DrawingController(model)
    window = MainWindow(controller)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()