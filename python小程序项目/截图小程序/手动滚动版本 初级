import sys
import io
from PIL import Image, ImageChops
from PySide2.QtCore import Qt, QRect, QPoint, QSettings, QTimer, Signal
from PySide2.QtGui import QPainter, QPen, QColor, QScreen, QGuiApplication, QImage, QPixmap
from PySide2.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QCheckBox, QLabel, QSpinBox, QMessageBox)

class ScreenshotOverlay(QWidget):
    """矩形选区划定遮罩层（仅用于第一步划定区域）"""
    def __init__(self, mode="rect", enable_border=False, border_width=2, enable_shadow=True, callback=None):
        super().__init__()
        # 使用整型或标准的枚举组合，避免 PySide2 的 DeprecationWarning
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        screen = QGuiApplication.primaryScreen()
        self.pixmap = screen.grabWindow(0)
        self.resize(self.pixmap.size())
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False

        self.mode = mode
        self.callback = callback

        self.enable_border = enable_border
        self.border_width = border_width
        self.enable_shadow = enable_shadow

        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if not self.start_point.isNull() and not self.end_point.isNull():
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawPixmap(rect, self.pixmap, rect)
            
            border_color = QColor(0, 120, 215) if self.mode == "rect" else QColor(0, 200, 100)
            pen = QPen(border_color, 1 if self.mode == "rect" else 2, Qt.DashLine if self.mode == "rect" else Qt.SolidLine)
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
            rect = QRect(self.start_point, self.end_point).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.close()
                if self.callback:
                    self.callback(rect, self.pixmap)
            else:
                self.close()
                if hasattr(self, 'parent_panel') and self.parent_panel:
                    self.parent_panel.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            if hasattr(self, 'parent_panel') and self.parent_panel:
                self.parent_panel.show()


