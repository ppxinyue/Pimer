import os
import platform
import subprocess
from pathlib import Path

class MacAdapter:
    @staticmethod
    def play_system_sound(sound_type='bingo'):
        """在Mac上播放系统音效"""
        try:
            if sound_type == 'bingo':
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Blow.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Bottle.aiff'])
            elif sound_type == 'achievement':
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Blow.aiff'])
            elif sound_type == 'levelup':
                subprocess.run(['afplay', '/System/Library/Sounds/Bottle.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Blow.aiff'])
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
            else:
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
        except Exception as e:
            print(f"播放系统音效失败: {e}")

    @staticmethod
    def add_to_startup():
        """在Mac上添加到启动项"""
        try:
            # 获取应用路径
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))
            
            # 创建启动项
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pimer.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>{app_path}/Pimer</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
            
            # 写入启动项文件
            plist_path = os.path.expanduser('~/Library/LaunchAgents/com.pimer.app.plist')
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # 设置权限
            os.chmod(plist_path, 0o644)
            
            # 加载启动项
            subprocess.run(['launchctl', 'load', plist_path])
            return True
        except Exception as e:
            print(f"添加到启动项失败: {e}")
            return False

    @staticmethod
    def remove_from_startup():
        """从Mac启动项中移除"""
        try:
            plist_path = os.path.expanduser('~/Library/LaunchAgents/com.pimer.app.plist')
            if os.path.exists(plist_path):
                # 卸载启动项
                subprocess.run(['launchctl', 'unload', plist_path])
                # 删除启动项文件
                os.remove(plist_path)
            return True
        except Exception as e:
            print(f"从启动项移除失败: {e}")
            return False

    @staticmethod
    def get_app_data_dir():
        """获取Mac应用数据目录"""
        return Path(os.path.expanduser('~/Library/Application Support/Pimer'))

    @staticmethod
    def ensure_app_data_dir():
        """确保Mac应用数据目录存在"""
        data_dir = MacAdapter.get_app_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir 