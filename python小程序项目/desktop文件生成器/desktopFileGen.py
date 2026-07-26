import sys
import os
import stat
import shutil
import subprocess
from PySide2.QtGui import QIcon, QPixmap, QImage, QPainter, QPen, QColor
from PySide2.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QFileDialog, 
                               QMessageBox, QListView, QSplitter, QFrame,
                               QFileSystemModel, QTextEdit, QDialog, QRubberBand)
from PySide2.QtCore import QSettings, Qt, QDir, QModelIndex, QRect, QPoint, QSize

class ImageCropDialog(QDialog):
    """图片裁剪对话框：彻底修复坐标偏移及边缘限制问题"""
    def __init__(self, image_path, original_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪正方形图标")
        self.setModal(True)
        self.resize(550, 600)
        
        self.source_pixmap = QPixmap(image_path)
        self.cropped_pixmap = None
        self.original_filename = original_filename
        
        layout = QVBoxLayout(self)
        
        # --- 图标名称输入 ---
        name_layout = QHBoxLayout()
        self.label_name_tip = QLabel("图标文件名:")
        self.name_edit = QLineEdit()
        base_name = os.path.splitext(os.path.basename(original_filename))[0] if original_filename else "gimp"
        self.name_edit.setText(base_name)
        name_layout.addWidget(self.label_name_tip)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        self.label_tip = QLabel("提示：在图片上按住鼠标左键自由拖动绘制裁剪框；画好后可在框内拖动调整位置。")
        self.label_tip.setStyleSheet("color: #666; margin-bottom: 5px;")
        layout.addWidget(self.label_tip)
        
        # --- 图片预览与缩放 ---
        max_preview_size = 400
        if self.source_pixmap.width() > max_preview_size or self.source_pixmap.height() > max_preview_size:
            self.display_pixmap = self.source_pixmap.scaled(max_preview_size, max_preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self.display_pixmap = self.source_pixmap
            
        # 【关键修复】将图片载体精确限制为图片大小，避免外围留白导致鼠标坐标与图片像素产生偏移
        self.image_label = QLabel()
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.setFixedSize(self.display_pixmap.size()) 
        
        # 使用一个居中的外层布局来包装固定大小的 image_label
        img_container = QWidget()
        img_layout = QHBoxLayout(img_container)
        img_layout.setAlignment(Qt.AlignCenter)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.addWidget(self.image_label)
        layout.addWidget(img_container, stretch=1)
        
        # 橡皮筋选框绑定到 image_label 上
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.image_label)
        
        # --- 交互变量 ---
        self.mode = "NONE"          
        self.origin = QPoint()      
        self.selection_rect = QRect() 
        self.move_offset = QPoint()   
        
        # --- 按钮区域 ---
        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("确认裁剪")
        self.btn_confirm.setMinimumHeight(35)
        self.btn_confirm.clicked.connect(self.accept_crop)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        # 重写鼠标事件
        self.image_label.mousePressEvent = self.on_mouse_press
        self.image_label.mouseMoveEvent = self.on_mouse_move
        self.image_label.mouseReleaseEvent = self.on_mouse_release
        
        self.rubber_band.hide()

    def on_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            click_pos = event.pos()
            if self.selection_rect.isValid() and self.selection_rect.contains(click_pos):
                self.mode = "MOVE"
                self.move_offset = click_pos - self.selection_rect.topLeft()
            else:
                self.mode = "DRAW"
                self.origin = click_pos
                self.selection_rect = QRect(self.origin, QSize())
                self.rubber_band.setGeometry(self.selection_rect)
                self.rubber_band.show()

    def on_mouse_move(self, event):
        if not self.image_label.rect().isValid():
            return
            
        w = self.image_label.width()
        h = self.image_label.height()

        if self.mode == "DRAW":
            # 1. 限制鼠标虚拟点在组件范围内
            curr_x = max(0, min(event.pos().x(), w))
            curr_y = max(0, min(event.pos().y(), h))
            
            # 2. 计算相对位移
            dx = curr_x - self.origin.x()
            dy = curr_y - self.origin.y()
            
            # 3. 获取基础边长
            side = max(abs(dx), abs(dy))
            
            # 4. 根据四个象限分别约束边长最大值（防撞墙死锁）
            if dx >= 0:
                side = min(side, w - self.origin.x())
            else:
                side = min(side, self.origin.x())
                
            if dy >= 0:
                side = min(side, h - self.origin.y())
            else:
                side = min(side, self.origin.y())
                
            # 5. 根据方向倒推真正的左上角顶点
            left = self.origin.x() if dx >= 0 else self.origin.x() - side
            top  = self.origin.y() if dy >= 0 else self.origin.y() - side
            
            side = max(side, 1) # 防止不可见
            
            self.selection_rect = QRect(int(left), int(top), int(side), int(side))
            self.rubber_band.setGeometry(self.selection_rect)

        elif self.mode == "MOVE":
            # 拖拽移动模式下的边缘防溢出
            new_top_left = event.pos() - self.move_offset
            side = self.selection_rect.width()
            
            new_x = max(0, min(new_top_left.x(), w - side))
            new_y = max(0, min(new_top_left.y(), h - side))
            
            self.selection_rect = QRect(new_x, new_y, side, side)
            self.rubber_band.setGeometry(self.selection_rect)

    def on_mouse_release(self, event):
        self.mode = "NONE"

    def accept_crop(self):
        if not self.selection_rect.isValid() or self.selection_rect.width() <= 5:
            QMessageBox.warning(self, "提示", "请先在图片上拖拽出一个可见的正方形裁剪框！")
            return

        # 强制使用原图宽度与展示宽度的严格比值，避免长宽浮点数比例不同导致的非正方问题
        scale = self.source_pixmap.width() / self.display_pixmap.width()
        
        orig_x = int(self.selection_rect.x() * scale)
        orig_y = int(self.selection_rect.y() * scale)
        orig_side = int(self.selection_rect.width() * scale)
        
        # 保险起见，防止像素进位导致最终拷贝超出原图边界
        orig_side = min(orig_side, self.source_pixmap.width() - orig_x, self.source_pixmap.height() - orig_y)
            
        self.cropped_pixmap = self.source_pixmap.copy(orig_x, orig_y, orig_side, orig_side)
        self.accept()

class DesktopGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(".desktop 文件与多尺寸图标生成器")
        self.resize(850, 600)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "image_101204885222667.png") 
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings = QSettings("KylinTools", "DesktopGenerator")
        
        self.fields_config = {
            "Type": "Application",
            "Name": "麒麟截图工具",
            "Comment": "支持描边和阴影的截图小程序",
            "Exec": "/usr/bin/python3 /path/to/your/script.py",
            "Icon": "ksnapshot",
            "Terminal": "false",
            "Categories": "Utility;Graphics;"
        }
        
        main_layout = QHBoxLayout()
        
        left_widget = QFrame()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        nav_layout = QHBoxLayout()
        self.btn_parent = QPushButton("⬆️ 返回上级")
        self.btn_parent.clicked.connect(self.go_parent_dir)
        nav_layout.addWidget(self.btn_parent)
        
        self.btn_child = QPushButton("⬇️ 下一级")
        self.btn_child.clicked.connect(self.go_child_dir)
        nav_layout.addWidget(self.btn_child)
        
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_dir)
        nav_layout.addWidget(self.btn_refresh)
        left_layout.addLayout(nav_layout)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("输入文件夹路径并回车")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        left_layout.addWidget(self.path_edit)
        
        self.btn_folder = QPushButton("📁 选择文件夹位置")
        self.btn_folder.clicked.connect(self.select_folder)
        left_layout.addWidget(self.btn_folder)
        
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setDragEnabled(True)
        self.list_view.setDragDropMode(QListView.DragOnly)
        self.list_view.doubleClicked.connect(self.on_double_click)
        left_layout.addWidget(self.list_view)
        
        self.btn_open_peony = QPushButton("📂 在文件管理器中打开当前路径")
        self.btn_open_peony.clicked.connect(self.open_in_peony)
        left_layout.addWidget(self.btn_open_peony)
        
        right_widget = QFrame()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.line_edits = {}
        for key, default_val in self.fields_config.items():
            h_layout = QHBoxLayout()
            label = QLabel(f"{key}:")
            label.setFixedWidth(80)
            
            line_edit = QLineEdit()
            saved_val = self.settings.value(key, default_val)
            line_edit.setText(str(saved_val))
            line_edit.setPlaceholderText(f"请输入 {key}")
            
            if key in ["Exec", "Icon"]:
                line_edit.setAcceptDrops(True)
                line_edit.dragEnterEvent = lambda e, le=line_edit, k=key: self.on_drag_enter(e, le, k)
                line_edit.dropEvent = lambda e, le=line_edit, k=key: self.on_drop(e, le, k)
            
            self.line_edits[key] = line_edit
            h_layout.addWidget(label)
            h_layout.addWidget(line_edit)
            right_layout.addLayout(h_layout)
            
        btn_generate = QPushButton("生成 .desktop 文件")
        btn_generate.clicked.connect(self.generate_desktop)
        right_layout.addWidget(btn_generate)
        
        btn_generate_sync = QPushButton("生成并同步到系统")
        btn_generate_sync.clicked.connect(self.generate_and_sync_to_system)
        right_layout.addWidget(btn_generate_sync)
        
        # --- 打开 ~/.local/share/applications 按钮 ---
        self.btn_open_apps_dir = QPushButton("📂 打开 ~/.local/share/applications")
        self.btn_open_apps_dir.clicked.connect(self.open_local_apps_dir)
        right_layout.addWidget(self.btn_open_apps_dir)
        
        btn_clean_icons = QPushButton("🗑️ 一键删除已生成的系统 PNG 图标")
        btn_clean_icons.setStyleSheet("background-color: #ffcccc; color: #990000;")
        btn_clean_icons.clicked.connect(self.clean_generated_icons)
        right_layout.addWidget(btn_clean_icons)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("操作日志将显示在这里...")
        self.log_text.setFixedHeight(100)
        right_layout.addWidget(QLabel("📋 状态输出日志:"))
        right_layout.addWidget(self.log_text)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        saved_path = self.settings.value("last_folder", QDir.homePath() + "/Desktop")
        if os.path.exists(saved_path):
            self.set_folder(saved_path)
        else:
            self.set_folder(QDir.homePath())
            
        # 调用居中显示函数
        self.center()

    def center(self):
        """将窗口居中显示在屏幕上"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", self.path_edit.text())
        if folder:
            self.set_folder(folder)

    def navigate_to_path(self):
        path = self.path_edit.text().strip()
        if os.path.isdir(path):
            self.set_folder(path)
        else:
            QMessageBox.warning(self, "提示", "输入的路径不存在或不是文件夹！")

    def go_parent_dir(self):
        current_path = self.path_edit.text()
        parent_path = os.path.dirname(current_path)
        if os.path.exists(parent_path):
            self.set_folder(parent_path)

    def go_child_dir(self):
        selected_indexes = self.list_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "提示", "请先在列表中选中一个文件夹！")
            return
        file_path = self.model.filePath(selected_indexes[0])
        if os.path.isdir(file_path):
            self.set_folder(file_path)
        else:
            QMessageBox.information(self, "提示", "选中的是文件，请选择文件夹后再点击【下一级】！")

    def refresh_dir(self):
        self.set_folder(self.path_edit.text())

    def on_double_click(self, index: QModelIndex):
        file_path = self.model.filePath(index)
        if os.path.isdir(file_path):
            self.set_folder(file_path)

    def open_in_peony(self):
        current_path = self.path_edit.text().strip()
        try:
            subprocess.Popen(["peony", current_path])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动 peony 文件管理器：\n{str(e)}")

    def open_local_apps_dir(self):
        apps_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(apps_dir, exist_ok=True)
        try:
            subprocess.Popen(["peony", apps_dir])
            self.log(f"📂 正在打开目录: {apps_dir}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动 peony 文件管理器：\n{str(e)}")

    def set_folder(self, path):
        self.model.setRootPath(path)
        self.list_view.setRootIndex(self.model.index(path))
        self.path_edit.setText(path)
        self.btn_folder.setText(f"当前: {path}")
        self.settings.setValue("last_folder", path)

    def on_drag_enter(self, event, line_edit, field_name):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def on_drop(self, event, line_edit, field_name):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if field_name == "Exec":
                if file_path.endswith(".py"):
                    line_edit.setText(f"/usr/bin/python3 {file_path}")
                else:
                    line_edit.setText(file_path)
            elif field_name == "Icon":
                image_exts = (".png", ".jpg", ".jpeg", ".svg", ".xpm")
                if file_path.lower().endswith(image_exts):
                    crop_dialog = ImageCropDialog(file_path, original_filename=file_path, parent=self)
                    if crop_dialog.exec_() == QDialog.Accepted and crop_dialog.cropped_pixmap:
                        custom_icon_name = crop_dialog.name_edit.text().strip()
                        self.process_and_install_icons(crop_dialog.cropped_pixmap, custom_icon_name)
                else:
                    QMessageBox.warning(self, "提示", "拖入的文件不是有效的图片格式！")

    def process_and_install_icons(self, pixmap, custom_icon_name):
        icon_base_name = custom_icon_name.lower().replace(" ", "_") if custom_icon_name else "gimp"
        
        sizes = [16, 24, 22, 32, 48, 256]
        hicolor_dir = os.path.expanduser("~/.local/share/icons/hicolor")
        
        self.log(f"开始生成多尺寸图标，图标名称: {icon_base_name}")
        
        for size in sizes:
            size_str = f"{size}x{size}"
            target_folder = os.path.join(hicolor_dir, size_str, "apps")
            os.makedirs(target_folder, exist_ok=True)
            
            target_file_path = os.path.join(target_folder, f"{icon_base_name}.png")
            
            scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_pixmap.save(target_file_path, "PNG")
            
            self.log(f"-> 实际写入: {target_file_path}")
            
        self.line_edits["Icon"].setText(icon_base_name)
        self.log("✅ 所有尺寸图标分发成功！")
        QMessageBox.information(self, "成功", "多尺寸图标裁剪并分发到系统目录成功！")

    def clean_generated_icons(self):
        icon_base_name = self.line_edits["Icon"].text().strip()
        if not icon_base_name:
            QMessageBox.warning(self, "提示", "【Icon】字段为空，无法确定要删除的图标名称！")
            return
            
        sizes = [16, 24, 22, 32, 48, 256]
        hicolor_dir = os.path.expanduser("~/.local/share/icons/hicolor")
        
        deleted_count = 0
        for size in sizes:
            size_str = f"{size}x{size}"
            target_file_path = os.path.join(hicolor_dir, size_str, "apps", f"{icon_base_name}.png")
            if os.path.exists(target_file_path):
                try:
                    os.remove(target_file_path)
                    self.log(f"🗑️ 已删除: {target_file_path}")
                    deleted_count += 1
                except Exception as e:
                    self.log(f"❌ 删除失败 {target_file_path}: {str(e)}")
                    
        if deleted_count > 0:
            QMessageBox.information(self, "成功", f"成功清除了 {deleted_count} 个对应名称 '{icon_base_name}' 的系统图标文件！")
        else:
            QMessageBox.information(self, "提示", f"没有找到名称为 '{icon_base_name}.png' 的系统图标文件。")

    def _write_desktop_file(self, current_dir):
        for key, line_edit in self.line_edits.items():
            self.settings.setValue(key, line_edit.text())
            
        desktop_content = "[Desktop Entry]\n"
        for key, line_edit in self.line_edits.items():
            desktop_content += f"{key}={line_edit.text()}\n"
            
        name = self.line_edits["Name"].text().strip() or "NewApp"
        file_name = f"{name.replace(' ', '_')}.desktop"
        
        full_file_path = os.path.join(current_dir, file_name)
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(desktop_content)
            
        st = os.stat(full_file_path)
        os.chmod(full_file_path, st.st_mode | stat.S_IEXEC)
        
        return full_file_path, file_name

    def generate_desktop(self):
        current_dir = self.path_edit.text().strip()
        try:
            full_file_path, file_name = self._write_desktop_file(current_dir)
            self.log(f"成功生成 .desktop 文件到: {full_file_path}")
            QMessageBox.information(self, "成功", f"文件 '{file_name}' 已生成在：\n{full_file_path}")
        except Exception as e:
            self.log(f"❌ 生成文件失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"生成文件失败：\n{str(e)}")

    def generate_and_sync_to_system(self):
        current_dir = self.path_edit.text().strip()
        try:
            full_file_path, file_name = self._write_desktop_file(current_dir)
            
            user_app_dir = os.path.expanduser("~/.local/share/applications")
            os.makedirs(user_app_dir, exist_ok=True)
            target_path = os.path.join(user_app_dir, file_name)
            shutil.copy2(full_file_path, target_path)
            self.log(f"已同步 .desktop 到应用菜单目录: {target_path}")
            
            subprocess.Popen(["update-desktop-database", user_app_dir])
            
            name = self.line_edits["Name"].text().strip()
            self.log(f"✅ 系统应用菜单同步完成。")
            QMessageBox.information(self, "成功", 
                f"文件 '{file_name}' 已生成并同步到系统！\n\n"
                f"现在您可以在系统启动器中搜索 '{name}'，\n"
                f"或者在启动器中右键将其【固定到任务栏】！")
                
        except Exception as e:
            self.log(f"❌ 同步失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"生成并同步失败：\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopGenerator()
    window.show()
    sys.exit(app.exec_())
