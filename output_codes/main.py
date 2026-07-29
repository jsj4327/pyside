import sys
from PySide2.QtWidgets import QApplication
from model import ExcelModel
from view import MainWindow
from controller import ExcelController


def main():
    app = QApplication(sys.argv)

    model = ExcelModel()
    view = MainWindow()
    controller = ExcelController(model, view)

    view.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()