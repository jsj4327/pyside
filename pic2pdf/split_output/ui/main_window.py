"""主窗口类，负责布局组装、信号连接及用户交互协调"""
import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidgetItem, QPushButton, QFileDialog, QLabel,
    QSplitter, QMessageBox, QMenu, QApplication
)
from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QPixmap, QIcon, QTransform

from config.constants import (
    THUMBNAIL_ICON_SIZE, THUMBNAIL_ITEM_WIDTH, THUMBNAIL_ITEM_HEIGHT,
    WINDOW_SIZE_RATIO, SPLITTER_LEFT_WIDTH
)
from core.image_model import ImageModel
from services.pdf_exporter import PdfExporter
from ui.zoomable_scroll_area import ZoomableScrollArea
from ui.strict_order_list import StrictOrderListWidget


class ThumbnailViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pic2pdf - 图片转 PDF 工具")

        screen = QApplication.primaryScreen().availableGeometry()

        window_width = int(screen.width() * WINDOW_SIZE_RATIO)
        window_height = int(screen.height() * WINDOW_SIZE_RATIO)

        self.resize(window_width, window_height)
        center_x = screen.x() + (screen.width() - window_width) // 2
        center_y = screen.y() + (screen.height() - window_height) // 2
        self.move(center_x, center_y)

        self.model = ImageModel()
        self.init_ui(window_width)

    def init_ui(self, window_width: int):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部工具栏
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

        self.btn_rotate_left = QPushButton("↺ 左旋")
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_selected(-90))
        top_bar_layout.addWidget(self.btn_rotate_left)

        self.btn_rotate_right = QPushButton("↻ 右旋")
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_selected(90))
        top_bar_layout.addWidget(self.btn_rotate_right)

        self.btn_export_pdf = QPushButton("✨ 导出为 PDF")
        self.btn_export_pdf.setStyleSheet(
            "background-color: #0078d7; color: white; font-weight: bold;"
        )
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)
        top_bar_layout.addWidget(self.btn_export_pdf)

        main_layout.addLayout(top_bar_layout)

        # 中间分栏
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        self.thumbnail_list = StrictOrderListWidget()
        self.thumbnail_list.itemClicked.connect(self.show_large_image)
        self.thumbnail_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.thumbnail_list.customContextMenuRequested.connect(self.show_context_menu)
        splitter.addWidget(self.thumbnail_list)

        self.image_scroll_area = ZoomableScrollArea()
        splitter.addWidget(self.image_scroll_area)

        splitter.setSizes([SPLITTER_LEFT_WIDTH, window_width - SPLITTER_LEFT_WIDTH])

        # 底部状态栏
        self.status_label = QLabel("就绪：请点击上方“打开文件夹”按钮")
        self.status_label.setStyleSheet("color: #555; font-size: 11px;")
        main_layout.addWidget(self.status_label)

    def _create_rotated_thumbnail(self, pixmap: QPixmap, angle: int) -> QPixmap:
        """创建旋转后的缩略图"""
        if angle == 0 or pixmap.isNull():
            return pixmap.scaled(
                THUMBNAIL_ICON_SIZE, THUMBNAIL_ICON_SIZE,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        transform = QTransform()
        transform.rotate(angle)
        rotated = pixmap.transformed(transform, Qt.SmoothTransformation)
        return rotated.scaled(
            THUMBNAIL_ICON_SIZE, THUMBNAIL_ICON_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

    def _update_thumbnail_icon(self, row: int):
        """更新指定行的缩略图图标（根据当前旋转角度）"""
        item = self.thumbnail_list.item(row)
        if item is None:
            return
        filename = item.text()
        file_path = self.model.get_full_path(filename)
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            angle = self.model.get_rotation(filename)
            scaled_pixmap = self._create_rotated_thumbnail(pixmap, angle)
            item.setIcon(QIcon(scaled_pixmap))

    def rotate_selected(self, angle: int):
        """旋转所有选中的图片（同时更新缩略图和大图预览）"""
        selected_items = self.thumbnail_list.selectedItems()
        if not selected_items:
            # 如果没有选中项但有大图预览，则只旋转预览
            if not self.image_scroll_area.original_pixmap.isNull():
                self.image_scroll_area.rotate_image(angle)
            return

        for item in selected_items:
            row = self.thumbnail_list.row(item)
            filename = item.text()
            self.model.rotate(filename, angle)
            self._update_thumbnail_icon(row)

        # 如果当前选中的第一项正好是大图预览显示的，也同步旋转大图
        current_item = self.thumbnail_list.currentItem()
        if current_item and current_item in selected_items:
            self.image_scroll_area.rotate_image(angle)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder_path:
            return

        count = self.model.load_folder(folder_path)
        self.thumbnail_list.clear()
        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()

        for file_name in self.model.file_names:
            file_path = self.model.get_full_path(file_name)
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    THUMBNAIL_ICON_SIZE, THUMBNAIL_ICON_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                item = QListWidgetItem(QIcon(scaled_pixmap), file_name)
                item.setSizeHint(QSize(THUMBNAIL_ITEM_WIDTH, THUMBNAIL_ITEM_HEIGHT))
                self.thumbnail_list.addItem(item)

        self.status_label.setText(
            f"已加载文件夹: {folder_path} (共 {count} 张图片)"
        )

    def show_large_image(self, item: QListWidgetItem):
        if self.model.folder_path:
            file_path = self.model.get_full_path(item.text())
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.image_scroll_area.set_pixmap(pixmap)
                # 应用该图片已有的旋转角度
                angle = self.model.get_rotation(item.text())
                if angle != 0:
                    self.image_scroll_area.rotation_angle = angle
                    self.image_scroll_area.update_image_display()

    def move_item_up(self):
        row = self.thumbnail_list.currentRow()
        if row > 0:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row - 1, item)
            self.thumbnail_list.setCurrentRow(row - 1)
            self.model.move_item(row, row - 1)

    def move_item_down(self):
        row = self.thumbnail_list.currentRow()
        if 0 <= row < self.thumbnail_list.count() - 1:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row + 1, item)
            self.thumbnail_list.setCurrentRow(row + 1)
            self.model.move_item(row, row + 1)

    def remove_selected_items(self):
        rows = sorted(
            [self.thumbnail_list.row(item) for item in self.thumbnail_list.selectedItems()],
            reverse=True
        )
        for row in rows:
            self.thumbnail_list.takeItem(row)
            self.model.remove_at(row)

        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText(f"剩余图片数: {self.model.count} 张")

    def clear_all_items(self):
        self.thumbnail_list.clear()
        self.model.clear()
        self.image_scroll_area.image_label.setText("在此处预览大图")
        self.image_scroll_area.original_pixmap = QPixmap()
        self.status_label.setText("列表已清空")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        up_action = menu.addAction("⬆️ 上移选中项")
        down_action = menu.addAction("⬇️ 下移选中项")
        menu.addSeparator()
        rotate_left_action = menu.addAction("↺ 左旋")
        rotate_right_action = menu.addAction("↻ 右旋")
        menu.addSeparator()
        remove_action = menu.addAction("❌ 移除选中图片")
        clear_action = menu.addAction("🗑️ 清空所有列表")

        action = menu.exec_(self.thumbnail_list.mapToGlobal(pos))
        if action == up_action:
            self.move_item_up()
        elif action == down_action:
            self.move_item_down()
        elif action == rotate_left_action:
            self.rotate_selected(-90)
        elif action == rotate_right_action:
            self.rotate_selected(90)
        elif action == remove_action:
            self.remove_selected_items()
        elif action == clear_action:
            self.clear_all_items()

    def export_to_pdf(self):
        if self.model.count == 0:
            QMessageBox.warning(self, "警告", "当前没有可导出的图片！")
            return

        pdf_path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF 文件", "", "PDF Files (*.pdf)"
        )
        if not pdf_path:
            return

        try:
            image_data = []
            for i in range(self.model.count):
                filename = self.model.get_file_at(i)
                full_path = self.model.get_full_path(filename)
                rotation = self.model.get_rotation(filename)
                image_data.append((full_path, rotation))

            PdfExporter.export(image_data, pdf_path)
            QMessageBox.information(
                self, "成功", f"PDF 文件已成功导出至：\n{pdf_path}"
            )
            self.status_label.setText(f"PDF 导出成功: {pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出 PDF 失败：\n{str(e)}")