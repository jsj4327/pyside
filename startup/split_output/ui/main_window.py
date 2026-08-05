import os
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QLineEdit, QPushButton,
    QDialog, QMessageBox, QButtonGroup
)
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont, QIcon
from PySide2.QtWidgets import QApplication

from ui.widgets.app_card import AppCard
from ui.dialogs.add_app_dialog import AddAppDialog
from core.data_manager import DataManager
from config.constants import (
    BASE_DIR, VIEW_ALL, VIEW_CATEGORY, VIEW_ALPHA,
    GRID_COLS, WINDOW_SCALE
)

class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python 脚本启动器")
        self.current_view = VIEW_ALL

        self.APPS = DataManager.load_data()

        self._setup_window()
        self._setup_logo()
        self._build_ui()

    def _setup_window(self):
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        w = int(geo.width() * WINDOW_SCALE)
        h = int(geo.height() * WINDOW_SCALE)
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
        logo_path = os.path.join(BASE_DIR, "startup.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
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
            self._create_view_button("全部", VIEW_ALL),
            self._create_view_button("分类", VIEW_CATEGORY),
            self._create_view_button("A-Z", VIEW_ALPHA),
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
            if DataManager.save_data(self.APPS):
                self._refresh_grid(self.search_edit.text().strip().lower())
            else:
                QMessageBox.warning(self, "保存失败", "无法保存数据")

    def _on_delete_app(self, app_name):
        reply = QMessageBox.question(
            self, "删除记录", f"确定要移除 【{app_name}】 吗？\n(仅移除快捷方式，不删源文件)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.APPS = [app for app in self.APPS if app["name"] != app_name]
            if DataManager.save_data(self.APPS):
                self._refresh_grid(self.search_edit.text().strip().lower())
            else:
                QMessageBox.warning(self, "保存失败", "无法保存数据")

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

        if self.current_view == VIEW_CATEGORY:
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
                    row, col = divmod(idx, GRID_COLS)
                    grid_layout.addWidget(card, row, col)

                self.main_container_layout.addWidget(grid_widget)
        else:
            sorted_apps = sorted(apps, key=lambda a: a["name"]) if self.current_view == VIEW_ALPHA else apps

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
                row, col = divmod(idx, GRID_COLS)
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
