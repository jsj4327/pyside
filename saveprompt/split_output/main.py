"""
应用程序入口点
初始化 QApplication 并启动主窗口。
"""
import sys
from PySide2.QtWidgets import QApplication
from main_window import PromptManagerApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PromptManagerApp()
    window.show()
    sys.exit(app.exec_())
