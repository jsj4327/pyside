from PySide2.QtWidgets import QFrame, QVBoxLayout, QLabel, QMenu, QMessageBox
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont, QPixmap
import os
from utils.path_utils import get_absolute_path
from core.app_launcher import AppLauncher

class AppCard(QFrame):
    """单个应用卡片组件"""
    delete_requested = Signal(str)

    def __init__(self, app_name: str, icon_path: str = None, exe_path: str = None, description: str = "", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.exe_path = exe_path
        self.description = description
        self.setFixedSize(140, 160)
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

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(56, 56)
        self.icon_label.setAlignment(Qt.AlignCenter)

        absolute_icon_path = get_absolute_path(icon_path) if icon_path else None
        if absolute_icon_path and os.path.isfile(absolute_icon_path):
            pixmap = QPixmap(absolute_icon_path).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText("🐍")
            self.icon_label.setFont(QFont("Noto Sans CJK SC", 24))
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)

        self.name_label = QLabel(app_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(False)
        self.name_label.setMaximumWidth(124)
        self.name_label.setFont(QFont("Noto Sans CJK SC", 10, QFont.Bold))
        self.name_label.setStyleSheet("color: #2D3748; background: transparent;")
        self.name_label.setText(self._truncate_text(app_name, 12))
        layout.addWidget(self.name_label, alignment=Qt.AlignCenter)

        self.desc_label = QLabel()
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumWidth(124)
        self.desc_label.setFixedHeight(30)
        font = QFont("Noto Sans CJK SC", 9, QFont.Bold)
        self.desc_label.setFont(font)
        self.desc_label.setStyleSheet("color: #4A5568; background: transparent; line-height: 1.2;")

        if description:
            lines = description.split('\n')
            if len(lines) > 2:
                description = '\n'.join(lines[:2])
            truncated_lines = []
            for line in description.split('\n')[:2]:
                truncated_lines.append(self._truncate_text(line, 15))
            self.desc_label.setText('\n'.join(truncated_lines))
        else:
            self.desc_label.hide()
        layout.addWidget(self.desc_label, alignment=Qt.AlignCenter)

        layout.addStretch()

    def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            return text[:max_length-1] + "…"
        return text

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._launch_app()
        super().mousePressEvent(event)

    def _launch_app(self):
        success, msg = AppLauncher.launch(self.exe_path)
        if not success:
            QMessageBox.information(self, "应用提示", f"【{self.app_name}】 {msg}")

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
