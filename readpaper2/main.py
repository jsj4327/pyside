# main.py
"""
程序主入口：初始化 QApplication、日志体系、全局 Exception 钩子与界面初始化。
"""
import sys
import logging
from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2.QtCore import Qt
from config import GLOBAL_QSS, LOG_DIR
from db.connection import DatabaseConnection
from db.repositories import ArticleRepository
from ui.main_window import MainWindow

# 全局日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Main")

def global_exception_hook(exctype, value, traceback):
    """全局未捕获异常 Hook，防止程序崩溃闪退"""
    logger.critical("捕获到未处理的全局异常:", exc_info=(exctype, value, traceback))
    msg = f"系统发生未预期的错误:\n{str(value)}"
    QMessageBox.critical(None, "致命错误", msg)

def main():
    sys.excepthook = global_exception_hook

    # 启用高 DPI 缩放适配
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)

    # 初始化数据库连接与 DAO 容器
    db_conn = DatabaseConnection()
    repository = ArticleRepository(db_conn)

    # 实例化并展示主窗口
    window = MainWindow(repository)
    window.show()

    logger.info("ReadPaper 生产级应用系统启动完毕。")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()