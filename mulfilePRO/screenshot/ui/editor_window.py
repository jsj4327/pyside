# -*- coding: utf-8 -*-
# 文件: ui/editor_window.py

from PySide2.QtCore import Qt
from PySide2.QtGui import (QPainter, QColor, QPixmap, QGuiApplication, QKeySequence)
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QSpinBox, QComboBox, 
                               QCheckBox, QFrame, QShortcut)

# 引入拆分出来的画布和渲染器
from ui.canvas import CanvasWidget, ShapeRenderer

class ScreenshotEditorWindow(QWidget):
    """功能完备的截图标注与编辑窗口"""
    def __init__(self, pixmap: QPixmap, callback=None):
        super().__init__()
        self.setWindowTitle("截图编辑与标注")
        self.setWindowFlags(Qt.WindowType(Qt.WindowStaysOnTopHint | Qt.Window))
        
        self.original_pixmap = pixmap
        self.base_image = pixmap.toImage() 
        self.callback = callback
        
        self.shapes = []
        
        self.tool_mode = "rect"          
        self.pen_width = 3               
        self.pen_color = QColor(255, 0, 0) 
        self.fill_enabled = False        
        self.outline_enabled = False     
        self.outline_color = QColor(255, 255, 255) 
        self.outline_width = 7           

        self.init_ui()
        
        # 绑定快捷键：撤回 Ctrl+Z 与 删除 Delete
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_last_shape)

        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.delete_selected_shape)

    def init_ui(self):
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

        # 载入拆分后的独立画布组件
        self.canvas_widget = CanvasWidget(self)
        main_layout.addWidget(self.canvas_widget, stretch=1)

        self.setup_toolbar(main_layout)

    def setup_toolbar(self, main_layout):
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

        self.btn_text = QPushButton("文本")
        self.btn_text.setCheckable(True)
        self.btn_text.clicked.connect(lambda: self.set_tool("text"))
        t_layout.addWidget(self.btn_text)

        t_layout.addWidget(QLabel("画笔颜色:"))
        self.combo_color = QComboBox()
        self.populate_color_combo(self.combo_color)
        self.combo_color.setCurrentIndex(0) 
        self.combo_color.currentIndexChanged.connect(self.on_color_changed)
        t_layout.addWidget(self.combo_color)

        t_layout.addWidget(QLabel("粗细/字号:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20)
        self.spin_width.setValue(3)
        self.spin_width.valueChanged.connect(self.on_pen_width_changed)
        t_layout.addWidget(self.spin_width)

        self.chk_fill = QCheckBox("图形内部填充")
        self.chk_fill.stateChanged.connect(self.on_fill_changed)
        t_layout.addWidget(self.chk_fill)

        line = QFrame()
        line.setObjectName("separator")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        t_layout.addWidget(line)

        self.chk_outline = QCheckBox("启用线条描边")
        self.chk_outline.stateChanged.connect(self.on_outline_changed)
        t_layout.addWidget(self.chk_outline)

        t_layout.addWidget(QLabel("描边颜色:"))
        self.combo_outline_color = QComboBox()
        self.populate_color_combo(self.combo_outline_color)
        self.combo_outline_color.setCurrentIndex(5) 
        self.combo_outline_color.currentIndexChanged.connect(self.on_outline_color_changed)
        t_layout.addWidget(self.combo_outline_color)

        t_layout.addWidget(QLabel("描边粗细:"))
        self.spin_outline_width = QSpinBox()
        self.spin_outline_width.setRange(2, 30)
        self.spin_outline_width.setValue(7)
        self.spin_outline_width.valueChanged.connect(self.on_outline_width_changed)
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
        self.canvas_widget.commit_text_if_active()
        
        self.tool_mode = mode
        self.btn_rect.setChecked(mode == "rect")
        self.btn_ellipse.setChecked(mode == "ellipse")
        self.btn_line.setChecked(mode == "line")
        self.btn_arrow.setChecked(mode == "arrow")
        self.btn_text.setChecked(mode == "text")
        
        if mode == 'text':
            self.canvas_widget.setCursor(Qt.IBeamCursor)
        else:
            self.canvas_widget.setCursor(Qt.CrossCursor)

    # ==================== 事件槽函数（支持实时联动） ====================

    def on_color_changed(self, index):
        self.pen_color = self.combo_color.itemData(index)
        self.canvas_widget.update_selected_shape_style('color', self.pen_color)
        self.canvas_widget.update_active_text_editor_style()

    def on_outline_color_changed(self, index):
        self.outline_color = self.combo_outline_color.itemData(index)
        self.canvas_widget.update_selected_shape_style('out_color', self.outline_color)

    def on_pen_width_changed(self, v):
        self.pen_width = v
        self.canvas_widget.update_selected_shape_style('width', v)
        self.canvas_widget.update_active_text_editor_style()

    def on_fill_changed(self, state):
        self.fill_enabled = (state == Qt.Checked)
        self.canvas_widget.update_selected_shape_style('fill', self.fill_enabled)

    def on_outline_changed(self, state):
        self.outline_enabled = (state == Qt.Checked)
        self.canvas_widget.update_selected_shape_style('outline', self.outline_enabled)

    def on_outline_width_changed(self, v):
        self.outline_width = v
        self.canvas_widget.update_selected_shape_style('out_width', v)

    def undo_last_shape(self):
        self.canvas_widget.commit_text_if_active()
        if self.shapes:
            self.shapes.pop()
            self.canvas_widget.update()

    def delete_selected_shape(self):
        if hasattr(self.canvas_widget, 'selected_shape_index') and self.canvas_widget.selected_shape_index != -1:
            idx = self.canvas_widget.selected_shape_index
            if 0 <= idx < len(self.shapes):
                self.shapes.pop(idx)
                self.canvas_widget.selected_shape_index = -1
                self.canvas_widget.commit_text_if_active()
                self.canvas_widget.update()

    def finish_editing(self):
        self.canvas_widget.commit_text_if_active()
        self.close()
        if self.callback:
            final_image = self.base_image.copy()
            painter = QPainter(final_image)
            for shape in self.shapes:
                ShapeRenderer.draw(painter, shape) 
            painter.end()
            self.callback(QPixmap.fromImage(final_image))