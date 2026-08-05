import sys
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont

from ui.main_window import LauncherWindow

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    font = QFont("Noto Sans CJK SC", 10)
    if not font.exactMatch():
        font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = LauncherWindow()
    window.show()
    sys.exit(app.exec_())
