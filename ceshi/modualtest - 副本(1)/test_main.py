# -*- coding:utf-8 -*-
import sys
from PySide2.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide2.QtGui import QFont

from file_browser import FileBrowserWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件浏览器测试")
        self.resize(800, 500)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = FileBrowserWidget()
        layout.addWidget(self.browser)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont()
    for name in ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei"]:
        if QFont(name).exactMatch():
            font = QFont(name, 9)
            break
    app.setFont(font)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())