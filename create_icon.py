from PIL import Image, ImageDraw, ImageFont
import os

def create_pig_nose_icon():
    """创建一个猪鼻子图标并保存为ico文件"""
    # 创建一个透明背景的图像
    size = 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 设置颜色
    pink_color = (255, 192, 203, 255)  # 粉红色
    dark_pink = (219, 112, 147, 255)   # 深粉红色
    
    # 绘制圆形背景
    draw.ellipse((0, 0, size, size), fill=pink_color)
    
    # 绘制猪鼻子
    # 主鼻子椭圆
    nose_width = size * 0.7
    nose_height = size * 0.6
    nose_left = (size - nose_width) / 2
    nose_top = (size - nose_height) / 2
    draw.ellipse(
        (nose_left, nose_top, nose_left + nose_width, nose_top + nose_height), 
        fill=dark_pink
    )
    
    # 鼻孔
    nostril_size = size * 0.15
    nostril_y = nose_top + nose_height * 0.4
    
    # 左鼻孔
    left_nostril_x = nose_left + nose_width * 0.25
    draw.ellipse(
        (left_nostril_x, nostril_y, left_nostril_x + nostril_size, nostril_y + nostril_size),
        fill=(0, 0, 0, 200)
    )
    
    # 右鼻孔
    right_nostril_x = nose_left + nose_width * 0.65
    draw.ellipse(
        (right_nostril_x, nostril_y, right_nostril_x + nostril_size, nostril_y + nostril_size),
        fill=(0, 0, 0, 200)
    )
    
    # 保存为ico文件
    icon_path = "pig_nose_icon.ico"
    # 创建不同尺寸的图标
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for s in sizes:
        images.append(image.resize((s, s), Image.LANCZOS))
    
    # 保存ico文件
    images[0].save(icon_path, format='ICO', sizes=[(s, s) for s in sizes])
    
    print(f"图标已保存为: {os.path.abspath(icon_path)}")
    return icon_path

if __name__ == "__main__":
    create_pig_nose_icon() 