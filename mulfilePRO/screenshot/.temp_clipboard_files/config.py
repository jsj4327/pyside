# -*- coding: utf-8 -*-
# 文件: config.py

from PySide2.QtCore import QSettings

class AppConfig:
    def __init__(self):
        # 初始化 QSettings，指定组织名和应用名
        self.settings = QSettings("KylinTools", "ScreenShotApp")

    def get_use_border(self) -> bool:
        return self.settings.value("use_border", False, type=bool)

    def set_use_border(self, value: bool):
        self.settings.setValue("use_border", value)

    def get_border_width(self) -> int:
        return self.settings.value("border_width", 2, type=int)

    def set_border_width(self, value: int):
        self.settings.setValue("border_width", value)

    def get_use_shadow(self) -> bool:
        return self.settings.value("use_shadow", True, type=bool)

    def set_use_shadow(self, value: bool):
        self.settings.setValue("use_shadow", value)

    def get_use_editor(self) -> bool:
        return self.settings.value("use_editor", True, type=bool)

    def set_use_editor(self, value: bool):
        self.settings.setValue("use_editor", value)