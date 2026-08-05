"""
异步加载过渡界面组件
"""
from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide2.QtCore import Qt


class LoadingScreen(QWidget):
    """数据加载时的过渡等待界面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch()

        lbl = QLabel("<b>正在异步加载数据，请稍候...</b>")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        self.bar = QProgressBar()
        self.bar.setFixedWidth(300)
        self.bar.setRange(0, 0)  # 跑马灯效果
        layout.addWidget(self.bar, alignment=Qt.AlignCenter)

        layout.addStretch()
