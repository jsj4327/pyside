import sys
from PySide2.QtCore import Qt, QRect, QPoint, QSettings, QTimer
from PySide2.QtGui import QPainter, QPen, QColor, QScreen, QGuiApplication, QImage
from PySide2.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QCheckBox, 
                               QLabel, QSpinBox)

class ScreenshotOverlay(QWidget):
    def __init__(self, enable_border=False, border_width=2, enable_shadow=True):
        super().__init__()
        # 设置无边框、置顶、全屏
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # 获取全屏图像（此时控制面板已完全消失，不会被截进去）
        screen = QGuiApplication.primaryScreen()
        self.pixmap = screen.grabWindow(0)
        self.resize(self.pixmap.size())
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False

        # 配置项
        self.enable_border = enable_border
        self.border_width = border_width
        self.border_color = QColor(255, 0, 0) # 默认红色描边
        self.enable_shadow = enable_shadow   # 阴影开关
        self.corner_radius = 8               # 阴影的圆角半径大小

        # 设置鼠标样式为十字
        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        # 1. 绘制全屏截图
        painter.drawPixmap(0, 0, self.pixmap)
        # 2. 绘制半透明黑色遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # 3. 如果正在框选，高亮显示选中的区域
        if not self.start_point.isNull() and not self.end_point.isNull():
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawPixmap(rect, self.pixmap, rect)
            
            # 绘制选框的蓝色引导边框
            pen = QPen(QColor(0, 120, 215), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.process_screenshot()

    def process_screenshot(self):
        rect = QRect(self.start_point, self.end_point).normalized()
        if rect.width() > 5 and rect.height() > 5:
            # 1. 裁剪选中区域原图（保持尖角）
            cropped = self.pixmap.copy(rect)

            # 2. 如果开启了描边，直接在尖角原图上绘制边框
            if self.enable_border:
                p_border = QPainter(cropped)
                p_border.setRenderHint(QPainter.Antialiasing, True)
                pen = QPen(self.border_color, self.border_width)
                p_border.setPen(pen)
                p_border.setBrush(Qt.NoBrush)
                draw_rect = cropped.rect().adjusted(
                    self.border_width // 2, 
                    self.border_width // 2, 
                    -self.border_width // 2, 
                    -self.border_width // 2
                )
                p_border.drawRect(draw_rect)
                p_border.end()

            # 3. 如果开启了阴影（阴影带有圆角效果，尖角原图保持原样贴在中央）
            if self.enable_shadow:
                shadow_margin = 16  
                offset_x = 4        
                offset_y = 4        
                
                new_width = cropped.width() + shadow_margin + offset_x
                new_height = cropped.height() + shadow_margin + offset_y
                final_image = QImage(new_width, new_height, QImage.Format_ARGB32)
                final_image.fill(Qt.transparent)  
                
                painter = QPainter(final_image)
                painter.setRenderHint(QPainter.Antialiasing, True)
                
                # 多层渐变绘制右下方偏移的圆角柔和阴影
                for i in range(shadow_margin, 0, -1):
                    alpha = int(35 * (1.0 - i / shadow_margin))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(0, 0, 0, alpha))
                    
                    shadow_rect = QRect(
                        2 + offset_x,             
                        2 + offset_y,             
                        cropped.width() + i,      
                        cropped.height() + i      
                    )
                    painter.drawRoundedRect(shadow_rect, self.corner_radius, self.corner_radius)
                
                # 将尖角的原图（含描边）直接贴在阴影画布的指定位置
                painter.drawImage(2, 2, cropped.toImage())
                painter.end()
                
                clipboard = QGuiApplication.clipboard()
                clipboard.setImage(final_image)
            else:
                clipboard = QGuiApplication.clipboard()
                clipboard.setImage(cropped.toImage())
            
        self.close()
        if hasattr(self, 'parent_panel') and self.parent_panel:
            self.parent_panel.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            if hasattr(self, 'parent_panel') and self.parent_panel:
                self.parent_panel.show()


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麒麟截图工具")
        self.resize(300, 160)
        
        self.settings = QSettings("KylinTools", "ScreenShotApp")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("配置选项："))

        # 描边设置栏
        border_layout = QHBoxLayout()
        self.chk_border = QCheckBox("启用描边")
        self.chk_border.stateChanged.connect(lambda s: self.spin_width.setEnabled(s == Qt.Checked))
        border_layout.addWidget(self.chk_border)

        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 10)
        self.spin_width.setValue(2)
        self.spin_width.setEnabled(False)
        border_layout.addWidget(QLabel("宽度:"))
        border_layout.addWidget(self.spin_width)
        layout.addLayout(border_layout)

        # 阴影设置栏（可选，默认选中）
        self.chk_shadow = QCheckBox("启用阴影效果")
        layout.addWidget(self.chk_shadow)

        # 截图触发按钮
        self.btn_capture = QPushButton("开始矩形截图")
        self.btn_capture.clicked.connect(self.start_screenshot)
        layout.addWidget(self.btn_capture)

        self.setLayout(layout)
        
        self.load_settings()
        self.screenshot_overlay = None

    def load_settings(self):
        use_border = self.settings.value("use_border", False, type=bool)
        border_width = self.settings.value("border_width", 2, type=int)
        use_shadow = self.settings.value("use_shadow", True, type=bool)

        self.chk_border.setChecked(use_border)
        self.spin_width.setValue(border_width)
        self.spin_width.setEnabled(use_border)
        self.chk_shadow.setChecked(use_shadow)

    def save_settings(self):
        self.settings.setValue("use_border", self.chk_border.isChecked())
        self.settings.setValue("border_width", self.spin_width.value())
        self.settings.setValue("use_shadow", self.chk_shadow.isChecked())

    def start_screenshot(self):
        self.save_settings()
        
        # 1. 隐藏窗体
        self.hide()
        # 2. 连续两次处理事件队列，强制把窗口隐藏指令彻底推送到 X11 窗口管理器并完成画面刷新
        QApplication.processEvents()
        QApplication.processEvents()
        
        # 3. 将延迟由 150ms 增加到 300ms，确保完全消失后再抓取全屏
        QTimer.singleShot(300, self._show_overlay)

    def _show_overlay(self):
        self.screenshot_overlay = ScreenshotOverlay(
            enable_border=self.chk_border.isChecked(),
            border_width=self.spin_width.value(),
            enable_shadow=self.chk_shadow.isChecked()
        )
        self.screenshot_overlay.parent_panel = self
        self.screenshot_overlay.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_()) 
