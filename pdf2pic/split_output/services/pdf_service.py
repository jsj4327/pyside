"""
PDF 服务模块 (PDF Service)
封装 pdf2image 解析、QPixmap 转换以及缩略图生成功能。
已启用多核心并行渲染加速 (thread_count)。
"""
import os
from typing import List
from PIL import Image
from PySide2.QtGui import QPixmap, QImage, QIcon
from PySide2.QtCore import Qt, QSize

from pdf2image import convert_from_path

from config import THUMBNAIL_ITEM_SIZE


def load_pdf_images(pdf_path: str, dpi: int = 150) -> List[Image.Image]:
    """
    使用 pdf2image 多核心并行加载 PDF 文件的所有页面为 PIL Image 列表。
    通过设置 thread_count 充分利用多核 CPU 性能，大幅提升加载速度。
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    # 自动获取当前 CPU 核心数进行多线程并行渲染
    cpu_cores = os.cpu_count() or 4
    
    # 调用 pdf2image 转换，传入 thread_count 开启底层并行加速
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        thread_count=cpu_cores
    )
    return images


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    """将 PIL Image 转换为 PySide2 QPixmap"""
    if image.mode == "RGBA":
        r, g, b, a = image.split()
        img = Image.merge("RGBA", (b, g, r, a))
        im_data = img.tobytes("raw", "RGBA")
        qim = QImage(im_data, image.width, image.height, QImage.Format_ARGB32)
    else:
        rgb = image.convert("RGB")
        r, g, b = rgb.split()
        img = Image.merge("RGB", (b, g, r))
        im_data = img.tobytes("raw", "RGB")
        qim = QImage(im_data, image.width, image.height, QImage.Format_RGB888)
    
    return QPixmap.fromImage(qim)


def create_thumbnail_icon(image: Image.Image, size: tuple = THUMBNAIL_ITEM_SIZE) -> QIcon:
    """快速生成符合列表尺寸的图标"""
    pixmap = pil_to_pixmap(image)
    scaled = pixmap.scaled(
        size[0] - 20, size[1] - 20,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )
    return QIcon(scaled)