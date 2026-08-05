"""PDF导出服务"""
from typing import List, Tuple, Union
from PIL import Image


class PdfExporter:
    """处理图片格式转换与多页PDF生成"""

    @staticmethod
    def export(image_data: List[Union[str, Tuple[str, int]]], output_path: str) -> None:
        """
        将图片列表导出为PDF文件
        :param image_data: 图片数据列表，每项可以是路径字符串或(路径, 旋转角度)元组
        :param output_path: 输出PDF文件路径
        :raises Exception: 导出失败时抛出异常
        """
        if not image_data:
            raise ValueError("没有可导出的图片")

        images = []
        for entry in image_data:
            if isinstance(entry, tuple):
                path, rotation = entry
            else:
                path = entry
                rotation = 0

            img = Image.open(path)

            # 应用旋转
            if rotation != 0:
                # PIL的rotate是逆时针，而我们的约定是顺时针，所以取负
                img = img.rotate(-rotation, expand=True)

            # 处理透明通道
            if (img.mode in ("RGBA", "LA") or
                    (img.mode == "P" and "transparency" in img.info)):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.convert("RGBA").split()[3])
                img = background
            else:
                img = img.convert("RGB")
            images.append(img)

        first_img = images[0]
        rest_imgs = images[1:] if len(images) > 1 else []
        first_img.save(
            output_path,
            "PDF",
            save_all=True,
            append_images=rest_imgs
        )