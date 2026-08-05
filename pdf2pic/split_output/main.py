"""
应用程序入口点
初始化 QApplication，配置高DPI支持、全局样式、命令行参数解析及异常处理。
"""
import sys
import os
import traceback
import logging
from logging.handlers import RotatingFileHandler

from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2.QtCore import Qt

from main_window import Pdf2PicViewer

APP_NAME = "PDF2Pic Viewer"
LOG_FILE = "pdf2pic.log"


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        logger.warning(f"无法创建日志文件 {LOG_FILE}，仅使用控制台输出")
    
    return logger


def global_exception_hook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical(f"未捕获的异常:\n{error_msg}")
    
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None,
                "程序错误",
                f"发生未预期的错误，详情已记录到日志：\n\n{str(exc_value)}"
            )
    except Exception:
        pass


def main():
    logger = setup_logging()
    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # 全局禁用 Kylin OS 原生对话框，防止 Peony/UKUI 组件析构崩溃
    if hasattr(QApplication, "DontUseNativeDialogs"):
        app.setOption(QApplication.DontUseNativeDialogs, True)
    
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("PdfTools")
    app.setApplicationVersion("1.5.4")
    
    sys.excepthook = global_exception_hook
    
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    logger.info(f"{APP_NAME} v{app.applicationVersion()} 启动")
    
    initial_pdf = None
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if os.path.isfile(candidate) and candidate.lower().endswith(".pdf"):
            initial_pdf = os.path.abspath(candidate)
            logger.info(f"通过命令行加载文件: {initial_pdf}")
        else:
            logger.warning(f"命令行参数不是有效的PDF文件: {candidate}")
    
    viewer = Pdf2PicViewer()
    
    if initial_pdf:
        try:
            if hasattr(viewer, 'load_pdf_from_path'):
                viewer.load_pdf_from_path(initial_pdf)
            elif hasattr(viewer, 'open_pdf'):
                logger.info("使用兼容模式加载PDF")
                viewer.open_pdf(initial_pdf)
            else:
                logger.error("主窗口缺少PDF加载方法")
        except TypeError:
            logger.warning("当前版本不支持静默加载，请手动打开文件")
        except Exception as e:
            logger.error(f"自动加载PDF失败: {e}")
            QMessageBox.warning(
                viewer, "加载失败", 
                f"无法打开文件:\n{initial_pdf}\n\n{str(e)}"
            )
    
    viewer.show()
    exit_code = app.exec_()
    
    try:
        viewer.close()
        viewer.deleteLater()
        app.processEvents()
    except RuntimeError:
        pass
    except Exception:
        pass
    
    logger.info(f"应用程序退出，代码: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()