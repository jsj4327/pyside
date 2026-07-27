# -*- coding: utf-8 -*-
# 文件: settings.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PySide2.QtCore import QSettings

class SettingsManager:
    """全局配置管理器，封装 QSettings 的读写操作"""
    SETTINGS_FILE = "project_builder_v2.ini"

    @classmethod
    def get_recent_project(cls) -> str:
        settings = QSettings(cls.SETTINGS_FILE, QSettings.IniFormat)
        return settings.value("recent_project", "")

    @classmethod
    def set_recent_project(cls, path: str):
        settings = QSettings(cls.SETTINGS_FILE, QSettings.IniFormat)
        settings.setValue("recent_project", path)

    @classmethod
    def get_window_geometry(cls) -> dict:
        settings = QSettings(cls.SETTINGS_FILE, QSettings.IniFormat)
        return {
            "width": settings.value("window_width", 1200, type=int),
            "height": settings.value("window_height", 800, type=int)
        }

    @classmethod
    def set_window_geometry(cls, width: int, height: int):
        settings = QSettings(cls.SETTINGS_FILE, QSettings.IniFormat)
        settings.setValue("window_width", width)
        settings.setValue("window_height", height)