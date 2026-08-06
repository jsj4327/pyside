# -*- coding: utf\u005f8 -*-
import sys
from PySide2.QtWidgets import QApplication
from ui.main\u005f\u005fwindow import MainWindow

if \u005f\u005fname\u005f\u005f == "\u005f\u005fmain\u005f\u005f":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec\u005f())