class PersistentBorderWindow(QWidget):
    """极其轻量的常驻边框窗口：只在选区四周画绿线，绝不挡住鼠标穿透滚动"""
    def __init__(self, rect):
        super().__init__()
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 完美穿透鼠标
        
        self.setGeometry(rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(0, 200, 100), 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # 减去 1 像素防止边框被窗口边界切掉
        draw_rect = self.rect().adjusted(0, 0, -1, -1)
        painter.drawRect(draw_rect)


class ManualScrollControlWindow(QWidget):
    """手动滚动截图控制悬浮条"""
    capture_frame_signal = Signal()
    finish_signal = Signal()
    cancel_signal = Signal()

    def __init__(self, count=0):
        super().__init__()
        self.setWindowFlags(Qt.WindowType(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool))
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)

        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 240);
                border-radius: 8px;
                border: 1px solid #666;
            }
            QLabel {
                color: #00FFCC;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0086F8;
            }
            QPushButton#finish_btn {
                background-color: #107C10;
            }
            QPushButton#finish_btn:hover {
                background-color: #169816;
            }
            QPushButton#cancel_btn {
                background-color: #D83B01;
            }
            QPushButton#cancel_btn:hover {
                background-color: #EA4300;
            }
        """)
        
        box_layout = QHBoxLayout(container)
        box_layout.setContentsMargins(10, 6, 10, 6)

        self.label = QLabel(f"已截取: {count} 张")
        box_layout.addWidget(self.label)

        self.btn_capture = QPushButton("截取当前帧")
        self.btn_capture.clicked.connect(self.capture_frame_signal.emit)
        box_layout.addWidget(self.btn_capture)

        self.btn_finish = QPushButton("停止并拼接")
        self.btn_finish.setObjectName("finish_btn")
        self.btn_finish.clicked.connect(self.finish_signal.emit)
        box_layout.addWidget(self.btn_finish)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("cancel_btn")
        self.btn_cancel.clicked.connect(self.cancel_signal.emit)
        box_layout.addWidget(self.btn_cancel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        screen = QGuiApplication.primaryScreen().geometry()
        self.adjustSize()
        self.move((screen.width() - self.width()) // 2, 30)

    def update_count(self, count):
        self.label.setText(f"已截取: {count} 张")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_signal.emit()


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麒麟截图工具 (手动滚动版)")
        self.resize(300, 210)
        
        self.settings = QSettings("KylinTools", "ScreenShotApp")
        self.corner_radius = 8  # 修复圆角属性缺失的问题

        layout = QVBoxLayout()
        self.lbl_status = QLabel("状态: 就绪")
        self.lbl_status.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        layout.addWidget(QLabel("配置选项："))

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

        self.chk_shadow = QCheckBox("启用阴影效果")
        layout.addWidget(self.chk_shadow)

        self.btn_capture = QPushButton("开始矩形截图")
        self.btn_capture.clicked.connect(self.start_screenshot)
        layout.addWidget(self.btn_capture)

        self.btn_manual_scroll = QPushButton("手动滚动截图")
        self.btn_manual_scroll.clicked.connect(self.start_manual_scroll_screenshot)
        layout.addWidget(self.btn_manual_scroll)

        self.setLayout(layout)
        
        self.load_settings()
        self.screenshot_overlay = None
        self.border_window = None
        self.float_window = None
        
        self.manual_rect = None
        self.manual_screenshots = []

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
        self.hide()
        QApplication.processEvents()
        QApplication.processEvents()
        QTimer.singleShot(300, lambda: self._show_overlay(mode="rect"))

    def start_manual_scroll_screenshot(self):
        self.save_settings()
        self.manual_screenshots.clear()
        self.hide()
        QApplication.processEvents()
        QApplication.processEvents()
        QTimer.singleShot(300, lambda: self._show_overlay(mode="manual_scroll"))

    def _show_overlay(self, mode):
        callback = self.process_rect_result if mode == "rect" else self.on_manual_scroll_region_selected
        self.screenshot_overlay = ScreenshotOverlay(
            mode=mode,
            enable_border=self.chk_border.isChecked(),
            border_width=self.spin_width.value(),
            enable_shadow=self.chk_shadow.isChecked(),
            callback=callback
        )
        self.screenshot_overlay.parent_panel = self
        self.screenshot_overlay.show()

    def process_rect_result(self, rect, pixmap):
        cropped = pixmap.copy(rect)
        self.finalize_and_copy(cropped)
        self.lbl_status.setText("状态: 矩形截图已完成并复制！")
        self.show()

    def on_manual_scroll_region_selected(self, rect, pixmap):
        self.manual_rect = rect
        self.manual_screenshots.clear()

        # 1. 自动截取第一张
        first_img = self.grab_region_image(pixmap, rect)
        self.manual_screenshots.append(first_img)

        self.lbl_status.setText("状态: 手动滚动截图中...")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")

        # 2. 弹出轻量边框窗口（精准匹配选区且完美穿透鼠标）
        self.border_window = PersistentBorderWindow(rect)
        self.border_window.show()

        # 3. 弹出控制悬浮条
        self.float_window = ManualScrollControlWindow(count=len(self.manual_screenshots))
        self.float_window.capture_frame_signal.connect(self.on_capture_next_frame)
        self.float_window.finish_signal.connect(self.on_finish_manual_scroll)
        self.float_window.cancel_signal.connect(self.on_cancel_manual_scroll)
        self.float_window.show()

    def grab_region_image(self, pixmap, rect):
        cropped_pixmap = pixmap.copy(rect)
        qimage = cropped_pixmap.toImage().convertToFormat(QImage.Format_RGB888)
        img_bytes = bytes(qimage.constBits())
        pil_img = Image.frombytes(
            "RGB", 
            (qimage.width(), qimage.height()), 
            img_bytes, 
            "raw", 
            "RGB", 
            qimage.bytesPerLine()
        )
        return pil_img

    def on_capture_next_frame(self):
        screen = QGuiApplication.primaryScreen()
        full_pixmap = screen.grabWindow(0)
        new_img = self.grab_region_image(full_pixmap, self.manual_rect)
        
        self.manual_screenshots.append(new_img)
        if self.float_window:
            self.float_window.update_count(len(self.manual_screenshots))

    def on_cancel_manual_scroll(self):
        if self.border_window:
            self.border_window.close()
            self.border_window = None
        if self.float_window:
            self.float_window.close()
            self.float_window = None
        self.manual_screenshots.clear()
        self.lbl_status.setText("状态: 手动滚动截图已取消")
        self.lbl_status.setStyleSheet("color: blue; font-weight: bold;")
        self.show()

    def on_finish_manual_scroll(self):
        if self.border_window:
            self.border_window.close()
            self.border_window = None
        if self.float_window:
            self.float_window.close()
            self.float_window = None

        if not self.manual_screenshots:
            self.lbl_status.setText("状态: 未采集到有效内容")
            self.lbl_status.setStyleSheet("color: orange; font-weight: bold;")
            self.show()
            return

        # 优化后的精确拼接逻辑
        final_pieces = [self.manual_screenshots[0]]
        for i in range(1, len(self.manual_screenshots)):
            prev_img = self.manual_screenshots[i - 1]
            curr_img = self.manual_screenshots[i]
            
            # 寻找最佳重叠偏移量（剔除重复像素）
            best_offset = self.find_best_overlap(prev_img, curr_img)
            
            if best_offset > 0 and best_offset < curr_img.height:
                # 裁剪掉当前帧与上一帧重复的顶部像素
                cropped_curr = curr_img.crop((0, best_offset, curr_img.width, curr_img.height))
                final_pieces.append(cropped_curr)
            else:
                final_pieces.append(curr_img)

        max_width = self.manual_rect.width()
        total_height = sum(img.height for img in final_pieces)
        stitched_img = Image.new('RGB', (max_width, total_height))
        current_y = 0
        for img in final_pieces:
            stitched_img.paste(img, (0, current_y))
            current_y += img.height
        
        buffer = io.BytesIO()
        stitched_img.save(buffer, format="PNG")
        q_img = QImage()
        q_img.loadFromData(buffer.getvalue())
        pixmap_result = QPixmap.fromImage(q_img)
        
        self.finalize_and_copy(pixmap_result)
        
        self.lbl_status.setText("状态: 手动滚动长图已完成并复制！")
        self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
        self.show()
        QMessageBox.information(self, "提示", "手动滚动长图已成功拼合并复制到剪贴板！")

    def find_best_overlap(self, img1, img2):
        """利用 SAD（绝对差值和）算法精确计算两张图的重叠行数，彻底消除重复像素"""
        w, h1 = img1.width, img1.height
        h2 = img2.height
        
        # 转换为灰度图以加快计算并提高鲁棒性
        g1 = img1.convert("L")
        g2 = img2.convert("L")
        
        # 取上一图底部的一部分作为模板（例如底部 30 像素）
        sample_h = min(30, h1)
        template = g1.crop((0, h1 - sample_h, w, h1))
        
        # 在下一图的顶部区域（比如前 80% 的高度范围内）搜索匹配位置
        search_max = int(h2 * 0.8)
        if search_max < sample_h:
            return 0
            
        min_sad = float('inf')
        best_y = 0
        
        # 逐行滑动对比计算绝对差值和 (SAD)
        for y in range(0, search_max - sample_h):
            target = g2.crop((0, y, w, y + sample_h))
            diff = ImageChops.difference(template, target)
            
            # 获取当前偏移下的像素差异总和
            extrema = diff.getextrema()
            # 简便起见，利用像素直方图或直接求和判断相似度
            # 这里通过计算差值图像的绝对能量和
            sad = sum(diff.histogram()) # 或者是更精确的像素均值
            
            # 使用更标准的 SAD 计算差值
            # 优化：直接用像素绝对值累加
            diff_data = list(diff.getdata())
            current_sad = sum(diff_data)
            
            if current_sad < min_sad:
                min_sad = current_sad
                best_y = y

        # 如果最小误差在合理范围内，说明找到了真正的重复重叠区
        # 这里的 sample_h 加上 best_y 即为上一张图中与下一张图重合的起始行在下一图中的对应位置
        # 换句话说，下一图需要向下切掉前 (best_y + sample_h) 或者根据匹配点裁剪
        # 我们的目标是把下一图中与上一图重复的部分切掉
        return best_y + sample_h if min_sad < (w * sample_h * 255 * 0.1) else 0

    def find_best_overlap(self, img1, img2):
        h1, h2 = img1.height, img2.height
        search_max = int(h2 * 0.8)
        if search_max < 5:
            return 0
        
        best_y = 0
        min_diff_val = float('inf')
        strip_h = min(20, h1)
        strip1 = img1.crop((0, h1 - strip_h, img1.width, h1))
        
        for y in range(0, search_max - strip_h):
            strip2 = img2.crop((0, y, img2.width, y + strip_h))
            diff_ext = ImageChops.difference(strip1, strip2).convert("L").getextrema()
            total_diff = diff_ext[1]
            if total_diff < min_diff_val:
                min_diff_val = total_diff
                best_y = y

        return best_y if min_diff_val < 80 else int(h2 * 0.25)

    def finalize_and_copy(self, cropped):
        if self.chk_border.isChecked():
            p_border = QPainter(cropped)
            p_border.setRenderHint(QPainter.Antialiasing, True)
            w = self.spin_width.value()
            pen = QPen(QColor(255, 0, 0), w)
            p_border.setPen(pen)
            p_border.setBrush(Qt.NoBrush)
            draw_rect = cropped.rect().adjusted(w // 2, w // 2, -w // 2, -w // 2)
            p_border.drawRect(draw_rect)
            p_border.end()

        if self.chk_shadow.isChecked():
            shadow_margin = 16  
            offset_x = 4        
            offset_y = 4        
            
            new_width = cropped.width() + shadow_margin + offset_x
            new_height = cropped.height() + shadow_margin + offset_y
            final_image = QImage(new_width, new_height, QImage.Format_ARGB32)
            final_image.fill(Qt.transparent)  
            
            painter = QPainter(final_image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
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
            
            painter.drawImage(2, 2, cropped.toImage())
            painter.end()
            
            clipboard = QGuiApplication.clipboard()
            clipboard.setImage(final_image)
        else:
            clipboard = QGuiApplication.clipboard()
            clipboard.setImage(cropped.toImage())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())
