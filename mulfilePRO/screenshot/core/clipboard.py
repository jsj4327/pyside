import os
import time
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QImage, QPixmap

class ClipboardManager:
    """负责剪贴板写入与本地历史图像缓存管理"""
    
    CACHE_DIR = os.path.expanduser("~/.cache/kylin_screenshot_history")

    @classmethod
    def initialize(cls):
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR, exist_ok=True)

    @classmethod
    def save_and_copy(cls, image: QImage) -> str:
        """将图像写入系统剪贴板，并自动持久化到本地历史目录"""
        cls.initialize()
        
        # 1. 写入系统剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setImage(image)

        # 2. 保存到本地历史文件夹
        timestamp = int(time.time() * 1000)
        file_path = os.path.join(cls.CACHE_DIR, f"shot_{timestamp}.png")
        image.save(file_path, "PNG")
        
        return file_path