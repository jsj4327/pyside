"""程序入口，初始化QApplication并启动主窗口"""
import sys
from PySide2.QtWidgets import QApplication
from ui.main_window import ThumbnailViewer


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ThumbnailViewer()
    # 图片旋转功能已集成在ThumbnailViewer中，可通过工具栏或右键菜单使用
    viewer.show()
    sys.exit(app.exec_())