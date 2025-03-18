import os
import sys
import shutil
from pathlib import Path
import platform
import subprocess
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
def setup_logging():
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'mac_build.log'
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    
    logger = logging.getLogger('MacBuild')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

def clean_build():
    """清理构建文件夹"""
    logger.info("正在清理构建文件夹...")
    dirs_to_clean = ['build', 'dist', 'mac_build']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    if os.path.exists('Pimer.spec'):
        os.remove('Pimer.spec')

def create_mac_icon():
    """创建Mac版本的图标文件"""
    logger.info("正在创建Mac图标...")
    
    # 检查是否已存在icns文件
    if os.path.exists('pig_nose_icon.icns'):
        logger.info("已存在Mac图标文件")
        return 'pig_nose_icon.icns'
    
    # 检查create_mac_icon.py是否存在
    if not os.path.exists('create_mac_icon.py'):
        logger.error("错误: 找不到create_mac_icon.py文件")
        sys.exit(1)
    
    # 检查PIL是否安装
    try:
        import PIL
    except ImportError:
        logger.error("错误: 未安装PIL库，请运行: pip install pillow")
        sys.exit(1)
    
    # 在Windows环境下，使用PIL直接生成ICNS文件
    if platform.system() == 'Windows':
        logger.info("在Windows环境下使用PIL生成ICNS文件...")
        try:
            from PIL import Image
            import tempfile
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 打开ICO文件
                img = Image.open('pig_nose_icon.ico')
                
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
                # 在Windows上，我们需要使用一个临时的icns文件
                # 这个文件会在Mac上被替换为真实的icns文件
                shutil.copy('pig_nose_icon.ico', 'pig_nose_icon.icns')
                logger.info("已创建临时ICNS文件")
                return 'pig_nose_icon.icns'
                
        except Exception as e:
            logger.error(f"在Windows上创建临时ICNS文件失败: {e}")
            sys.exit(1)
    
    # 在Mac环境下，使用iconutil创建真实的ICNS文件
    logger.info("在Mac环境下创建ICNS文件...")
    result = subprocess.run(['python', 'create_mac_icon.py'], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"创建Mac图标时出错: {result.stderr}")
        sys.exit(1)
    
    # 检查是否成功创建了icns文件
    if not os.path.exists('pig_nose_icon.icns'):
        logger.error("错误: 未能创建Mac图标文件")
        sys.exit(1)
    
    return 'pig_nose_icon.icns'

