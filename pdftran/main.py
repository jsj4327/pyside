# -*- coding: utf_8 -*-
import sys
from PySide2.QtWidgets import QApplication
from ui.main__window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())