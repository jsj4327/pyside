import sys
from PySide2.QtWidgets import QApplication
from view.main_window import MainWindow
from controller.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    
    main_window = MainWindow()
    main_controller = MainController(main_window)
    
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()