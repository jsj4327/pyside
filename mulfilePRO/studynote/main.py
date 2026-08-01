# -*- coding: utf-8 -*-

import sys
from PySide2 import QtWidgets
from note_logic import NoteAppWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = NoteAppWindow()
    window.show()
    sys.exit(app.exec_())