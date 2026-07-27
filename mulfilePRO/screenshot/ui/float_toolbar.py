from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QGuiApplication
from PySide2.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

class ManualScrollControlWindow(QWidget):
    """手动滚动截图控制悬浮条"""
    capture_frame_signal = Signal()
    finish_signal = Signal()
    cancel_signal = Signal()

    def __init__(self, count=0):
        super().__init__()
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 240);
                border-radius: 8px;
                border: 1px solid #666;
            }
            QLabel {
                color: #00FFCC;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0086F8;
            }
            QPushButton#finish_btn {
                background-color: #107C10;
            }
            QPushButton#finish_btn:hover {
                background-color: #169816;
            }
            QPushButton#cancel_btn {
                background-color: #D83B01;
            }
            QPushButton#cancel_btn:hover {
                background-color: #EA4300;
            }
        """)
        
        box_layout = QHBoxLayout(container)
        box_layout.setContentsMargins(10, 6, 10, 6)

        self.label = QLabel(f"已截取: {count} 张")
        box_layout.addWidget(self.label)

        self.btn_capture = QPushButton("截取当前帧")
        self.btn_capture.clicked.connect(self.capture_frame_signal.emit)
        box_layout.addWidget(self.btn_capture)

        self.btn_finish = QPushButton("停止并拼接")
        self.btn_finish.setObjectName("finish_btn")
        self.btn_finish.clicked.connect(self.finish_signal.emit)
        box_layout.addWidget(self.btn_finish)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("cancel_btn")
        self.btn_cancel.clicked.connect(self.cancel_signal.emit)
        box_layout.addWidget(self.btn_cancel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        screen = QGuiApplication.primaryScreen().geometry()
        self.adjustSize()
        self.move((screen.width() - self.width()) // 2, 30)

    def update_count(self, count):
        self.label.setText(f"已截取: {count} 张")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_signal.emit()