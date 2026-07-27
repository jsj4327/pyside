import sys
from PySide2.QtWidgets import QApplication
from ui.control_panel import ControlPanel

if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())