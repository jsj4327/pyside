"""
PDF 异步加载工作线程 (PDF Loader Worker)
在后台线程中执行 PDF 解析与多线程渲染，确保 UI 界面不卡顿。
"""
from PySide2.QtCore import QThread, Signal
from services.pdf_service import load_pdf_images


class PdfLoaderWorker(QThread):
    """异步加载 PDF 的工作线程"""
    
    # 定义成功和失败信号
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, pdf_path: str, dpi: int, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.dpi = dpi

    def run(self):
        """线程执行入口"""
        try:
            # 调用高性能多线程加载服务
            images = load_pdf_images(self.pdf_path, self.dpi)
            self.finished.emit(images)
        except Exception as e:
            self.error.emit(str(e))