def check_required_files():
    """检查必需的文件是否存在"""
    logger.info("开始检查必需文件...")
    
    required_files = [
        'work_timer_cross_platform.py',
        'mac_adapter.py',
        'work_timer_mac.py',
        'pig_nose_icon.ico',
        'donate_qr.png',
        'sounds',
        '.env',
        'settings.json',
        'cloud_config.json',
        'LICENSE'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
            logger.warning(f"文件不存在: {file}")
        else:
            logger.info(f"文件存在: {file}")
    
    if missing_files:
        error_msg = f"错误: 以下必需文件缺失: {', '.join(missing_files)}"
        logger.error(error_msg)
        print(f"\n{error_msg}")  # 直接打印到控制台
        sys.exit(1)
    
    logger.info("所有必需文件检查完成")

def build_on_windows():
    """在Windows上准备Mac版本的文件"""
    try:
        logger.info("开始准备Mac版本文件...")
        
        # 清理旧的构建文件
        clean_build()
        
        # 创建Mac构建目录
        mac_build_dir = 'mac_build'
        if os.path.exists(mac_build_dir):
            shutil.rmtree(mac_build_dir)
        os.makedirs(mac_build_dir)
        
        # 检查必需文件
        check_required_files()
        
        # 复制所有必需文件到mac_build目录
        files_to_copy = [
            'work_timer_cross_platform.py',
            'mac_adapter.py',
            'work_timer_mac.py',
            'pig_nose_icon.ico',
            'donate_qr.png',
            '.env',
            'settings.json',
            'cloud_config.json',
            'LICENSE'
        ]
        
        # 复制文件
        for file in files_to_copy:
            if os.path.isfile(file):
                shutil.copy2(file, mac_build_dir)
            elif os.path.isdir(file):
                shutil.copytree(file, os.path.join(mac_build_dir, file))
        
        # 复制sounds目录
        if os.path.exists('sounds'):
            shutil.copytree('sounds', os.path.join(mac_build_dir, 'sounds'))
        
        logger.info("Mac版本文件准备完成！")
        logger.info("请将mac_build目录复制到Mac系统上，然后运行以下命令完成构建:")
        logger.info("  python build_mac.py")
        
    except Exception as e:
        logger.error(f"准备Mac版本文件时出错: {e}")
        sys.exit(1)

def build_on_mac():
    """在Mac上完成构建和打包"""
    try:
        logger.info("开始构建Mac版本...")
        
        # 检查create-dmg是否安装
        result = subprocess.run(['which', 'create-dmg'], capture_output=True)
        if result.returncode != 0:
            logger.error("错误: 未安装create-dmg工具")
            logger.info("请先安装create-dmg: brew install create-dmg")
            sys.exit(1)
        
        # 检查是否在mac_build目录中
        if not os.path.exists('work_timer_cross_platform.py'):
            logger.error("错误: 请在mac_build目录中运行此脚本")
            sys.exit(1)
        
        # 创建Mac图标
        mac_icon = create_mac_icon()
        
        # 构建命令
        cmd = (
            'pyinstaller '
            '--name="Pimer" '
            '--windowed '
            f'--icon={mac_icon} '
            '--add-data="pig_nose_icon.ico:." '
            f'--add-data="{mac_icon}:." '
            '--add-data="donate_qr.png:." '
            '--add-data="sounds:sounds" '
            '--add-data=".env:." '
            '--add-data="settings.json:." '
            '--add-data="cloud_config.json:." '
            '--add-data="LICENSE:." '
            '--add-data="mac_adapter.py:." '
            '--add-data="work_timer.py:." '
            '--distpath=dist '
            'work_timer_cross_platform.py'
        )
        
        # 执行构建
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"构建Mac应用失败: {result.stderr}")
            sys.exit(1)
        
        # 创建DMG安装包
        create_dmg()
        
        logger.info("Mac版本构建完成！")
        logger.info("DMG安装包位于 installer/mac/Pimer.dmg")
        
    except Exception as e:
        logger.error(f"Mac版本构建过程中出错: {e}")
        sys.exit(1)

def create_dmg():
    """创建DMG安装包"""
    logger.info("正在创建DMG安装包...")
    
    # 创建DMG输出目录
    dmg_dir = 'installer/mac'
    if not os.path.exists(dmg_dir):
        os.makedirs(dmg_dir)
    
    # 检查Mac图标
    mac_icon = 'pig_nose_icon.icns' if os.path.exists('pig_nose_icon.icns') else 'pig_nose_icon.ico'
    
    # 使用create-dmg工具创建DMG
    cmd = (
        'create-dmg '
        '--volname "Pimer Installer" '
        f'--volicon "{mac_icon}" '
        '--window-pos 200 120 '
        '--window-size 800 400 '
        '--icon-size 100 '
        '--icon "Pimer.app" 200 190 '
        '--hide-extension "Pimer.app" '
        '--app-drop-link 600 185 '
        '"installer/mac/Pimer.dmg" '
        '"dist/Pimer.app"'
    )
    
    # 执行命令
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"创建DMG失败: {result.stderr}")
        sys.exit(1)
    
    logger.info("DMG创建完成！文件位于: installer/mac/Pimer.dmg")

def main():
    """主函数"""
    try:
        print("\n开始构建Mac版本...")  # 直接打印到控制台
        logger.info("开始构建Mac版本...")
        
        if platform.system() == 'Windows':
            build_on_windows()
        elif platform.system() == 'Darwin':
            build_on_mac()
        else:
            error_msg = f"不支持的操作系统: {platform.system()}"
            logger.error(error_msg)
            print(f"\n{error_msg}")  # 直接打印到控制台
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"构建过程中出错: {e}"
        logger.error(error_msg)
        print(f"\n{error_msg}")  # 直接打印到控制台
        sys.exit(1)

if __name__ == "__main__":
    main() 