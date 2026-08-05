"""
应用程序入口点
启动PySide2极客文件浏览器应用。
"""
import sys
import logging
from PySide2.QtWidgets import QApplication
from main_window import FileViewer


def setup_logging() -> None:
    """配置应用日志系统。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main() -> None:
    """应用程序主函数。"""
    setup_logging()
    app = QApplication(sys.argv)
    viewer = FileViewer()
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
