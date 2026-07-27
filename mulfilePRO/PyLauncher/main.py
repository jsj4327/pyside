import sys
from PySide2.QtWidgets import QApplication
from controller.main_controller import MainController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 初始化主控制器（内部会依次拉起 Model、View 和 Service）
    main_controller = MainController()
    main_controller.show()
    
    sys.exit(app.exec_())