from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QStatusBar,
    QColorDialog, QSpinBox
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QColor
from .canvas import CanvasWidget


class MainWindow(QMainWindow):
    def init(self, controller):
        super().init()
        self.controller = controller
        self.setWindowTitle('标图软件 - Linux 版')
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 工具栏
        toolbar = QHBoxLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(['line', 'rect', 'circle', 'ellipse', 'freehand'])
        self.tool_combo.currentTextChanged.connect(self.controller.set_tool)
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

        layout.addLayout(toolbar)

        self.canvas = CanvasWidget(controller, self)
        layout.addWidget(self.canvas)

        self.statusBar().showMessage('就绪')
        controller.view_updated.connect(self.canvas.update)

    def choose_color(self):
        color = QColorDialog.getColor(self.controller.get_color(), self, '选择颜色')
        if color.isValid():
            self.controller.set_color(color)
            self.color_btn.setStyleSheet(f'background-color: {color.name()};')
