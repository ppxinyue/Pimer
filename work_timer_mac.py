import os
import sys
import platform
from pathlib import Path
from mac_adapter import MacAdapter
from work_timer import WorkTimer

class MacWorkTimer(WorkTimer):
    def __init__(self):
        super().__init__()
        self.mac_adapter = MacAdapter()
        
        # 设置Mac特定的窗口属性
        self.root.attributes('-alpha', 0.9)  # 设置透明度
        self.root.attributes('-topmost', True)  # 设置窗口置顶
        
        # 设置Mac特定的数据目录
        self.data_dir = self.mac_adapter.ensure_app_data_dir()
        
    def play_system_sound(self, sound_type='bingo'):
        """使用Mac适配器播放系统音效"""
        self.mac_adapter.play_system_sound(sound_type)
        
    def add_to_startup(self):
        """使用Mac适配器添加到启动项"""
        return self.mac_adapter.add_to_startup()
        
    def remove_from_startup(self):
        """使用Mac适配器从启动项移除"""
        return self.mac_adapter.remove_from_startup()
        
    def setup_file_paths(self):
        """设置Mac特定的文件路径"""
        if self.user_manager.is_logged_in():
            username = self.user_manager.get_current_user()
            self.user_manager.ensure_user_data_dir(username)
            self.data_file = self.user_manager.get_user_data_file(username)
        else:
            # 使用Mac应用数据目录
            self.data_file = self.data_dir / 'work_time.json'
            self.data_file.parent.mkdir(exist_ok=True)

def main():
    # 确保在Mac系统上运行
    if platform.system() != 'Darwin':
        print("错误: 此程序只能在Mac系统上运行")
        sys.exit(1)
        
    # 创建并运行应用
    app = MacWorkTimer()
    app.root.mainloop()

if __name__ == "__main__":
    main() 