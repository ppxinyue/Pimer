import os
import sys
import shutil
from pathlib import Path
import platform
import subprocess

def clean_build():
    """清理构建文件夹"""
    print("正在清理构建文件夹...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    if os.path.exists('Pimer.spec'):
        os.remove('Pimer.spec')

def build_exe():
    """使用PyInstaller构建exe"""
    print("正在构建exe...")
    
    # 构建命令
    cmd = (
        'pyinstaller '
        '--name="Pimer" '
        '--windowed '
        '--icon=pig_nose_icon.ico '
        '--add-data="pig_nose_icon.ico;." '
        '--add-data="donate_qr.png;." '
        '--add-data="sounds;sounds" '
        '--add-data=".env;." '
        '--add-data="settings.json;." '
        '--add-data="cloud_config.json;." '
        '--add-data="LICENSE;." '
        'work_timer.py'
    )
    
    # 执行构建
    os.system(cmd)

def create_mac_icon():
    """创建Mac版本的图标文件"""
    print("正在创建Mac图标...")
    
    # 在Windows环境下，跳过图标转换
    if platform.system() != 'Darwin':
        print("在Windows环境下构建，跳过Mac图标转换")
        return 'pig_nose_icon.ico'
    
    # 检查是否已存在icns文件
    if os.path.exists('pig_nose_icon.icns'):
        print("已存在Mac图标文件")
        return 'pig_nose_icon.icns'
    
    # 检查create_mac_icon.py是否存在
    if not os.path.exists('create_mac_icon.py'):
        print("错误: 找不到create_mac_icon.py文件")
        sys.exit(1)
    
    # 运行图标转换脚本
    result = subprocess.run(['python', 'create_mac_icon.py'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"创建Mac图标时出错: {result.stderr}")
        sys.exit(1)
    
    # 检查是否成功创建了icns文件
    if not os.path.exists('pig_nose_icon.icns'):
        print("错误: 未能创建Mac图标文件")
        sys.exit(1)
    
    return 'pig_nose_icon.icns'

def build_mac_app():
    """使用PyInstaller构建Mac应用"""
    print("正在构建Mac应用...")
    
    # 创建Mac构建目录
    mac_build_dir = 'mac_build'
    if os.path.exists(mac_build_dir):
        shutil.rmtree(mac_build_dir)
    os.makedirs(mac_build_dir)
    
    # 创建Mac图标
    mac_icon = create_mac_icon()
    
    # 检查Mac适配器文件
    if not os.path.exists('mac_adapter.py'):
        print("错误: 找不到mac_adapter.py文件")
        sys.exit(1)
    
    # 检查Mac版本的主程序文件
    if not os.path.exists('work_timer_mac.py'):
        print("错误: 找不到work_timer_mac.py文件")
        sys.exit(1)
    
    # 复制图标文件到构建目录
    shutil.copy(mac_icon, mac_build_dir)
    
    # 构建命令 - Mac版本使用:分隔符而不是;
    # 在Windows上构建时使用;分隔符，但在命令中指定Mac的:分隔符
    separator = ';' if platform.system() == 'Windows' else ':'
    
    cmd = (
        'pyinstaller '
        '--name="Pimer" '
        '--windowed '
        f'--icon={mac_icon} '
        f'--add-data="pig_nose_icon.ico{separator}." '
        f'--add-data="{mac_icon}{separator}." '
        f'--add-data="donate_qr.png{separator}." '
        f'--add-data="sounds{separator}sounds" '
        f'--add-data=".env{separator}." '
        f'--add-data="settings.json{separator}." '
        f'--add-data="cloud_config.json{separator}." '
        f'--add-data="LICENSE{separator}." '
        f'--add-data="mac_adapter.py{separator}." '
        f'--add-data="work_timer.py{separator}." '
        '--distpath=' + mac_build_dir + '/dist '
        '--workpath=' + mac_build_dir + '/build '
        '--specpath=' + mac_build_dir + ' '
        'work_timer_mac.py'
    )
    
    # 执行构建
    os.system(cmd)
    
    return mac_build_dir

def create_dmg():
    """创建DMG安装包"""
    print("正在创建DMG安装包...")
    
    # 在Windows环境下，跳过DMG创建
    if platform.system() != 'Darwin':
        print("在Windows环境下构建，跳过DMG创建")
        print("注意: 要完成DMG创建，请在Mac系统上运行此脚本")
        print("已准备好的文件位于 mac_build/dist/Pimer.app")
        return
    
    # 创建DMG输出目录
    dmg_dir = 'installer/mac'
    if not os.path.exists(dmg_dir):
        os.makedirs(dmg_dir)
    
    # 检查Mac图标
    mac_icon = 'pig_nose_icon.icns' if os.path.exists('pig_nose_icon.icns') else 'pig_nose_icon.ico'
    
    # 使用create-dmg工具创建DMG
    # 注意：需要先安装create-dmg: brew install create-dmg
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
        '"mac_build/dist/Pimer.app"'
    )
    
    # 执行命令
    os.system(cmd)
    print("DMG创建完成！文件位于: installer/mac/Pimer.dmg")

def create_inno_script():
    """创建Inno Setup脚本"""
    print("正在创建Inno Setup脚本...")
    
    script_content = '''
#define MyAppName "Pimer"
#define MyAppVersion "2.0.4"
#define MyAppPublisher "pp & cursor"
#define MyAppURL "https://github.com/ppxinyue/Pimer"
#define MyAppExeName "Pimer.exe"

[Setup]
AppId={{8C8A69CA-9669-45C4-A5DA-34E5E4E8D3B0}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=Pimer_Setup
SetupIconFile=pig_nose_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\\Pimer\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion
Source: "settings.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "cloud_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\\Microsoft\\Internet Explorer\\Quick Launch\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
    '''
    
    # 写入Inno Setup脚本
    with open('pimer_setup.iss', 'w', encoding='utf-8') as f:
        f.write(script_content)

def build_installer():
    """使用Inno Setup构建安装程序"""
    print("正在构建安装程序...")
    
    # Inno Setup编译器路径
    iscc_path = r'D:\software\Inno Setup 6\ISCC.exe'
    
    # 创建installer目录
    if not os.path.exists('installer'):
        os.makedirs('installer')
    
    # 编译安装程序
    os.system(f'"{iscc_path}" pimer_setup.iss')

def build_mac():
    """构建Mac版本"""
    try:
        print("开始构建Mac版本...")
        
        # 构建Mac应用
        mac_build_dir = build_mac_app()
        
        # 创建DMG安装包
        create_dmg()
        
        if platform.system() == 'Windows':
            print("Mac版本基础构建完成！")
            print("注意: 在Windows环境下无法创建完整的DMG安装包")
            print("请将mac_build目录复制到Mac系统上，然后运行以下命令完成DMG创建:")
            print("  python pimer_build.py mac")
        else:
            print("Mac版本构建完成！")
            print("DMG安装包位于 installer/mac/Pimer.dmg")
        
    except Exception as e:
        print(f"Mac版本构建过程中出错: {e}")
        sys.exit(1)

def main():
    """主函数"""
    try:
        # 检查命令行参数
        if len(sys.argv) > 1:
            if sys.argv[1].lower() == 'mac':
                # 构建Mac版本
                build_mac()
                return
            elif sys.argv[1].lower() == 'windows':
                # 继续构建Windows版本
                pass
            else:
                print(f"未知参数: {sys.argv[1]}")
                print("用法: python pimer_build.py [mac|windows]")
                return
        
        # 默认构建Windows版本
        # 清理旧的构建文件
        clean_build()
        
        # 构建exe
        build_exe()
        
        # 创建Inno Setup脚本
        create_inno_script()
        
        # 构建安装程序
        build_installer()
        
        print("Windows版本构建完成！")
        print("安装程序位于 installer/Pimer_Setup.exe")
        
    except Exception as e:
        print(f"构建过程中出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()