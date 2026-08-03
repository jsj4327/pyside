# -*- coding:utf-8 -*-
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 窗口图标
ICON_FILE = os.path.join(BASE_DIR, "p.png")

# 窗口占屏幕比例
WINDOW_SCALE_RATIO = 0.85

# 支持的文本后缀
TEXT_FILE_SUFFIX = {
    ".txt", ".py", ".pyw", ".md", ".json", ".yaml", ".yml", 
    ".html", ".css", ".js", ".vue", ".java", ".c", ".cpp", 
    ".h", ".sql", ".sh", ".bash", ".ini", ".csv"
}

# 编码读取优先级
CODEC_PRIORITY = ["utf-8", "gbk", "gb2312"]
