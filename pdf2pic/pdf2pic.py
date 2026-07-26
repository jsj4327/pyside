import sys
import os
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, 
                             QFileDialog, QLabel, QSplitter, QMessageBox, QMenu, 
                             QScrollArea)
from PySide2.QtCore import Qt, QSize, QPoint
from PySide2.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QWheelEvent, QMouseEvent
from pdf2image import convert_from_path

class ZoomableScrollArea(QScrollArea):
    """支持滚轮缩放、边界限制及鼠标左键拖拽平移的图片预览滚动区域"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_label = QLabel("在此处预览页面大图")
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
        
        angle = event.angleDelta().y()
        if angle == 0:
            return

        factor = 1.15 if angle > 0 else 1. / 1.15
        new_scale = self.scale_factor * factor

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


class Pdf2PicViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pdf2pic - PDF 转图片工具")
        
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = int(screen.width() * 0.8)
        window_height = int(screen.height() * 0.8)
        
        self.resize(window_width, window_height)
        center_x = screen.x() + (screen.width() - window_width) // 2
        center_y = screen.y() + (screen.height() - window_height) // 2
        self.move(center_x, center_y)

        self.pdf_images = []  # 存储加载的 PIL Image 对象列表
        self.init_ui(window_width)

    def init_ui(self, window_width):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 1. 顶部工具栏：单行排列
        top_bar_layout = QHBoxLayout()
        
        self.btn_open_pdf = QPushButton("📁 打开 PDF 文件")
        self.btn_open_pdf.setStyleSheet("font-weight: bold;")
        self.btn_open_pdf.clicked.connect(self.open_pdf)
        top_bar_layout.addWidget(self.btn_open_pdf)

        self.btn_move_up = QPushButton("⬆️ 上移")
        self.btn_move_up.clicked.connect(self.move_item_up)
        top_bar_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("⬇️ 下移")
        self.btn_move_down.clicked.connect(self.move_item_down)
        top_bar_layout.addWidget(self.btn_move_down)

        self.btn_remove_item = QPushButton("❌ 移除页面")
        self.btn_remove_item.clicked.connect(self.remove_selected_items)
        top_bar_layout.addWidget(self.btn_remove_item)

        self.btn_clear_list = QPushButton("🗑️ 清空")
        self.btn_clear_list.clicked.connect(self.clear_all_items)
        top_bar_layout.addWidget(self.btn_clear_list)

        self.btn_export_images = QPushButton("✨ 导出为图片")
        self.btn_export_images.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_export_images.clicked.connect(self.export_to_images)
        top_bar_layout.addWidget(self.btn_export_images)

        main_layout.addLayout(top_bar_layout)

        # 2. 中间分栏（左侧缩略图，右侧带缩放和平移的大图预览）
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # 左侧：缩略图列表
        self.thumbnail_list = StrictOrderListWidget()
        self.thumbnail_list.itemClicked.connect(self.show_large_image)
        self.thumbnail_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.thumbnail_list.customContextMenuRequested.connect(self.show_context_menu)
        splitter.addWidget(self.thumbnail_list)

        # 右侧：大图预览区域
        self.image_scroll_area = ZoomableScrollArea()
        splitter.addWidget(self.image_scroll_area)

        splitter.setSizes([200, window_width - 200])

        # 3. 底部状态栏标签
        self.status_label = QLabel("就绪：请点击上方“打开 PDF 文件”按钮")
        self.status_label.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def open_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        if not pdf_path:
            return
            
        self.thumbnail_list.clear()
        self.image_scroll_area.image_label.setText("在此处预览页面大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText("正在解析 PDF，请稍候...")
        QApplication.processEvents()

        try:
            # 将 PDF 转换为 PIL Image 列表（默认 200 DPI 保证清晰度）
            self.pdf_images = convert_from_path(pdf_path, dpi=200)
            
            for index, img in enumerate(self.pdf_images):
                # 将 PIL 转换为 QPixmap 用于界面显示
                temp_path = f"temp_page_{index}.png"
                img.save(temp_path, "PNG")
                pixmap = QPixmap(temp_path)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(QIcon(scaled_pixmap), f"第 {index + 1} 页")
                item.setSizeHint(QSize(120, 110))
                self.thumbnail_list.addItem(item)
                
            self.status_label.setText(f"已加载 PDF: {os.path.basename(pdf_path)} (共 {len(self.pdf_images)} 页)")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"解析 PDF 失败：\n{str(e)}")
            self.status_label.setText("PDF 解析失败")

    def show_large_image(self, item):
        row = self.thumbnail_list.row(item)
        if 0 <= row < len(self.pdf_images):
            pil_img = self.pdf_images[row]
            temp_path = "temp_large_view.png"
            pil_img.save(temp_path, "PNG")
            pixmap = QPixmap(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if not pixmap.isNull():
                self.image_scroll_area.set_pixmap(pixmap)

    def move_item_up(self):
        row = self.thumbnail_list.currentRow()
        if row > 0:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row - 1, item)
            self.thumbnail_list.setCurrentRow(row - 1)
            # 同步更新底层数据列表顺序
            self.pdf_images.insert(row - 1, self.pdf_images.pop(row))

    def move_item_down(self):
        row = self.thumbnail_list.currentRow()
        if 0 <= row < self.thumbnail_list.count() - 1:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row + 1, item)
            self.thumbnail_list.setCurrentRow(row + 1)
            self.pdf_images.insert(row + 1, self.pdf_images.pop(row))

    def remove_selected_items(self):
        selected_items = self.thumbnail_list.selectedItems()
        if not selected_items:
            return
        
        # 从大到小排序索引，防止删除时索引错位
        rows = sorted([self.thumbnail_list.row(item) for item in selected_items], reverse=True)
        for row in rows:
            self.thumbnail_list.takeItem(row)
            if 0 <= row < len(self.pdf_images):
                self.pdf_images.pop(row)
                
        self.image_scroll_area.image_label.setText("在此处预览页面大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText(f"剩余页面数: {len(self.pdf_images)} 页")

    def clear_all_items(self):
        self.thumbnail_list.clear()
        self.pdf_images.clear()
        self.image_scroll_area.image_label.setText("在此处预览页面大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText("列表已清空")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        up_action = menu.addAction("⬆️ 上移选中页")
        down_action = menu.addAction("⬇️ 下移选中页")
        menu.addSeparator()
        remove_action = menu.addAction("❌ 移除选中页")
        clear_action = menu.addAction("🗑️ 清空所有")
        
        action = menu.exec_(self.thumbnail_list.mapToGlobal(pos))
        if action == up_action:
            self.move_item_up()
        elif action == down_action:
            self.move_item_down()
        elif action == remove_action:
            self.remove_selected_items()
        elif action == clear_action:
            self.clear_all_items()

    def export_to_images(self):
        if not self.pdf_images:
            QMessageBox.warning(self, "警告", "当前没有可导出的页面！")
            return

        folder_path = QFileDialog.getExistingDirectory(self, "选择保存图片的文件夹")
        if not folder_path:
            return

        try:
            # 弹窗让用户选择保存格式
            format_choice, ok = QFileDialog.getSaveFileName(
                self, "保存图片前缀", os.path.join(folder_path, "page_"), "PNG Files (*.png);;JPG Files (*.jpg)"
            )
            # 如果用户取消或没有填前缀，使用默认前缀
            base_name = "page_"
            ext = ".png"
            if format_choice:
                base_dir = os.path.dirname(format_choice)
                base_name = os.path.basename(format_choice).split('.')[0]
                if format_choice.lower().endswith('.jpg') or format_choice.lower().endswith('.jpeg'):
                    ext = ".jpg"
                folder_path = base_dir

            # 按照左侧列表当前的排序状态（即 self.pdf_images 调整后的顺序）依次导出
            for i, img in enumerate(self.pdf_images):
                save_path = os.path.join(folder_path, f"{base_name}{i + 1}{ext}")
                if ext == ".jpg":
                    # JPG 格式不支持 RGBA，转换成 RGB
                    if img.mode in ("RGBA", "LA"):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.convert("RGBA").split()[3])
                        background.save(save_path, "JPEG", quality=95)
                    else:
                        img.convert("RGB").save(save_path, "JPEG", quality=95)
                else:
                    img.save(save_path, "PNG")

            QMessageBox.information(self, "成功", f"所有页面已成功导出至文件夹：\n{folder_path}")
            self.status_label.setText(f"图片导出成功，共 {len(self.pdf_images)} 张")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出图片失败：\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = Pdf2PicViewer()
    viewer.show()
    sys.exit(app.exec_())
