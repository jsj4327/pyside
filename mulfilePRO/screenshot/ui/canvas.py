# -*- coding: utf-8 -*-
# 文件: ui/canvas.py

import math
from PySide2.QtCore import Qt, QRect, QPoint, QLineF
from PySide2.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPainterPath
from PySide2.QtWidgets import QWidget, QTextEdit

class ShapeRenderer:
    """静态渲染引擎：负责将 shape 数据绘制到 QPainter 上（支持文本描边与样式）"""
    @staticmethod
    def draw(painter: QPainter, shape: dict):
        painter.setRenderHint(QPainter.Antialiasing, True)
        mode = shape['mode']
        start = shape['start']
        end = shape.get('end', start)
        color = shape['color']
        width = shape['width']

        # 提取通用样式
        outline = shape.get('outline', False)
        out_color = shape.get('out_color', QColor(255, 255, 255))
        out_width = shape.get('out_width', 7)

        # 文本渲染特殊处理
        if mode == 'text':
            font = QFont()
            font.setPointSize(shape.get('font_size', 12))
            font.setBold(True)
            painter.setFont(font)
            
            text_str = shape.get('text', '')
            outline = shape.get('outline', False)
            out_color = shape.get('out_color', QColor(255, 255, 255))
            out_width = shape.get('out_width', 7)

            # 定义与下方 drawText 完全一致的绘制区域
            text_rect = QRect(start.x(), start.y(), 2000, 2000)

            # 如果文本开启了描边：利用 QPainterPath 在同一区域生成路径并描边
            if outline:
                from PySide2.QtGui import QPainterPath
                path = QPainterPath()
                # 使用和 drawText 相同的矩形区域和对齐方式填充文本路径，确保几何位置零错位
                path.addText(text_rect.x(), text_rect.y() + painter.fontMetrics().ascent(), font, text_str)
                
                painter.setPen(QPen(out_color, max(2, int(out_width * 0.7)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

            # 绘制文本主体
            painter.setPen(QPen(color))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop, text_str)
            return

        fill = shape.get('fill', False)

        # 1. 绘制底层描边 (非文本图形)
        if outline and mode in ["line", "arrow"]:
            outline_pen = QPen(out_color, out_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(outline_pen)
            if mode == "line":
                painter.drawLine(start, end)
            elif mode == "arrow":
                ShapeRenderer.draw_arrow_path(painter, start, end, out_width)

        # 2. 绘制主体图形
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
            ShapeRenderer.draw_arrow_path(painter, start, end, width)

    @staticmethod
    def draw_arrow_path(painter: QPainter, start: QPoint, end: QPoint, width: int):
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


class CanvasWidget(QWidget):
    """独立的截图画布区域"""
    def __init__(self, parent):
        super().__init__()
        self.parent_window = parent
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)
        
        self.is_drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        
        self.hovered_shape_index = -1
        self.selected_shape_index = -1  
        self.moving_shape_index = -1
        self.move_last_pos = QPoint()

        self.text_editor = None

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
        painter.translate(offset_x, offset_y)

        # 1. 绘制所有历史图形
        for idx, shape in enumerate(self.parent_window.shapes):
            ShapeRenderer.draw(painter, shape)
            if idx == self.selected_shape_index:
                painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                if shape['mode'] == 'text':
                    # 为文本对象计算一个包裹虚线框
                    font = QFont()
                    font.setPointSize(shape.get('font_size', 12))
                    font.setBold(True)
                    fm = QFontMetrics(font)
                    p1 = shape['start']
                    rect = fm.boundingRect(p1.x(), p1.y(), 2000, 2000, Qt.AlignLeft | Qt.AlignTop, shape['text'])
                    painter.drawRect(rect.adjusted(-4, -4, 4, 4))
                else:
                    p1, p2 = shape['start'], shape['end']
                    painter.drawRect(QRect(p1, p2).normalized().adjusted(-3, -3, 3, 3))

        # 2. 绘制正在进行的新图形
        if self.is_drawing and not self.start_point.isNull() and self.parent_window.tool_mode != 'text':
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
            ShapeRenderer.draw(painter, current_shape)

    def commit_text_if_active(self):
        """如果当前存在文本输入框，则将其内容固化或更新回图形数据（携带描边状态）"""
        if self.text_editor and self.text_editor.isVisible():
            text = self.text_editor.toPlainText()
            if text.strip():
                ox, oy = self.get_image_offset()
                img_pos = self.text_editor.pos() - QPoint(ox, oy)
                font_size = max(8, self.parent_window.pen_width * 4)
                
                new_shape = {
                    'mode': 'text',
                    'start': img_pos + QPoint(4, 4),
                    'text': text,
                    'color': self.parent_window.pen_color,
                    'width': self.parent_window.pen_width,
                    'font_size': font_size,
                    'outline': self.parent_window.outline_enabled,       # 绑定当前描边开关
                    'out_color': self.parent_window.outline_color,     # 绑定当前描边颜色
                    'out_width': self.parent_window.outline_width      # 绑定当前描边粗细
                }
                
                if hasattr(self.text_editor, 'edit_target_index') and self.text_editor.edit_target_index != -1:
                    self.parent_window.shapes[self.text_editor.edit_target_index] = new_shape
                else:
                    self.parent_window.shapes.append(new_shape)
            
            self.text_editor.hide()
            self.text_editor.deleteLater()
            self.text_editor = None
            self.update()

    def spawn_text_editor(self, img_pos, edit_index=-1):
        self.commit_text_if_active()
        
        self.text_editor = QTextEdit(self)
        self.text_editor.edit_target_index = edit_index
        
        initial_text = ""
        font_size = max(8, self.parent_window.pen_width * 4)
        
        if edit_index != -1:
            shape = self.parent_window.shapes[edit_index]
            initial_text = shape['text']
            img_pos = shape['start'] - QPoint(4, 4)
            font_size = shape.get('font_size', font_size)
            self.text_editor.setPlainText(initial_text)
        else:
            self.text_editor.setPlaceholderText("在此输入文字...")

        self.text_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(255, 255, 255, 50);
                border: 1px dashed #0078D7;
                color: {self.parent_window.pen_color.name()};
                font-size: {font_size}pt;
                font-weight: bold;
            }}
        """)
        ox, oy = self.get_image_offset()
        self.text_editor.move(img_pos.x() + ox, img_pos.y() + oy)
        self.text_editor.resize(260, 110)
        self.text_editor.show()
        self.text_editor.setFocus()

    def update_selected_shape_style(self, prop_key, prop_value):
        """实时更新当前选中图形或文本的对应属性（包括描边开关和颜色）"""
        if self.selected_shape_index != -1 and 0 <= self.selected_shape_index < len(self.parent_window.shapes):
            shape = self.parent_window.shapes[self.selected_shape_index]
            shape[prop_key] = prop_value
            if shape['mode'] == 'text' and prop_key == 'width':
                shape['font_size'] = max(8, prop_value * 4)
            self.update()

    def update_active_text_editor_style(self):
        if self.text_editor and self.text_editor.isVisible():
            font_size = max(8, self.parent_window.pen_width * 4)
            color_name = self.parent_window.pen_color.name()
            self.text_editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: rgba(255, 255, 255, 50);
                    border: 1px dashed #0078D7;
                    color: {color_name};
                    font-size: {font_size}pt;
                    font-weight: bold;
                }}
            """)

    def hit_test_all(self, pt: QPoint):
        for i in range(len(self.parent_window.shapes) - 1, -1, -1):
            if self.hit_test_shape(self.parent_window.shapes[i], pt):
                return i
        return -1

    def hit_test_shape(self, shape, pt: QPoint):
        mode = shape['mode']
        p1 = shape['start']
        
        if mode == 'text':
            font = QFont()
            font.setPointSize(shape.get('font_size', 12))
            font.setBold(True)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(p1.x(), p1.y(), 2000, 2000, Qt.AlignLeft | Qt.AlignTop, shape['text'])
            return rect.adjusted(-5, -5, 10, 10).contains(pt)

        p2 = shape['end']
        w = shape['width'] + (shape.get('out_width', 0) if shape.get('outline', False) else 0)
        tol = max(w, 8)
        
        if mode in ["rect", "ellipse"]:
            rect = QRect(p1, p2).normalized()
            return rect.adjusted(-tol, -tol, tol, tol).contains(pt)
        else:
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
            self.setFocus()
            img_pos = self.get_image_pos(event.pos())
            
            if self.parent_window.tool_mode != 'text' or self.hovered_shape_index != -1:
                self.commit_text_if_active()

            clicked_idx = self.hit_test_all(img_pos)
            self.selected_shape_index = clicked_idx

            if clicked_idx != -1:
                self.moving_shape_index = clicked_idx
                self.move_last_pos = img_pos
            elif self.parent_window.tool_mode == 'text':
                self.spawn_text_editor(img_pos)
            else:
                self.is_drawing = True
                self.start_point = img_pos
                self.end_point = img_pos
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            img_pos = self.get_image_pos(event.pos())
            idx = self.hit_test_all(img_pos)
            if idx != -1 and self.parent_window.shapes[idx]['mode'] == 'text':
                self.spawn_text_editor(img_pos, edit_index=idx)

    def mouseMoveEvent(self, event):
        img_pos = self.get_image_pos(event.pos())
        
        if self.moving_shape_index != -1:
            dx = img_pos.x() - self.move_last_pos.x()
            dy = img_pos.y() - self.move_last_pos.y()
            shape = self.parent_window.shapes[self.moving_shape_index]
            shape['start'] += QPoint(dx, dy)
            if 'end' in shape:
                shape['end'] += QPoint(dx, dy)
            self.move_last_pos = img_pos
            self.update()
        elif self.is_drawing:
            self.end_point = img_pos
            self.update()
        else:
            idx = self.hit_test_all(img_pos)
            if idx != self.hovered_shape_index:
                self.hovered_shape_index = idx
                if idx != -1:
                    self.setCursor(Qt.SizeAllCursor)
                elif self.parent_window.tool_mode == 'text':
                    self.setCursor(Qt.IBeamCursor)
                else:
                    self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.moving_shape_index != -1:
                self.moving_shape_index = -1
            elif self.is_drawing:
                self.is_drawing = False
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
                self.selected_shape_index = len(self.parent_window.shapes) - 1
            self.update()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Back):
            if self.selected_shape_index != -1 and 0 <= self.selected_shape_index < len(self.parent_window.shapes):
                self.parent_window.shapes.pop(self.selected_shape_index)
                self.selected_shape_index = -1
                self.commit_text_if_active()
                self.update()
        elif event.key() == Qt.Key_Escape:
            self.commit_text_if_active()
            self.selected_shape_index = -1
            self.update()