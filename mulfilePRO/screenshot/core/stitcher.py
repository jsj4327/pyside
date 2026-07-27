import io
from PIL import Image, ImageChops
from PySide2.QtCore import Qt, QRect
from PySide2.QtGui import QPainter, QPen, QColor, QImage, QPixmap

class ImageStitcher:
    """图像处理与长图拼接算法引擎"""

    @staticmethod
    def grab_region_image(pixmap: QPixmap, rect: QRect) -> Image:
        """将 QPixmap 指定区域转换为 PIL Image"""
        cropped_pixmap = pixmap.copy(rect)
        qimage = cropped_pixmap.toImage().convertToFormat(QImage.Format_RGB888)
        img_bytes = bytes(qimage.constBits())
        pil_img = Image.frombytes(
            "RGB", 
            (qimage.width(), qimage.height()), 
            img_bytes, 
            "raw", 
            "RGB", 
            qimage.bytesPerLine()
        )
        return pil_img

    @staticmethod
    def find_best_overlap(img1: Image, img2: Image) -> int:
        """精准计算两张图的重叠行数"""
        h1, h2 = img1.height, img2.height
        search_max = int(h2 * 0.8)
        if search_max < 5:
            return 0
        
        best_y = 0
        min_diff_val = float('inf')
        strip_h = min(20, h1)
        strip1 = img1.crop((0, h1 - strip_h, img1.width, h1))
        
        for y in range(0, search_max - strip_h):
            strip2 = img2.crop((0, y, img2.width, y + strip_h))
            diff_ext = ImageChops.difference(strip1, strip2).convert("L").getextrema()
            total_diff = diff_ext[1] if diff_ext else 0
            if total_diff < min_diff_val:
                min_diff_val = total_diff
                best_y = y

        return (best_y + strip_h) if min_diff_val < 80 else int(h2 * 0.25)

    @staticmethod
    def apply_border_and_shadow(cropped: QPixmap, use_border: bool, border_width: int, use_shadow: bool, corner_radius: int = 8) -> QImage:
        """为截图添加自定义描边和阴影美化效果"""
        # 1. 描边处理
        if use_border:
            p_border = QPainter(cropped)
            p_border.setRenderHint(QPainter.Antialiasing, True)
            w = border_width
            pen = QPen(QColor(255, 0, 0), w)
            p_border.setPen(pen)
            p_border.setBrush(Qt.NoBrush)
            draw_rect = cropped.rect().adjusted(w // 2, w // 2, -w // 2, -w // 2)
            p_border.drawRect(draw_rect)
            p_border.end()

        # 2. 阴影处理
        if use_shadow:
            shadow_margin = 16  
            offset_x = 4        
            offset_y = 4        
            
            new_width = cropped.width() + shadow_margin + offset_x
            new_height = cropped.height() + shadow_margin + offset_y
            final_image = QImage(new_width, new_height, QImage.Format_ARGB32)
            final_image.fill(Qt.transparent)  
            
            painter = QPainter(final_image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            for i in range(shadow_margin, 0, -1):
                alpha = int(35 * (1.0 - i / shadow_margin))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(0, 0, 0, alpha))
                
                shadow_rect = QRect(
                    2 + offset_x,             
                    2 + offset_y,             
                    cropped.width() + i,      
                    cropped.height() + i      
                )
                painter.drawRoundedRect(shadow_rect, corner_radius, corner_radius)
            
            painter.drawImage(2, 2, cropped.toImage())
            painter.end()
            return final_image
        else:
            return cropped.toImage()