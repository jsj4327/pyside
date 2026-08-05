"""
全局配置常量模块
集中管理默认DPI、缩放范围、临时文件前缀及支持格式等。
"""

# PDF 转换默认 DPI
DEFAULT_DPI = 200

# 预览区缩放限制
MIN_SCALE = 0.2
MAX_SCALE = 5.0
ZOOM_FACTOR = 1.15

# 缩略图尺寸
THUMBNAIL_SIZE = 100
THUMBNAIL_ITEM_SIZE = (120, 110)

# 拖拽自动滚动边缘阈值（像素）
DRAG_SCROLL_MARGIN = 30
DRAG_SCROLL_SPEED = 15

# 导出图片默认质量 (JPEG)
EXPORT_JPEG_QUALITY = 95

# 支持的导出格式
SUPPORTED_FORMATS = ["PNG", "JPG"]

# 窗口初始大小比例
WINDOW_SIZE_RATIO = 0.8

# UI 样式常量
STYLE_BTN_PRIMARY = "background-color: #0078d7; color: white; font-weight: bold;"
STYLE_BTN_BOLD = "font-weight: bold;"
STYLE_STATUS_LABEL = "color: #555; font-size: 11px;"
STYLE_PREVIEW_AREA = "background-color: #f0f0f0; border: 1px solid #ccc; color: #666;"