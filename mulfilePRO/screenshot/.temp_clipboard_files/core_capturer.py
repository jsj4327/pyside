from PySide2.QtGui import QGuiApplication, QPixmap

class ScreenCapturer:
    """屏幕抓取核心类，负责安全获取全屏图像"""
    
    @staticmethod
    def grab_fullscreen() -> QPixmap:
        """获取当前主屏幕或全景屏幕图像"""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            raise RuntimeError("无法获取主屏幕实例")
        # 抓取整个屏幕 (0 表示整个桌面根窗口)
        return screen.grabWindow(0)