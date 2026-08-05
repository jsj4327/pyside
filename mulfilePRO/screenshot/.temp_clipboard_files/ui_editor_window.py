import math
from PySide2.QtCore import Qt, QRect, QPoint, QLineF
from PySide2.QtGui import (QPainter, QPen, QBrush, QColor, QImage, QPixmap, 
                           QGuiApplication, QKeySequence)
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QSpinBox, QComboBox, 
                               QCheckBox, QFrame, QShortcut)

class ScreenshotEditorWindow(QWidget):
    """功能完备的截图标注与编辑窗口（支持撤回 Ctrl+Z、悬停选中、拖动移动）"""
    def __init__(self, pixmap: QPixmap, callback=None):
        super().__init__()
        self.setWindowTitle("截图编辑与标注")
        self.setWindowFlags(Qt.WindowType(Qt.WindowStaysOnTopHint | Qt.Window))
        
        self.original_pixmap = pixmap
        self.base_image = pixmap.toImage() # 纯净底图
        self.callback = callback
        
        # 矢量图形记录列表：保存所有绘制的图形字典
        self.shapes = []
        
        # 标注状态参数
        self.tool_mode = "rect"          
        self.pen_width = 3               
        self.pen_color = QColor(255, 0, 0) 
        self.fill_enabled = False        
        
        self.outline_enabled = False     
        self.outline_color = QColor(255, 255, 255) 
        self.outline_width = 7           

        self.init_ui(pixmap)
        
        # 绑定撤回快捷键 Ctrl+Z
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_last_shape)

    def init_ui(self, pixmap: QPixmap):
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        target_w = int(screen_geo.width() * 0.85)
        target_h = int(screen_geo.height() * 0.85)
        
        total_w = target_w + 160
        total_h = target_h
        
        x = screen_geo.x() + (screen_geo.width() - total_w) // 2
        y = screen_geo.y() + (screen_geo.height() - total_h) // 2
        self.setGeometry(x, y, total_w, total_h)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 画布区域
        self.canvas_widget = CanvasWidget(self)
        main_layout.addWidget(self.canvas_widget, stretch=1)

        # 右侧固定工具栏面板
        self.toolbar_panel = QWidget()
        self.toolbar_panel.setFixedWidth(160)
        self.toolbar_panel.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #ffffff; font-size: 12px; }
            QPushButton { background-color: #3c3c3c; border: 1px solid #555; border-radius: 4px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #0078D7; border-color: #0086F8; }
            QPushButton:checked { background-color: #0078D7; border-color: #FFF; }
            QPushButton#save_btn { background-color: #107C10; border: none; margin-top: 10px; }
            QPushButton#save_btn:hover { background-color: #169816; }
            QPushButton#undo_btn { background-color: #c42b1c; border: none; }
            QPushButton#undo_btn:hover { background-color: #d13438; }
            QLabel { color: #ccc; font-weight: bold; margin-top: 3px; }
            QComboBox, QSpinBox { background-color: #333; color: white; border: 1px solid #555; border-radius: 3px; padding: 4px; }
            QCheckBox { spacing: 5px; }
            QFrame#separator { color: #555; }
        """)
        
        t_layout = QVBoxLayout(self.toolbar_panel)
        t_layout.setContentsMargins(10, 15, 10, 15)
        t_layout.setSpacing(6)

        t_layout.addWidget(QLabel("工具选择:"))
        self.btn_rect = QPushButton("矩形框")
        self.btn_rect.setCheckable(True)
        self.btn_rect.setChecked(True)
        self.btn_rect.clicked.connect(lambda: self.set_tool("rect"))
        t_layout.addWidget(self.btn_rect)

        self.btn_ellipse = QPushButton("椭圆框")
        self.btn_ellipse.setCheckable(True)
        self.btn_ellipse.clicked.connect(lambda: self.set_tool("ellipse"))
        t_layout.addWidget(self.btn_ellipse)

        self.btn_line = QPushButton("线条")
        self.btn_line.setCheckable(True)
        self.btn_line.clicked.connect(lambda: self.set_tool("line"))
        t_layout.addWidget(self.btn_line)

        self.btn_arrow = QPushButton("箭头")
        self.btn_arrow.setCheckable(True)
        self.btn_arrow.clicked.connect(lambda: self.set_tool("arrow"))
        t_layout.addWidget(self.btn_arrow)

        t_layout.addWidget(QLabel("画笔颜色:"))
        self.combo_color = QComboBox()
        self.populate_color_combo(self.combo_color)
        self.combo_color.setCurrentIndex(0) # 默认红色
        self.combo_color.currentIndexChanged.connect(self.on_color_changed)
        t_layout.addWidget(self.combo_color)

        t_layout.addWidget(QLabel("线条粗细:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20)
        self.spin_width.setValue(3)
        self.spin_width.valueChanged.connect(lambda v: setattr(self, 'pen_width', v))
        t_layout.addWidget(self.spin_width)

        self.chk_fill = QCheckBox("图形内部填充")
        self.chk_fill.stateChanged.connect(lambda s: setattr(self, 'fill_enabled', s == Qt.Checked))
        t_layout.addWidget(self.chk_fill)

        line = QFrame()
        line.setObjectName("separator")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        t_layout.addWidget(line)

        self.chk_outline = QCheckBox("启用线条描边")
        self.chk_outline.stateChanged.connect(lambda s: setattr(self, 'outline_enabled', s == Qt.Checked))
        t_layout.addWidget(self.chk_outline)

        t_layout.addWidget(QLabel("描边颜色:"))
        self.combo_outline_color = QComboBox()
        self.populate_color_combo(self.combo_outline_color)
        self.combo_outline_color.setCurrentIndex(5) # 默认白色
        self.combo_outline_color.currentIndexChanged.connect(self.on_outline_color_changed)
        t_layout.addWidget(self.combo_outline_color)

        t_layout.addWidget(QLabel("描边粗细:"))
        self.spin_outline_width = QSpinBox()
        self.spin_outline_width.setRange(2, 30)
        self.spin_outline_width.setValue(7)
        self.spin_outline_width.valueChanged.connect(lambda v: setattr(self, 'outline_width', v))
        t_layout.addWidget(self.spin_outline_width)

        t_layout.addStretch()

        btn_undo = QPushButton("撤回 (Ctrl+Z)")
        btn_undo.setObjectName("undo_btn")
        btn_undo.clicked.connect(self.undo_last_shape)
        t_layout.addWidget(btn_undo)

        btn_save = QPushButton("完成并保存")
        btn_save.setObjectName("save_btn")
        btn_save.clicked.connect(self.finish_editing)
        t_layout.addWidget(btn_save)

        main_layout.addWidget(self.toolbar_panel)

    def populate_color_combo(self, combo: QComboBox):
        colors = [("红色", QColor(255,0,0)), ("绿色", QColor(0,200,0)), 
                  ("蓝色", QColor(0,120,215)), ("黄色", QColor(255,200,0)), 
                  ("黑色", QColor(0,0,0)), ("白色", QColor(255,255,255))]
        for name, color in colors:
            combo.addItem(name, color)

    def set_tool(self, mode):
        self.tool_mode = mode
        self.btn_rect.setChecked(mode == "rect")
        self.btn_ellipse.setChecked(mode == "ellipse")
        self.btn_line.setChecked(mode == "line")
        self.btn_arrow.setChecked(mode == "arrow")

    def on_color_changed(self, index):
        self.pen_color = self.combo_color.itemData(index)

    def on_outline_color_changed(self, index):
        self.outline_color = self.combo_outline_color.itemData(index)

    def undo_last_shape(self):
        """撤回最后一个绘制的图形"""
        if self.shapes:
            self.shapes.pop()
            self.canvas_widget.update()

    def draw_shape_on_painter(self, painter: QPainter, shape: dict):
        """通用图形绘制引擎（接收统一的形状字典数据）"""
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        mode = shape['mode']
        start = shape['start']
        end = shape['end']
        color = shape['color']
        width = shape['width']
        fill = shape['fill']
        outline = shape['outline']
        out_color = shape['out_color']
        out_width = shape['out_width']

        # 1. 绘制底层描边
        if outline and mode in ["line", "arrow"]:
            outline_pen = QPen(out_color, out_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(outline_pen)
            if mode == "line":
                painter.drawLine(start, end)
            elif mode == "arrow":
                self.draw_arrow_path(painter, start, end, out_width)

        # 2. 绘制常规主体图形
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)

        if fill and mode in ["rect", "ellipse"]:
            fill_c = QColor(color)
            fill_c.setAlpha(50)
            painter.setBrush(QBrush(fill_c))
        else:
            painter.setBrush(Qt.NoBrush)

        if mode == "rect":
            painter.drawRect(QRect(start, end).normalized())
        elif mode == "ellipse":
            painter.drawEllipse(QRect(start, end).normalized())
        elif mode == "line":
            painter.drawLine(start, end)
        elif mode == "arrow":
            self.draw_arrow_path(painter, start, end, width)

    def draw_arrow_path(self, painter: QPainter, start: QPoint, end: QPoint, width: int):
        painter.drawLine(start, end)
        line = QLineF(start, end)
        angle = line.angle()
        arrow_size = 12 + width * 1.5
        rad1 = math.radians(angle + 150)
        rad2 = math.radians(angle - 150)
        arrow_p1 = QPoint(int(end.x() + arrow_size * math.cos(rad1)), int(end.y() - arrow_size * math.sin(rad1)))
        arrow_p2 = QPoint(int(end.x() + arrow_size * math.cos(rad2)), int(end.y() - arrow_size * math.sin(rad2)))
        painter.drawLine(end, arrow_p1)
        painter.drawLine(end, arrow_p2)

    def finish_editing(self):
        self.close()
        if self.callback:
            # 渲染所有形状到一个干净的图像中并返回
            final_image = self.base_image.copy()
            painter = QPainter(final_image)
            for shape in self.shapes:
                self.draw_shape_on_painter(painter, shape)
            painter.end()
            self.callback(QPixmap.fromImage(final_image))


class CanvasWidget(QWidget):
    """独立的截图画布区域，负责坐标映射、交互绘制、命中测试与拖动"""
    def __init__(self, parent: ScreenshotEditorWindow):
        super().__init__()
        self.parent_window = parent
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor) # 默认十字光标
        
        # 交互状态
        self.is_drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        
        self.hovered_shape_index = -1   # 悬停的对象索引
        self.moving_shape_index = -1    # 正在移动的对象索引
        self.move_last_pos = QPoint()   # 拖动时的上一个坐标

    def get_image_offset(self):
        img_w = self.parent_window.base_image.width()
        img_h = self.parent_window.base_image.height()
        x = max(0, (self.width() - img_w) // 2)
        y = max(0, (self.height() - img_h) // 2)
        return x, y

    def get_image_pos(self, widget_pos: QPoint):
        offset_x, offset_y = self.get_image_offset()
        return widget_pos - QPoint(offset_x, offset_y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        offset_x, offset_y = self.get_image_offset()
        painter.drawImage(offset_x, offset_y, self.parent_window.base_image)

        # 平移坐标系，使画笔原点对齐图片的左上角
        painter.translate(offset_x, offset_y)

        # 1. 绘制历史图形
        for shape in self.parent_window.shapes:
            self.parent_window.draw_shape_on_painter(painter, shape)

        # 2. 绘制正在进行的新图形
        if self.is_drawing and not self.start_point.isNull():
            current_shape = {
                'mode': self.parent_window.tool_mode,
                'start': self.start_point,
                'end': self.end_point,
                'color': self.parent_window.pen_color,
                'width': self.parent_window.pen_width,
                'fill': self.parent_window.fill_enabled,
                'outline': self.parent_window.outline_enabled,
                'out_color': self.parent_window.outline_color,
                'out_width': self.parent_window.outline_width
            }
            self.parent_window.draw_shape_on_painter(painter, current_shape)

    def hit_test_all(self, pt: QPoint):
        """测试点是否落在任何图形上（倒序遍历以优先选中最上层）"""
        for i in range(len(self.parent_window.shapes) - 1, -1, -1):
            if self.hit_test_shape(self.parent_window.shapes[i], pt):
                return i
        return -1

    def hit_test_shape(self, shape, pt: QPoint):
        mode = shape['mode']
        p1 = shape['start']
        p2 = shape['end']
        w = shape['width'] + (shape['out_width'] if shape['outline'] else 0)
        tol = max(w, 8) # 容差至少 8 像素，方便选中
        
        if mode in ["rect", "ellipse"]:
            rect = QRect(p1, p2).normalized()
            return rect.adjusted(-tol, -tol, tol, tol).contains(pt)
        else:
            # 线条/箭头的命中测试（点到线段的距离）
            x0, y0 = pt.x(), pt.y()
            x1, y1 = p1.x(), p1.y()
            x2, y2 = p2.x(), p2.y()
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                return math.hypot(x0 - x1, y0 - y1) <= tol
            t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
            t = max(0, min(1, t))
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            return math.hypot(x0 - closest_x, y0 - closest_y) <= tol

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            img_pos = self.get_image_pos(event.pos())
            
            # 如果按在了某个图形上，进入拖动模式
            if self.hovered_shape_index != -1:
                self.moving_shape_index = self.hovered_shape_index
                self.move_last_pos = img_pos
            else:
                # 否则进入绘制新图形模式
                self.is_drawing = True
                self.start_point = img_pos
                self.end_point = img_pos
            self.update()

    def mouseMoveEvent(self, event):
        img_pos = self.get_image_pos(event.pos())
        
        if self.moving_shape_index != -1:
            # 拖动图形逻辑
            dx = img_pos.x() - self.move_last_pos.x()
            dy = img_pos.y() - self.move_last_pos.y()
            shape = self.parent_window.shapes[self.moving_shape_index]
            shape['start'] += QPoint(dx, dy)
            shape['end'] += QPoint(dx, dy)
            self.move_last_pos = img_pos
            self.update()
        elif self.is_drawing:
            # 绘制新图形逻辑
            self.end_point = img_pos
            self.update()
        else:
            # 悬停测试逻辑（改变光标）
            idx = self.hit_test_all(img_pos)
            if idx != self.hovered_shape_index:
                self.hovered_shape_index = idx
                if idx != -1:
                    self.setCursor(Qt.SizeAllCursor) # 移动箭头光标
                else:
                    self.setCursor(Qt.CrossCursor)   # 十字光标

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.moving_shape_index != -1:
                self.moving_shape_index = -1
            elif self.is_drawing:
                self.is_drawing = False
                # 结束绘制，将新图形数据封存并加入到列表中
                new_shape = {
                    'mode': self.parent_window.tool_mode,
                    'start': self.start_point,
                    'end': self.end_point,
                    'color': self.parent_window.pen_color,
                    'width': self.parent_window.pen_width,
                    'fill': self.parent_window.fill_enabled,
                    'outline': self.parent_window.outline_enabled,
                    'out_color': self.parent_window.outline_color,
                    'out_width': self.parent_window.outline_width
                }
                self.parent_window.shapes.append(new_shape)
            self.update()