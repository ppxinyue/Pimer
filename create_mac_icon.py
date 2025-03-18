import os
import subprocess
from PIL import Image
import tempfile

def create_icns_from_ico(ico_path, icns_path):
    """将ICO文件转换为ICNS文件"""
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 打开ICO文件
            img = Image.open(ico_path)
            
            # 创建iconset目录
            iconset_dir = os.path.join(temp_dir, 'icon.iconset')
            os.makedirs(iconset_dir, exist_ok=True)
            
            # 生成不同尺寸的图标
            sizes = [16, 32, 64, 128, 256, 512, 1024]
            for size in sizes:
                # 调整图片大小
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                # 保存为PNG
                resized.save(os.path.join(iconset_dir, f'icon_{size}x{size}.png'))
                # 保存2x版本
                if size <= 512:
                    resized.save(os.path.join(iconset_dir, f'icon_{size//2}x{size//2}@2x.png'))
            
            # 使用iconutil创建icns文件
            subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', icns_path], check=True)
            
            print(f"成功创建ICNS文件: {icns_path}")
            return True
            
    except Exception as e:
        print(f"创建ICNS文件失败: {e}")
        return False

def main():
    # 检查输入文件
    ico_path = 'pig_nose_icon.ico'
    icns_path = 'pig_nose_icon.icns'
    
    if not os.path.exists(ico_path):
        print(f"错误: 找不到ICO文件: {ico_path}")
        return False
    
    # 创建ICNS文件
    return create_icns_from_ico(ico_path, icns_path)

if __name__ == "__main__":
    main() 