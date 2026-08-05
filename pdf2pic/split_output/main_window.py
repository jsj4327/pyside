""" 主窗口类 组合 UI 子组件，协调 Service 与 Worker 完成业务流程。 """
import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSplitter, QMessageBox, QMenu, QFileDialog, QListWidgetItem, 
    QApplication, QInputDialog
)
from PySide2.QtCore import Qt, QSize, QPoint
from PySide2.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from config import (
    WINDOW_SIZE_RATIO, THUMBNAIL_ITEM_SIZE, DEFAULT_DPI, 
    STYLE_BTN_PRIMARY, STYLE_BTN_BOLD, STYLE_STATUS_LABEL
)
from services.pdf_service import create_thumbnail_icon, pil_to_pixmap
from services.export_service import export_images, parse_export_format
from workers.pdf_loader_worker import PdfLoaderWorker
from ui.zoomable_scroll_area import ZoomableScrollArea
from ui.strict_order_list import StrictOrderListWidget


class Pdf2PicViewer(QMainWindow):
    """PDF 转图片工具主窗口 (增强版)"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pdf2pic - PDF 转图片工具")
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * WINDOW_SIZE_RATIO)
        h = int(screen.height() * WINDOW_SIZE_RATIO)
        self.resize(w, h)
        self.move(
            screen.x() + (screen.width() - w) // 2,
            screen.y() + (screen.height() - h) // 2
        )
        
        self.pdf_images = []
        self.loader_worker = None
        
        # 启用文件拖拽
        self.setAcceptDrops(True)
        
        self._init_ui(w)

    def _init_ui(self, window_width: int):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # === 顶部工具栏 ===
        top = QHBoxLayout()
        
        # 打开按钮
        self.btn_open = QPushButton("📁 打开 PDF (支持拖拽)")
        self.btn_open.setStyleSheet(STYLE_BTN_BOLD)
        self.btn_open.setShortcut("Ctrl+O")  # 快捷键
        self.btn_open.clicked.connect(self.open_pdf)
        top.addWidget(self.btn_open)

        # 分隔符
        line1 = QLabel("|")
        line1.setStyleSheet("color: #aaa; padding: 0 5px;")
        top.addWidget(line1)

        # 旋转按钮
        self.btn_rotate_left = QPushButton("↺ 左旋")
        self.btn_rotate_left.setToolTip("逆时针旋转选中页面")
        self.btn_rotate_left.setShortcut("Left")  # 快捷键
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_pages(-90))
        top.addWidget(self.btn_rotate_left)

        self.btn_rotate_right = QPushButton("↻ 右旋")
        self.btn_rotate_right.setToolTip("顺时针旋转选中页面")
        self.btn_rotate_right.setShortcut("Right")  # 快捷键
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_pages(90))
        top.addWidget(self.btn_rotate_right)

        # 分隔符
        line2 = QLabel("|")
        line2.setStyleSheet("color: #aaa; padding: 0 5px;")
        top.addWidget(line2)

        # 排序/删除按钮
        self.btn_up = QPushButton("⬆️ 上移")
        self.btn_up.setShortcut("Ctrl+Up")
        self.btn_up.clicked.connect(self.move_item_up)
        top.addWidget(self.btn_up)

        self.btn_down = QPushButton("⬇️ 下移")
        self.btn_down.setShortcut("Ctrl+Down")
        self.btn_down.clicked.connect(self.move_item_down)
        top.addWidget(self.btn_down)

        self.btn_remove = QPushButton("❌ 移除")
        self.btn_remove.setShortcut("Delete")
        self.btn_remove.clicked.connect(self.remove_selected_items)
        top.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.clicked.connect(self.clear_all_items)
        top.addWidget(self.btn_clear)

        self.btn_export = QPushButton("✨ 导出图片")
        self.btn_export.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_export.clicked.connect(self.export_to_images)
        top.addWidget(self.btn_export)

        main_layout.addLayout(top)

        # === 主界面分割 ===
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # 左侧缩略图列表
        self.thumbnail_list = StrictOrderListWidget()
        self.thumbnail_list.itemClicked.connect(self.show_large_image)
        self.thumbnail_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.thumbnail_list.customContextMenuRequested.connect(self.show_context_menu)
        splitter.addWidget(self.thumbnail_list)

        # 右侧预览区
        self.image_scroll = ZoomableScrollArea()
        self.image_scroll.page_changed.connect(self._on_preview_page_changed)
        # 右侧预览区右键菜单
        self.image_scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_scroll.customContextMenuRequested.connect(self.show_preview_context_menu)
        splitter.addWidget(self.image_scroll)

        splitter.setSizes([200, window_width - 200])

        # 状态栏
        self.status_label = QLabel("就绪：支持拖拽 PDF 打开 | 使用 Delete 键删除 | Ctrl+滚轮缩放")
        self.status_label.setStyleSheet(STYLE_STATUS_LABEL)
        main_layout.addWidget(self.status_label)

    # ==================== 文件操作 (拖拽与打开) ====================
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """处理文件拖拽进入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith('.pdf'):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """处理文件放下事件"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith('.pdf'):
                self.open_pdf_path(path)

    def open_pdf(self):
        """打开文件对话框"""
        dialog = QFileDialog(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_() != QFileDialog.Accepted:
            return
        selected_files = dialog.selectedFiles()
        if selected_files:
            self.open_pdf_path(selected_files[0])

    def open_pdf_path(self, path: str):
        """核心加载逻辑：供按钮点击和拖拽共用"""
        # 重置界面
        self.thumbnail_list.clear()
        self.image_scroll.image_label.setText("在此处预览页面大图")
        self.image_scroll.original_pixmap = QPixmap()
        self.status_label.setText("正在解析 PDF，请稍候...")
        self.btn_open.setEnabled(False)

        # 启动后台线程加载
        self.loader_worker = PdfLoaderWorker(path, DEFAULT_DPI, self)
        self.loader_worker.finished.connect(lambda imgs: self.on_pdf_loaded(imgs, path))
        self.loader_worker.error.connect(self.on_pdf_load_error)
        self.loader_worker.start()

    # ==================== PDF 加载回调 ====================

    def on_pdf_loaded(self, images, pdf_path):
        self.pdf_images = images
        # 填充缩略图列表
        for idx, img in enumerate(images):
            icon = create_thumbnail_icon(img)
            item = QListWidgetItem(icon, f"第 {idx + 1} 页")
            item.setSizeHint(QSize(*THUMBNAIL_ITEM_SIZE))
            self.thumbnail_list.addItem(item)
        
        # 填充预览区
        pixmaps = [pil_to_pixmap(img) for img in images]
        self.image_scroll.set_continuous_pages(pixmaps)
        
        self.status_label.setText(
            f"已加载 PDF: {os.path.basename(pdf_path)} (共 {len(images)} 页) | "
            f"快捷键: Delete(删除) ←/→(旋转)"
        )
        self.btn_open.setEnabled(True)
        if self.thumbnail_list.count() > 0:
            self.thumbnail_list.setCurrentRow(0)

    def on_pdf_load_error(self, err_msg):
        QMessageBox.critical(self, "错误", f"解析 PDF 失败：\n{err_msg}")
        self.status_label.setText("PDF 解析失败")
        self.btn_open.setEnabled(True)

    # ==================== 新增功能：页面旋转 ====================

    def rotate_pages(self, angle: int):
        """旋转选中的页面 (angle: -90 或 90)，并保持当前位置"""
        selected_items = self.thumbnail_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先在左侧列表选中需要旋转的页面")
            return

        # 【关键修复】记录当前焦点的行号，用于旋转后恢复位置
        current_row = self.thumbnail_list.currentRow()

        self.thumbnail_list.blockSignals(True)
        
        for item in selected_items:
            row = self.thumbnail_list.row(item)
            if 0 <= row < len(self.pdf_images):
                # 旋转 PIL 图片 (expand=True 防止裁剪)
                pil_img = self.pdf_images[row]
                rotated_img = pil_img.rotate(angle, expand=True)
                self.pdf_images[row] = rotated_img
                
                # 立即更新列表图标
                item.setIcon(create_thumbnail_icon(rotated_img))

        self.thumbnail_list.blockSignals(False)
        
        # 【关键修复】刷新预览区，并传入 target_index，防止跳回第一页
        self._refresh_continuous_view(target_index=current_row)
        self.status_label.setText(f"已旋转 {len(selected_items)} 个页面")

    # ==================== 新增功能：键盘快捷键 ====================

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        
        # 删除键
        if key == Qt.Key_Delete:
            self.remove_selected_items()
            return

        # 常规上下选择（不带修饰键）
        if mods == Qt.NoModifier:
            if key == Qt.Key_Up:
                curr = self.thumbnail_list.currentRow()
                if curr > 0:
                    self.thumbnail_list.setCurrentRow(curr - 1)
                return
            elif key == Qt.Key_Down:
                curr = self.thumbnail_list.currentRow()
                if curr < self.thumbnail_list.count() - 1:
                    self.thumbnail_list.setCurrentRow(curr + 1)
                return
        
        super().keyPressEvent(event)

    # ==================== 新增功能：预览区右键菜单 ====================

    def show_preview_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        act_fit = menu.addAction("🔍 适应宽度")
        act_reset = menu.addAction("↺ 重置缩放 (100%)")
        menu.addSeparator()
        act_copy = menu.addAction("📋 复制当前页图片到剪贴板")
        
        action = menu.exec_(self.image_scroll.mapToGlobal(pos))
        
        if action == act_fit:
            self.image_scroll.fit_to_width()
            self.status_label.setText("已适应宽度显示")
        elif action == act_reset:
            self.image_scroll.reset_zoom()
        elif action == act_copy:
            self._copy_current_page_to_clipboard()

    def _copy_current_page_to_clipboard(self):
        row = self.thumbnail_list.currentRow()
        if 0 <= row < len(self.pdf_images):
            pixmap = pil_to_pixmap(self.pdf_images[row])
            if not pixmap.isNull():
                QApplication.clipboard().setPixmap(pixmap)
                self.status_label.setText("已复制当前页到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "未选中任何页面")

    # ==================== 原有逻辑 (交互与操作) ====================

    def show_large_image(self, item):
        row = self.thumbnail_list.row(item)
        if 0 <= row < len(self.pdf_images):
            if self.image_scroll.continuous_mode:
                # 联动滚动逻辑
                labels = self.image_scroll._page_labels
                if row < len(labels):
                    target_label = labels[row]
                    y = target_label.y()
                    bar = self.image_scroll.verticalScrollBar()
                    viewport_h = self.image_scroll.viewport().height()
                    label_h = target_label.height()
                    scroll_target = y - (viewport_h - label_h) // 2
                    bar.setValue(max(bar.minimum(), min(bar.maximum(), scroll_target)))
            else:
                pixmap = pil_to_pixmap(self.pdf_images[row])
                if not pixmap.isNull():
                    self.image_scroll.set_pixmap(pixmap)

    def _on_preview_page_changed(self, page_index: int):
        if 0 <= page_index < self.thumbnail_list.count():
            self.thumbnail_list.blockSignals(True)
            self.thumbnail_list.setCurrentRow(page_index)
            self.thumbnail_list.scrollToItem(
                self.thumbnail_list.item(page_index)
            )
            self.thumbnail_list.blockSignals(False)

    def move_item_up(self):
        row = self.thumbnail_list.currentRow()
        if row > 0:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row - 1, item)
            self.thumbnail_list.setCurrentRow(row - 1)
            self.pdf_images.insert(row - 1, self.pdf_images.pop(row))
            self._refresh_continuous_view()

    def move_item_down(self):
        row = self.thumbnail_list.currentRow()
        if 0 <= row < self.thumbnail_list.count() - 1:
            item = self.thumbnail_list.takeItem(row)
            self.thumbnail_list.insertItem(row + 1, item)
            self.thumbnail_list.setCurrentRow(row + 1)
            self.pdf_images.insert(row + 1, self.pdf_images.pop(row))
            self._refresh_continuous_view()

    def remove_selected_items(self):
        selected = self.thumbnail_list.selectedItems()
        if not selected:
            return
        
        # 从后往前删，防止索引错乱
        rows = sorted(
            [self.thumbnail_list.row(it) for it in selected], reverse=True
        )
        for r in rows:
            self.thumbnail_list.takeItem(r)
            if 0 <= r < len(self.pdf_images):
                self.pdf_images.pop(r)
        
        self._refresh_continuous_view()
        self.status_label.setText(f"剩余页面数: {len(self.pdf_images)} 页")

    def clear_all_items(self):
        self.thumbnail_list.clear()
        self.pdf_images.clear()
        self.image_scroll.image_label.setText("在此处预览页面大图")
        self.image_scroll.original_pixmap = QPixmap()
        self.image_scroll.set_continuous_pages([])
        self.status_label.setText("列表已清空")

    def _refresh_continuous_view(self, target_index: int = None):
        """刷新预览区
        :param target_index: 刷新后自动滚动到的索引（修复旋转后跳页bug的关键）
        """
        if not self.pdf_images:
            self.image_scroll.set_continuous_pages([])
            return
        pixmaps = [pil_to_pixmap(img) for img in self.pdf_images]
        # 将 target_index 传给 ZoomableScrollArea
        self.image_scroll.set_continuous_pages(pixmaps, target_index=target_index)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        act_up = menu.addAction("⬆️ 上移选中页")
        act_down = menu.addAction("⬇️ 下移选中页")
        menu.addSeparator()
        act_rot_l = menu.addAction("↺ 左旋 90°")
        act_rot_r = menu.addAction("↻ 右旋 90°")
        menu.addSeparator()
        act_rm = menu.addAction("❌ 移除选中页")
        act_clr = menu.addAction("🗑️ 清空所有")
        
        action = menu.exec_(self.thumbnail_list.mapToGlobal(pos))
        
        if action == act_up:
            self.move_item_up()
        elif action == act_down:
            self.move_item_down()
        elif action == act_rot_l:
            self.rotate_pages(-90)
        elif action == act_rot_r:
            self.rotate_pages(90)
        elif action == act_rm:
            self.remove_selected_items()
        elif action == act_clr:
            self.clear_all_items()

    def export_to_images(self):
        if not self.pdf_images:
            QMessageBox.warning(self, "警告", "当前没有可导出的页面！")
            return
        
        folder_dialog = QFileDialog(self, "选择保存图片的文件夹", "")
        folder_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        folder_dialog.setFileMode(QFileDialog.Directory)
        folder_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if folder_dialog.exec_() != QFileDialog.Accepted:
            return
            
        selected_folders = folder_dialog.selectedFiles()
        if not selected_folders: return
        folder = selected_folders[0]
        
        save_dialog = QFileDialog(self, "保存图片前缀", os.path.join(folder, "page_"))
        save_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        save_dialog.setAcceptMode(QFileDialog.AcceptSave)
        save_dialog.setNameFilters(["PNG Files (*.png)", "JPG Files (*.jpg)"])
        
        if save_dialog.exec_() != QFileDialog.Accepted:
            return
            
        selected_files = save_dialog.selectedFiles()
        if not selected_files: return
        fmt_choice = selected_files[0]
        
        base_name, ext = parse_export_format(fmt_choice)
        target_folder = os.path.dirname(fmt_choice) if fmt_choice else folder
        
        try:
            export_images(self.pdf_images, target_folder, base_name, ext)
            QMessageBox.information(
                self, "成功", f"所有页面已成功导出至文件夹：\n{target_folder}"
            )
            self.status_label.setText(
                f"图片导出成功，共 {len(self.pdf_images)} 张"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出图片失败：\n{str(e)}")
