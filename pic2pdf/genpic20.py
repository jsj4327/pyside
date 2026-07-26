import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('images', exist_ok=True)

# 自动寻找 Linux 系统中可用的常见大字体路径
font_paths = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # 文泉驿黑体
    'arial.ttf'
]

selected_font_path = None
for path in font_paths:
    if os.path.exists(path):
        selected_font_path = path
        break

for i in range(1, 21):
    img = Image.new('RGB', (400, 400), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    text = str(i)
    
    # 字体大小设为 320
    if selected_font_path:
        font = ImageFont.truetype(selected_font_path, 320)
    else:
        font = ImageFont.load_default()

    # 兼容旧版本 Pillow 的文字居中计算
    if hasattr(d, "textbbox"):
        bbox = d.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (400 - w) / 2 - bbox[0]
        y = (400 - h) / 2 - bbox[1]
    else:
        w, h = d.textsize(text, font=font)
        x = (400 - w) / 2
        y = (400 - h) / 2

    d.text((x, y), text, fill=(50, 50, 50), font=font)
    img.save(f'images/{i}.jpg', 'JPEG')

print('20张大字图片生成完毕！')
