import sys
import os
import re
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, 
                             QFileDialog, QLabel, QSplitter, QMessageBox, QMenu, 
                             QScrollArea)
from PySide2.QtCore import Qt, QSize, QPoint
from PySide2.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QWheelEvent, QMouseEvent
from PIL import Image

class ZoomableScrollArea(QScrollArea):
    """支持滚轮缩放、边界限制及鼠标左键拖拽平移的图片预览滚动区域"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_label = QLabel("在此处预览大图")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; color: #666;")
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        
        self.original_pixmap = QPixmap()
        self.scale_factor = 1.0
        self.min_scale = 0.2  # 最小缩放比例（20%）
        self.max_scale = 5.0  # 最大缩放比例（500%）
        
        # 拖拽平移相关变量
        self.is_dragging = False
        self.drag_start_pos = QPoint()

    def set_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.update_image_display()

    def update_image_display(self):
        if self.original_pixmap.isNull():
            return
        
        # 根据当前缩放系数计算新的尺寸
        new_width = int(self.original_pixmap.width() * self.scale_factor)
        new_height = int(self.original_pixmap.height() * self.scale_factor)
        
        scaled_pixmap = self.original_pixmap.scaled(
            new_width, new_height, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def wheelEvent(self, event: QWheelEvent):
        if self.original_pixmap.isNull():
            return
        
        # 获取滚轮滚动方向
        angle = event.angleDelta().y()
        if angle == 0:
            return

        # 计算缩放步长
        factor = 1.15 if angle > 0 else 1. / 1.15
        new_scale = self.scale_factor * factor

        # 严格限制缩放比例在 min_scale 和 max_scale 之间
        if new_scale < self.min_scale:
            new_scale = self.min_scale
        elif new_scale > self.max_scale:
            new_scale = self.max_scale

        if new_scale != self.scale_factor:
            self.scale_factor = new_scale
            self.update_image_display()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and not self.original_pixmap.isNull():
            self.is_dragging = True
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and not self.original_pixmap.isNull():
            delta = event.pos() - self.drag_start_pos
            self.drag_start_pos = event.pos()
            
            # 调整滚动条位置实现平移
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class StrictOrderListWidget(QListWidget):
    """自定义的 QListWidget，严格锁定单列纵向拖放，支持多选"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ListMode)
        self.setFlow(QListWidget.TopToBottom)
        self.setMovement(QListWidget.Free)
        
        self.setIconSize(QSize(100, 100))
        self.setSpacing(5)
        
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDropIndicatorShown(False)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        
        self.dragging_row = -1
        self.drop_indicator_row = -1

    def startDrag(self, supportedActions):
        selected = self.selectedItems()
        if selected:
            self.dragging_row = self.row(selected[0])
            
        super().startDrag(supportedActions)
        self.dragging_row = -1
        self.drop_indicator_row = -1
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self:
            pos = event.pos()
            scroll_margin = 30
            scrollbar = self.verticalScrollBar()
            if pos.y() < scroll_margin:
                scrollbar.setValue(scrollbar.value() - 15)
            elif pos.y() > self.viewport().height() - scroll_margin:
                scrollbar.setValue(scrollbar.value() + 15)

            constrained_x = self.viewport().width() // 2
            constrained_pos = pos
            constrained_pos.setX(constrained_x)

            item = self.itemAt(constrained_pos)
            if item:
                rect = self.visualItemRect(item)
                relative_y = constrained_pos.y() - rect.top()
                
                if rect.height() * 0.3 <= relative_y <= rect.height() * 0.7:
                    self.drop_indicator_row = -1
                    event.ignore()
                    self.viewport().update()
                    return
                
                row = self.row(item)
                if relative_y < rect.height() * 0.3:
                    self.drop_indicator_row = row
                else:
                    self.drop_indicator_row = row + 1
            else:
                if constrained_pos.y() < 0:
                    self.drop_indicator_row = 0
                else:
                    self.drop_indicator_row = self.count()

            event.acceptProposedAction()
            self.viewport().update()
        else:
            event.ignore()

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.dragging_row != -1:
            self.viewport().update()

    def dragLeaveEvent(self, event):
        self.drop_indicator_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.source() == self:
            target_row = self.drop_indicator_row
            selected_items = self.selectedItems()
            if not selected_items:
                event.ignore()
                return
            
            source_item = selected_items[0]
            source_row = self.row(source_item)
            
            if target_row == -1:
                event.ignore()
                return

            if source_row < target_row:
                target_row -= 1

            taken_item = self.takeItem(source_row)
            self.insertItem(target_row, taken_item)
            
            self.setCurrentItem(taken_item)
            self.dragging_row = -1
            self.drop_indicator_row = -1
            
            event.accept()
            self.clearSelection()
            self.viewport().update()
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dragging_row != -1 and self.dragging_row < self.count():
            item = self.item(self.dragging_row)
            rect = self.visualItemRect(item)
            if rect.isValid():
                painter = QPainter(self.viewport())
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.fillRect(rect, QColor(255, 255, 255, 160))
                painter.end()

        if self.drop_indicator_row != -1:
            painter = QPainter(self.viewport())
            pen = QPen(QColor(0, 120, 215), 3, Qt.SolidLine)
            painter.setPen(pen)
            
            y_pos = 0
            if self.drop_indicator_row < self.count():
                item = self.item(self.drop_indicator_row)
                rect = self.visualItemRect(item)
                if rect.isValid():
                    y_pos = rect.top() - 3
            else:
                if self.count() > 0:
                    last_item = self.item(self.count() - 1)
                    rect = self.visualItemRect(last_item)
                    if rect.isValid():
                        y_pos = rect.bottom() + 3
            
            if y_pos != 0:
                painter.drawLine(10, y_pos, self.viewport().width() - 10, y_pos)
            painter.end()


class ThumbnailViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pic2pdf - 图片转 PDF 工具")
        
        # 屏幕分辨率的 80% 居中显示（不包含底部任务栏）
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = int(screen.width() * 0.8)
        window_height = int(screen.height() * 0.8)
        
        self.resize(window_width, window_height)
        center_x = screen.x() + (screen.width() - window_width) // 2
        center_y = screen.y() + (screen.height() - window_height) // 2
        self.move(center_x, center_y)

        self.current_folder_path = ""
        self.init_ui(window_width)

    def init_ui(self, window_width):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 1. 顶部工具栏：将所有按钮全部放置在同一行
        top_bar_layout = QHBoxLayout()
        
        self.btn_open_folder = QPushButton("📁 打开文件夹")
        self.btn_open_folder.setStyleSheet("font-weight: bold;")
        self.btn_open_folder.clicked.connect(self.open_folder)
        top_bar_layout.addWidget(self.btn_open_folder)

        self.btn_move_up = QPushButton("⬆️ 上移")
        self.btn_move_up.clicked.connect(self.move_item_up)
        top_bar_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("⬇️ 下移")
        self.btn_move_down.clicked.connect(self.move_item_down)
        top_bar_layout.addWidget(self.btn_move_down)

        self.btn_remove_item = QPushButton("❌ 移除")
        self.btn_remove_item.clicked.connect(self.remove_selected_items)
        top_bar_layout.addWidget(self.btn_remove_item)

        self.btn_clear_list = QPushButton("🗑️ 清空")
        self.btn_clear_list.clicked.connect(self.clear_all_items)
        top_bar_layout.addWidget(self.btn_clear_list)

        self.btn_export_pdf = QPushButton("✨ 导出为 PDF")
        self.btn_export_pdf.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        top_bar_layout.addWidget(self.btn_export_pdf)

        main_layout.addLayout(top_bar_layout)

        # 2. 中间分栏（左侧缩略图，右侧带缩放平移的大图预览）
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # 左侧：缩略图列表
        self.thumbnail_list = StrictOrderListWidget()
        self.thumbnail_list.itemClicked.connect(self.show_large_image)
        self.thumbnail_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.thumbnail_list.customContextMenuRequested.connect(self.show_context_menu)
        splitter.addWidget(self.thumbnail_list)

        # 右侧：封装好的支持缩放和平移的滚动区域
        self.image_scroll_area = ZoomableScrollArea()
        splitter.addWidget(self.image_scroll_area)

        # 设置默认宽度比例：左侧窄（200像素），右侧宽
        splitter.setSizes([200, window_width - 200])

        # 3. 底部状态栏标签
        self.status_label = QLabel("就绪：请点击上方“打开文件夹”按钮")
        self.status_label.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder_path:
            return
            
        self.current_folder_path = folder_path
        self.thumbnail_list.clear()
        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()

        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        file_names = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
        
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
            
        file_names.sort(key=natural_sort_key)

        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(QIcon(scaled_pixmap), file_name)
                item.setSizeHint(QSize(120, 110))
                self.thumbnail_list.addItem(item)
                
        self.status_label.setText(f"已加载文件夹: {folder_path} (共 {len(file_names)} 张图片)")

    def show_large_image(self, item):
        if self.current_folder_path:
            file_path = os.path.join(self.current_folder_path, item.text())
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.image_scroll_area.set_pixmap(pixmap)

    def move_item_up(self):
        """将选中的项往上移动一位"""
        row = self.thumbnail_list.currentRow()
        if row > 0:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row - 1, item)
            self.thumbnail_list.setCurrentRow(row - 1)

    def move_item_down(self):
        """将选中的项往下移动一位"""
        row = self.thumbnail_list.currentRow()
        if row >= 0 and row < self.thumbnail_list.count() - 1:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row + 1, item)
            self.thumbnail_list.setCurrentRow(row + 1)

    def remove_selected_items(self):
        """移除左侧选中的图片项"""
        for item in self.thumbnail_list.selectedItems():
            row = self.thumbnail_list.row(item)
            self.thumbnail_list.takeItem(row)
        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText(f"剩余图片数: {self.thumbnail_list.count()} 张")

    def clear_all_items(self):
        """清空左侧所有列表项"""
        self.thumbnail_list.clear()
        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText("列表已清空")

    def show_context_menu(self, pos):
        """右键菜单功能"""
        menu = QMenu(self)
        up_action = menu.addAction("⬆️ 上移选中项")
        down_action = menu.addAction("⬇️ 下移选中项")
        menu.addSeparator()
        remove_action = menu.addAction("❌ 移除选中图片")
        clear_action = menu.addAction("🗑️ 清空所有列表")
        
        action = menu.exec_(self.thumbnail_list.mapToGlobal(pos))
        if action == up_action:
            self.move_item_up()
        elif action == down_action:
            self.move_item_down()
        elif action == remove_action:
            self.remove_selected_items()
        elif action == clear_action:
            self.clear_all_items()

    def export_to_pdf(self):
        """按照左侧列表当前的排序顺序，将图片导出合并为 PDF"""
        if self.thumbnail_list.count() == 0:
            QMessageBox.warning(self, "警告", "当前没有可导出的图片！")
            return

        pdf_path, _ = QFileDialog.getSaveFileName(self, "导出 PDF 文件", "", "PDF Files (*.pdf)")
        if not pdf_path:
            return

        try:
            images = []
            for i in range(self.thumbnail_list.count()):
                item = self.thumbnail_list.item(i)
                file_path = os.path.join(self.current_folder_path, item.text())
                
                img = Image.open(file_path)
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.convert("RGBA").split()[3])
                    img = background
                else:
                    img = img.convert("RGB")
                
                images.append(img)

            if images:
                first_img = images[0]
                rest_imgs = images[1:] if len(images) > 1 else []
                first_img.save(pdf_path, "PDF", save_all=True, append_images=rest_imgs)
                
                QMessageBox.information(self, "成功", f"PDF 文件已成功导出至：\n{pdf_path}")
                self.status_label.setText(f"PDF 导出成功: {pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出 PDF 失败：\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ThumbnailViewer()
    viewer.show()
    sys.exit(app.exec_())
