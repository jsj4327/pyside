"""
图片导出服务 (Export Service)
提供完整的 PDF 页面导出功能，支持：
- 批量导出为 PNG / JPG 格式
- 自动处理 RGBA 到 RGB 的透明通道背景填充（适配 JPEG）
- 单张图片独立导出
- 导出文件名与格式解析
"""
import os
from typing import List, Tuple, Optional
from PIL import Image

from config import EXPORT_JPEG_QUALITY


def export_images(
    images: List[Image.Image],
    folder_path: str,
    base_name: str = "page_",
    ext: str = ".png",
    quality: int = EXPORT_JPEG_QUALITY
) -> List[str]:
    """
    批量导出 PIL 图像列表到指定文件夹。
    
    :param images: PIL 图像对象列表
    :param folder_path: 目标文件夹路径
    :param base_name: 文件名前缀
    :param ext: 扩展名（如 '.png', '.jpg'）
    :param quality: JPEG 压缩质量 (1-100)
    :return: 成功导出的文件路径列表
    """
    if not os.path.isdir(folder_path):
        raise IOError(f"目标文件夹不存在或无效: {folder_path}")

    if not images:
        raise ValueError("没有可导出的图像数据")

    saved_paths = []
    is_jpeg = ext.lower() in (".jpg", ".jpeg")
    
    for i, img in enumerate(images):
        # 构造保存文件名，页码从 1 开始
        file_name = f"{base_name}{i + 1}{ext}"
        save_path = os.path.join(folder_path, file_name)

        # 处理 JPEG 格式的透明通道兼容性问题（RGBA转RGB，填充白色背景）
        target_img = img
        if is_jpeg:
            if target_img.mode != "RGB":
                background = Image.new("RGB", target_img.size, (255, 255, 255))
                if target_img.mode in ("RGBA", "LA", "PA"):
                    # 如果有透明通道，利用 alpha 通道作为 mask 粘贴
                    try:
                        background.paste(target_img, mask=target_img.split()[-1])
                    except Exception:
                        background.paste(target_img.convert("RGB"))
                else:
                    background.paste(target_img.convert("RGB"))
                target_img = background
            
            target_img.save(save_path, "JPEG", quality=quality)
        else:
            # PNG 格式直接保存
            target_img.save(save_path, "PNG")
            
        saved_paths.append(save_path)

    return saved_paths


def export_single_image(
    image: Image.Image,
    save_path: str,
    quality: int = EXPORT_JPEG_QUALITY
) -> str:
    """
    导出单张 PIL 图像到指定绝对路径。
    
    :param image: PIL 图像对象
    :param save_path: 完整保存文件路径
    :param quality: JPEG 压缩质量
    :return: 保存后的文件路径
    """
    directory = os.path.dirname(save_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    ext = os.path.splitext(save_path)[1].lower()
    is_jpeg = ext in (".jpg", ".jpeg")

    target_img = image
    if is_jpeg:
        if target_img.mode != "RGB":
            background = Image.new("RGB", target_img.size, (255, 255, 255))
            if target_img.mode in ("RGBA", "LA", "PA"):
                try:
                    background.paste(target_img, mask=target_img.split()[-1])
                except Exception:
                    background.paste(target_img.convert("RGB"))
            else:
                background.paste(target_img.convert("RGB"))
            target_img = background
        target_img.save(save_path, "JPEG", quality=quality)
    else:
        target_img.save(save_path, "PNG")

    return save_path


def parse_export_format(format_choice: str) -> Tuple[str, str]:
    """
    解析保存文件对话框返回的完整路径，提取基础名称和扩展名。
    
    :param format_choice: QFileDialog.getSaveFileName 返回的文件路径
    :return: (base_name, ext) 元组，例如 ("page_", ".png")
    """
    base_name = "page_"
    ext = ".png"

    if format_choice:
        name_part = os.path.basename(format_choice)
        root, file_ext = os.path.splitext(name_part)
        if root:
            # 去除用户可能不小心带上的数字后缀，保持规范
            base_name = root
        if file_ext.lower() in (".jpg", ".jpeg"):
            ext = ".jpg"
        elif file_ext.lower() == ".png":
            ext = ".png"

    return base_name, ext