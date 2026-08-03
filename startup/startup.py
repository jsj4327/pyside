import sys
import os
import json
import subprocess
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                               QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QScrollArea, QLineEdit, QPushButton, QDialog,
                               QMessageBox, QMenu, QButtonGroup, QComboBox,
                               QTextEdit)
from PySide2.QtCore import Qt, Signal, QMimeData
from PySide2.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent, QIcon

# 定义本地数据存储文件
DATA_FILE = "launcher_apps.json"
# 获取程序所在目录作为基准路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class DropZone(QFrame):
    """通用拖放接收区域"""
    pathDropped = Signal(str)  # 新增信号：拖入文件后发送路径

    def __init__(self, hint_text: str, accept_mode: str = "all", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(200, 110)
        self.hint_text = hint_text
        self.accept_mode = accept_mode
        self.current_path = None

        self._default_style = """
            DropZone {
                border: 2px dashed rgba(255,255,255,0.2);
                border-radius: 12px;
                background-color: rgba(255,255,255,0.03);
            }
        """
        self._hover_style = """
            DropZone {
                border: 2px dashed #3B82F6;
                border-radius: 12px;
                background-color: rgba(59,130,246,0.08);
            }
        """
        self.setStyleSheet(self._default_style)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        # 使用 QLabel 显示提示文字和预览图
        self.preview_label = QLabel(hint_text)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFont(QFont("Noto Sans CJK SC", 10))
        self.preview_label.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent;")
        self.preview_label.setWordWrap(True)
        # 设置最小高度，确保有足够空间显示预览图
        self.preview_label.setMinimumHeight(80)
        layout.addWidget(self.preview_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and self._is_valid(event.mimeData()):
            event.acceptProposedAction()
            self.setStyleSheet(self._hover_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._default_style)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self._default_style)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._validate(path):
                self.current_path = path
                self._update_preview(path)
                self.pathDropped.emit(path)  # 抛出信号

    def _is_valid(self, mime: QMimeData) -> bool:
        urls = mime.urls()
        if not urls:
            return False
        path = urls[0].toLocalFile()
        return self._validate(path)

    def _validate(self, path: str) -> bool:
        """核心修改：增加文件后缀名判定"""
        if not os.path.isfile(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if self.accept_mode == "exe":
            return ext in [".py", ".pyw"]
        elif self.accept_mode == "image":
            return ext in [".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".gif"]
        return True

    def _update_preview(self, path: str):
        name = os.path.basename(path)
        if self.accept_mode == "image":
            # 强化图片预览：在控件内显示缩放后的图片
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # 根据 DropZone 的可用空间缩放图片
                available_width = self.width() - 20  # 减去边距
                available_height = self.height() - 20
                scaled_pixmap = pixmap.scaled(
                    available_width,
                    available_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                self.preview_label.setStyleSheet("background: transparent; border: none;")
            else:
                # 如果图片无法加载，显示文件名
                self.preview_label.setText(f"⚠️ 无法加载: {name}")
                self.preview_label.setStyleSheet("color: #F87171; background: transparent;")
        else:
            # 对于 .py 文件，显示文件名
            self.preview_label.clear()
            self.preview_label.setText(f"✅ {name}")
            self.preview_label.setStyleSheet("color: #4ADE80; background: transparent; font-weight: bold;")


class AddAppDialog(QDialog):
    """添加应用对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新程序")
        # 增加弹窗高度以容纳名称输入框
        self.setFixedSize(420, 730)
        self.result_data = None

        self.setStyleSheet("""
            QDialog { background-color: #2A2A3E; }
            QLabel { color: #D0D0D0; background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("添加新 Python 程序")
        title.setFont(QFont("Noto Sans CJK SC", 14, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; margin-bottom: 4px;")
        layout.addWidget(title)

        # ========== 新增：自定义程序名称输入框 ==========
        lbl_name = QLabel("程序名称（可自定义）")
        lbl_name.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_name)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("拖入py文件将自动填充名称，也可以手动修改")
        self.name_edit.setFixedHeight(38)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px 10px;
                color: white;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; }
        """)
        layout.addWidget(self.name_edit)

        lbl_exe = QLabel("① 拖入 .py 文件")
        lbl_exe.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_exe)
        self.drop_exe = DropZone("将 Python 脚本拖放到此处", accept_mode="exe")
        # 绑定拖入信号，自动填充名称
        self.drop_exe.pathDropped.connect(self._on_py_file_drop)
        layout.addWidget(self.drop_exe)

        lbl_icon = QLabel("② 拖入图标文件 (.png / .svg / .ico)")
        lbl_icon.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_icon)
        self.drop_icon = DropZone("将图标拖放到此处（可选）", accept_mode="image")
        layout.addWidget(self.drop_icon)

        # ====== 分类选择下拉框 ======
        lbl_cat = QLabel("③ 选择或输入分类")
        lbl_cat.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_cat)

        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.lineEdit().setPlaceholderText("选择或输入新分类...")
        self.cat_combo.addItems(["我的脚本", "系统工具", "数据处理", "自动化", "开发测试", "其他"])
        self.cat_combo.setFixedHeight(38)
        self.cat_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px 10px;
                color: white;
            }
            QComboBox:focus { border: 1px solid #3B82F6; }
            QComboBox QAbstractItemView {
                background-color: #2A2A3E;
                color: white;
                selection-background-color: #3B82F6;
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
            }
        """)
        layout.addWidget(self.cat_combo)

        # ====== 中文说明输入框（多行） ======
        lbl_desc = QLabel("④ 中文说明（可选，最多2行）")
        lbl_desc.setFont(QFont("Noto Sans CJK SC", 9))
        layout.addWidget(lbl_desc)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("输入程序的中文说明...\n支持换行，最多显示2行")
        self.desc_edit.setFixedHeight(60)
        self.desc_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 8px 12px;
                color: #E0E0E0;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #3B82F6;
                background-color: rgba(255,255,255,0.12);
            }
        """)
        layout.addWidget(self.desc_edit)

        layout.addStretch() # 把下方空白顶开

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.08); color: #A0A0A0; border-radius: 6px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); color: #E0E0E0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确定添加")
        confirm_btn.setFixedSize(100, 36)
        confirm_btn.setStyleSheet("""
            QPushButton { background-color: #3B82F6; color: white; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_py_file_drop(self, file_path):
        """拖入py文件，自动填充程序名称"""
        filename = os.path.splitext(os.path.basename(file_path))[0]
        self.name_edit.setText(filename)

    def _get_relative_path(self, absolute_path: str) -> str:
        """将绝对路径转换为相对于程序目录的路径"""
        try:
            return os.path.relpath(absolute_path, BASE_DIR)
        except ValueError:
            # 如果在不同驱动器上（Windows），无法计算相对路径，则返回绝对路径
            return absolute_path

    def _on_confirm(self):
        exe_path = self.drop_exe.current_path
        icon_path = self.drop_icon.current_path

        # 获取自定义名称
        app_name = self.name_edit.text().strip()
        category_text = self.cat_combo.currentText().strip()
        if not category_text:
            category_text = "未分类"

        # 获取中文说明
        description = self.desc_edit.toPlainText().strip()

        if not exe_path:
            QMessageBox.warning(self, "提示", "请先拖入一个 Python 脚本文件 (.py)")
            return
        if not app_name:
            QMessageBox.warning(self, "提示", "请填写程序名称！")
            return

        # 转换为相对路径
        relative_exe_path = self._get_relative_path(exe_path)
        relative_icon_path = self._get_relative_path(icon_path) if icon_path else None

        self.result_data = {
            "name": app_name,
            "icon": relative_icon_path,
            "exe_path": relative_exe_path,
            "category": category_text,
            "description": description
        }
        self.accept()


class AppCard(QFrame):
    """单个应用卡片组件"""
    delete_requested = Signal(str)

    def __init__(self, app_name: str, icon_path: str = None, exe_path: str = None, description: str = "", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.exe_path = exe_path
        self.description = description
        self.setFixedSize(140, 160)  # 增加高度以容纳2行说明文字
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("appCard")

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setStyleSheet("""
            #appCard {
                background-color: transparent;
                border-radius: 12px;
                padding: 10px;
            }
            #appCard:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # 图标区域
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(56, 56)  # 稍微缩小图标以腾出空间
        self.icon_label.setAlignment(Qt.AlignCenter)

        # 处理图标路径（可能是相对路径）
        absolute_icon_path = self._get_absolute_path(icon_path) if icon_path else None
        if absolute_icon_path and os.path.isfile(absolute_icon_path):
            pixmap = QPixmap(absolute_icon_path).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText("🐍")
            self.icon_label.setFont(QFont("Noto Sans CJK SC", 24))
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)

        # 程序名称（单行，不换行）
        self.name_label = QLabel(app_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(False)  # 不换行
        self.name_label.setMaximumWidth(124)
        self.name_label.setFont(QFont("Noto Sans CJK SC", 10, QFont.Bold))
        self.name_label.setStyleSheet("color: #2D3748; background: transparent;")
        # 如果名字太长，用省略号显示
        self.name_label.setText(self._truncate_text(app_name, 12))
        layout.addWidget(self.name_label, alignment=Qt.AlignCenter)

        # 中文说明（最多2行）
        self.desc_label = QLabel()
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumWidth(124)
        self.desc_label.setFixedHeight(30)  # 固定高度容纳2行
        font = QFont("Noto Sans CJK SC", 9, QFont.Bold)  # 加粗字体
        self.desc_label.setFont(font)
        self.desc_label.setStyleSheet("color: #4A5568; background: transparent; line-height: 1.2;")

        if description:
            # 限制显示2行，超出部分截断
            lines = description.split('\n')
            if len(lines) > 2:
                description = '\n'.join(lines[:2])
            # 每行最多显示一定字符数
            truncated_lines = []
            for line in description.split('\n')[:2]:
                truncated_lines.append(self._truncate_text(line, 15))
            self.desc_label.setText('\n'.join(truncated_lines))
        else:
            self.desc_label.hide()
        layout.addWidget(self.desc_label, alignment=Qt.AlignCenter)

        layout.addStretch()

    def _truncate_text(self, text, max_length):
        """截断文本，超出长度用省略号"""
        if len(text) > max_length:
            return text[:max_length-1] + "…"
        return text

    def _get_absolute_path(self, relative_path: str) -> str:
        """将相对路径转换为绝对路径"""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(BASE_DIR, relative_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._launch_app()
        super().mousePressEvent(event)

    def _launch_app(self):
        # 获取脚本的绝对路径
        absolute_exe_path = self._get_absolute_path(self.exe_path)
        if not absolute_exe_path or not os.path.exists(absolute_exe_path):
            QMessageBox.information(self, "应用提示", f"【{self.app_name}】 路径无效或文件不存在。\n路径: {absolute_exe_path}")
            return

        try:
            # 获取脚本所在目录
            script_dir = os.path.dirname(absolute_exe_path)

            # 使用 subprocess.Popen 启动脚本，设置工作目录为脚本所在目录
            # 这样脚本中的 __file__ 和 os.getcwd() 都能正确指向脚本所在目录
            if sys.platform == "win32":
                # Windows 系统
                subprocess.Popen(
                    ['python', absolute_exe_path],
                    cwd=script_dir,  # 设置工作目录
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.stdout else 0
                )
            else:
                # Linux/Mac 系统
                subprocess.Popen(
                    ['python3', absolute_exe_path],
                    cwd=script_dir  # 设置工作目录
                )
        except Exception as e:
            QMessageBox.warning(self, "启动失败", f"无法启动程序：\n{str(e)}")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2A2A3E; color: #D0D0D0; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #3B82F6; color: white; }
        """)

        open_action = menu.addAction("🚀 运行脚本")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除记录")

        action = menu.exec_(self.mapToGlobal(pos))

        if action == open_action:
            self._launch_app()
        elif action == delete_action:
            self.delete_requested.emit(self.app_name)


class LauncherWindow(QMainWindow):
    COLS = 5
    SCALE = 0.85
    VIEW_ALL = "all"
    VIEW_CATEGORY = "category"
    VIEW_ALPHA = "alpha"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 脚本启动器")
        self.current_view = self.VIEW_ALL

        self.APPS = []
        self._load_data()

        self._setup_window()
        self._setup_logo()  # 设置应用图标
        self._build_ui()

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.APPS = json.load(f)
            except Exception as e:
                print(f"读取数据失败: {e}")

    def _save_data(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.APPS, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存数据:\n{e}")

    def _setup_window(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        w = int(geo.width() * self.SCALE)
        h = int(geo.height() * self.SCALE)
        x = geo.x() + (geo.width() - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        self.setGeometry(x, y, w, h)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E2E; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 4px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.4); }
        """)

    def _setup_logo(self):
        """设置应用程序图标（仅用于系统窗口图标和任务栏图标）"""
        logo_path = os.path.join(BASE_DIR, "startup.png")
        if os.path.exists(logo_path):
            # 设置窗口图标（标题栏图标）
            self.setWindowIcon(QIcon(logo_path))
            # 设置应用程序级别的图标（任务栏图标）
            QApplication.instance().setWindowIcon(QIcon(logo_path))
        else:
            print(f"未找到logo文件: {logo_path}，将使用默认图标")

    def _build_top_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(70)
        top_bar.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(30, 15, 30, 15)
        layout.setSpacing(15)

        add_btn = QPushButton("+ 添加程序")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(38)
        add_btn.setStyleSheet("""
            QPushButton { background-color: #3B82F6; color: white; border-radius: 8px; padding: 0 18px; font-weight: bold; }
            QPushButton:hover { background-color: #2563EB; }
        """)
        add_btn.clicked.connect(self._open_add_dialog)
        layout.addWidget(add_btn)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索程序...")
        self.search_edit.setFixedHeight(38)
        # 修改搜索框样式，让占位文字颜色更浅
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 0 15px;
                color: #E0E0E0;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
                background-color: rgba(255,255,255,0.12);
            }
            QLineEdit::placeholder {
                color: rgba(255,255,255,0.3);
            }
        """)
        self.search_edit.textChanged.connect(self._on_search)
        layout.addWidget(self.search_edit, stretch=1)

        view_frame = QFrame()
        view_layout = QHBoxLayout(view_frame)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.view_buttons = [
            self._create_view_button("全部", self.VIEW_ALL),
            self._create_view_button("分类", self.VIEW_CATEGORY),
            self._create_view_button("A-Z", self.VIEW_ALPHA),
        ]

        for btn in self.view_buttons:
            self.btn_group.addButton(btn)
            view_layout.addWidget(btn)
            if btn.property("viewMode") == self.current_view:
                btn.setChecked(True)

        self.btn_group.buttonClicked.connect(self._on_view_changed)

        layout.addWidget(view_frame)
        return top_bar

    def _create_view_button(self, text, view_mode):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setFixedWidth(70)
        btn.setProperty("viewMode", view_mode)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A0A0A0;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.06);
                color: #E0E0E0;
            }
            QPushButton:checked {
                background-color: #3B82F6;
                color: white;
                border: none;
                font-weight: bold;
            }
        """)
        return btn

    def _on_view_changed(self, button):
        view_mode = button.property("viewMode")
        if view_mode != self.current_view:
            self.current_view = view_mode
            self._refresh_grid(self.search_edit.text().strip().lower())

    def _open_add_dialog(self):
        dlg = AddAppDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            if any(app["name"] == dlg.result_data["name"] for app in self.APPS):
                QMessageBox.warning(self, "重复添加", f"程序 '{dlg.result_data['name']}' 已存在！")
                return

            self.APPS.insert(0, dlg.result_data)
            self._save_data()
            self._refresh_grid(self.search_edit.text().strip().lower())

    def _on_delete_app(self, app_name):
        reply = QMessageBox.question(
            self, "删除记录", f"确定要移除 【{app_name}】 吗？\n(仅移除快捷方式，不删源文件)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.APPS = [app for app in self.APPS if app["name"] != app_name]
            self._save_data()
            self._refresh_grid(self.search_edit.text().strip().lower())

    def _build_app_grid(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.main_container_layout = QVBoxLayout(self.container)
        self.main_container_layout.setContentsMargins(30, 10, 30, 30)
        self.main_container_layout.setSpacing(20)
        self.main_container_layout.setAlignment(Qt.AlignTop)

        self._populate_content(self.APPS)
        scroll.setWidget(self.container)
        return scroll

    def _populate_content(self, apps):
        while self.main_container_layout.count():
            item = self.main_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not apps:
            lbl_empty = QLabel("暂无程序，点击上方按钮添加。")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet("color: #888888; font-size: 14px; margin-top: 50px;")
            self.main_container_layout.addWidget(lbl_empty)
            return

        if self.current_view == self.VIEW_CATEGORY:
            categories = {}
            for app in apps:
                cat = app.get("category", "未分类")
                categories.setdefault(cat, []).append(app)

            for cat_name, cat_apps in sorted(categories.items()):
                lbl_cat = QLabel(cat_name)
                lbl_cat.setFont(QFont("Noto Sans CJK SC", 12, QFont.Bold))
                lbl_cat.setStyleSheet("color: #93C5FD; margin-top: 15px; margin-bottom: 5px;")
                self.main_container_layout.addWidget(lbl_cat)

                grid_widget = QWidget()
                grid_layout = QGridLayout(grid_widget)
                grid_layout.setSpacing(12)
                grid_layout.setContentsMargins(0, 0, 0, 0)
                grid_layout.setAlignment(Qt.AlignLeft)

                for idx, app in enumerate(cat_apps):
                    card = AppCard(
                        app["name"],
                        app.get("icon"),
                        app.get("exe_path"),
                        app.get("description", "")
                    )
                    card.delete_requested.connect(self._on_delete_app)
                    row, col = divmod(idx, self.COLS)
                    grid_layout.addWidget(card, row, col)

                self.main_container_layout.addWidget(grid_widget)
        else:
            sorted_apps = sorted(apps, key=lambda a: a["name"]) if self.current_view == self.VIEW_ALPHA else apps

            grid_widget = QWidget()
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setSpacing(12)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            for idx, app in enumerate(sorted_apps):
                card = AppCard(
                    app["name"],
                    app.get("icon"),
                    app.get("exe_path"),
                    app.get("description", "")
                )
                card.delete_requested.connect(self._on_delete_app)
                row, col = divmod(idx, self.COLS)
                grid_layout.addWidget(card, row, col)

            self.main_container_layout.addWidget(grid_widget)

        self.main_container_layout.addStretch(1)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_grid(self, keyword):
        apps = self.APPS
        if keyword:
            # 搜索时同时匹配名称和说明
            apps = [a for a in apps if keyword in a["name"].lower() or keyword in a.get("description", "").lower()]
        self._populate_content(apps)

    def _on_search(self, text):
        self._refresh_grid(text.strip().lower())

    def _build_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._build_top_bar())
        main_layout.addWidget(self._build_app_grid(), stretch=1)
        self.setCentralWidget(central)

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    font = QFont("Noto Sans CJK SC", 10)
    if not font.exactMatch():
        font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = LauncherWindow()
    window.show()
    sys.exit(app.exec_())