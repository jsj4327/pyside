from PySide2.QtCore import Qt, QRect, QTimer
from PySide2.QtGui import QImage, QPixmap, QKeySequence
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QCheckBox, QLabel, QSpinBox, QMessageBox, QShortcut, QApplication)

from config import AppConfig
from core.capturer import ScreenCapturer
from core.stitcher import ImageStitcher
from core.clipboard import ClipboardManager
from ui.overlay import ScreenshotOverlay
from ui.border_window import PersistentBorderWindow
from ui.float_toolbar import ManualScrollControlWindow
from ui.editor_window import ScreenshotEditorWindow

class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麒麟截图工具 (模块化版)")
        self.resize(300, 250)
        
        self.config = AppConfig()
        self.corner_radius = 8

        layout = QVBoxLayout()
        self.lbl_status = QLabel("状态: 就绪")
        self.lbl_status.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        layout.addWidget(QLabel("配置选项："))

        # 描边配置
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

        # 阴影配置
        self.chk_shadow = QCheckBox("启用阴影效果")
        layout.addWidget(self.chk_shadow)

        # 新增：标注开关配置
        self.chk_editor = QCheckBox("启用截图标注")
        layout.addWidget(self.chk_editor)

        # 功能触发按钮
        self.btn_capture = QPushButton("开始矩形截图 (Ctrl+Shift+S)")
        self.btn_capture.clicked.connect(self.start_screenshot)
        layout.addWidget(self.btn_capture)

        self.btn_manual_scroll = QPushButton("手动滚动截图 (Ctrl+Alt+S)")
        self.btn_manual_scroll.clicked.connect(self.start_manual_scroll_screenshot)
        layout.addWidget(self.btn_manual_scroll)

        self.setLayout(layout)
        
        self.load_settings()
        self.register_shortcuts()
        
        self.screenshot_overlay = None
        self.border_window = None
        self.float_window = None
        self.editor_window = None
        
        self.manual_rect = None
        self.manual_screenshots = []

    def register_shortcuts(self):
        """注册应用级快捷键"""
        self.shortcut_rect = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.shortcut_rect.setContext(Qt.ApplicationShortcut)
        self.shortcut_rect.activated.connect(self.start_screenshot)

        self.shortcut_scroll = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self.shortcut_scroll.setContext(Qt.ApplicationShortcut)
        self.shortcut_scroll.activated.connect(self.start_manual_scroll_screenshot)

    def load_settings(self):
        self.chk_border.setChecked(self.config.get_use_border())
        self.spin_width.setValue(self.config.get_border_width())
        self.spin_width.setEnabled(self.config.get_use_border())
        self.chk_shadow.setChecked(self.config.get_use_shadow())
        self.chk_editor.setChecked(self.config.get_use_editor())

    def save_settings(self):
        self.config.set_use_border(self.chk_border.isChecked())
        self.config.set_border_width(self.spin_width.value())
        self.config.set_use_shadow(self.chk_shadow.isChecked())
        self.config.set_use_editor(self.chk_editor.isChecked())

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
        self.handle_capture_result(cropped)

    def on_manual_scroll_region_selected(self, rect, pixmap):
        self.manual_rect = rect
        self.manual_screenshots.clear()

        first_img = ImageStitcher.grab_region_image(pixmap, rect)
        self.manual_screenshots.append(first_img)

        self.lbl_status.setText("状态: 手动滚动截图中...")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")

        self.border_window = PersistentBorderWindow(rect)
        self.border_window.show()

        self.float_window = ManualScrollControlWindow(count=len(self.manual_screenshots))
        self.float_window.capture_frame_signal.connect(self.on_capture_next_frame)
        self.float_window.finish_signal.connect(self.on_finish_manual_scroll)
        self.float_window.cancel_signal.connect(self.on_cancel_manual_scroll)
        self.float_window.show()

    def on_capture_next_frame(self):
        full_pixmap = ScreenCapturer.grab_fullscreen()
        new_img = ImageStitcher.grab_region_image(full_pixmap, self.manual_rect)
        
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

        final_pieces = [self.manual_screenshots[0]]
        for i in range(1, len(self.manual_screenshots)):
            prev_img = self.manual_screenshots[i - 1]
            curr_img = self.manual_screenshots[i]
            
            best_offset = ImageStitcher.find_best_overlap(prev_img, curr_img)
            
            if best_offset > 0 and best_offset < curr_img.height:
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
        
        import io
        buffer = io.BytesIO()
        stitched_img.save(buffer, format="PNG")
        q_img = QImage()
        q_img.loadFromData(buffer.getvalue())
        pixmap_result = QPixmap.fromImage(q_img)
        
        self.handle_capture_result(pixmap_result)

    def handle_capture_result(self, pixmap):
        """根据勾选框状态决定是直接保存还是进入编辑器"""
        if self.chk_editor.isChecked():
            # 开启了标注：弹出编辑器
            self.editor_window = ScreenshotEditorWindow(pixmap=pixmap, callback=self.on_editing_finished)
            self.editor_window.show()
            self.lbl_status.setText("状态: 正在编辑截图...")
        else:
            # 未开启标注：直接执行默认逻辑（描边、阴影、复制、本地缓存）
            self.finalize_and_copy(pixmap)
            self.lbl_status.setText("状态: 截图已完成并复制！")
            self.show()

    def on_editing_finished(self, edited_pixmap):
        """编辑完成后执行边框、阴影渲染并写入剪贴板与历史缓存"""
        self.finalize_and_copy(edited_pixmap)
        self.lbl_status.setText("状态: 截图已编辑并成功复制！")
        self.show()

    def finalize_and_copy(self, cropped):
        result_image = ImageStitcher.apply_border_and_shadow(
            cropped=cropped,
            use_border=self.chk_border.isChecked(),
            border_width=self.spin_width.value(),
            use_shadow=self.chk_shadow.isChecked(),
            corner_radius=self.corner_radius
        )
        saved_path = ClipboardManager.save_and_copy(result_image)
        print(f"截图已自动复制并持久化到本地: {saved_path}")