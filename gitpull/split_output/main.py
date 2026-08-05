import sys
from PySide2.QtWidgets import QApplication

from ui.main_window import SimpleGitClient

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = SimpleGitClient()
    window.show()
    sys.exit(app.exec_())
