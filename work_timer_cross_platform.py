import os
import sys
import platform
import json
import time
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
from dotenv import load_dotenv
import keyboard
import pystray
import webbrowser
import logging
import uuid
from logging.handlers import RotatingFileHandler

# 根据平台导入特定模块
if platform.system() == 'Windows':
    import winreg
    import winsound
    from work_timer import WorkTimer as BaseWorkTimer
elif platform.system() == 'Darwin':
    from mac_adapter import MacAdapter
    from work_timer_mac import MacWorkTimer as BaseWorkTimer
else:
    from work_timer import WorkTimer as BaseWorkTimer

# 加载环境变量
load_dotenv()

# 配置日志
def setup_logging():
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'pimer.log'
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    logger = logging.getLogger('Pimer')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logging()

class CloudConfig:
    def __init__(self):
        self.config_file = Path('cloud_config.json')
        self.config = {}
        self.load_config()
        self.setup_device_id()
    
    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
        except Exception as e:
            logger.error(f"加载云配置失败: {e}")
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存云配置失败: {e}")
    
    def get(self, key):
        return self.config.get(key)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()
    
    def setup_device_id(self):
        if not self.get('device_id'):
            self.set('device_id', str(uuid.uuid4()))

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
    
    def on_modified(self, event):
        if event.src_path == str(self.app.data_file):
            self.app.handle_external_data_change()

class Settings:
    def __init__(self):
        self.settings_file = Path('settings.json')
        self.settings = {}
        self.load_settings()
    
    def load_settings(self):
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
    
    def get(self, key):
        return self.settings.get(key)
    
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

class CrossPlatformWorkTimer(BaseWorkTimer):
    def __init__(self):
        super().__init__()
        self.setup_platform_specific()
        self.setup_file_paths()
        self.setup_file_watcher()
    
    def setup_platform_specific(self):
        """设置平台特定的功能"""
        if platform.system() == 'Darwin':
            self.mac_adapter = MacAdapter()
            self.root.attributes('-alpha', 0.9)
            self.root.attributes('-topmost', True)
    
    def setup_file_paths(self):
        """设置文件路径"""
        try:
            if platform.system() == 'Darwin':
                # Mac系统使用用户数据目录
                self.data_file = Path.home() / 'Library' / 'Application Support' / 'Pimer' / 'pimer_data.json'
            else:
                # Windows系统使用当前目录
                self.data_file = Path('pimer_data.json')
            
            # 确保数据文件所在目录存在
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果数据文件不存在，创建它
            if not self.data_file.exists():
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据文件路径: {self.data_file}")
        except Exception as e:
            logger.error(f"设置文件路径失败: {e}")
            raise
    
    def setup_file_watcher(self):
        """设置文件监视器"""
        try:
            self.observer = Observer()
            self.observer.schedule(FileChangeHandler(self), str(self.data_file.parent), recursive=False)
            self.observer.start()
            logger.info("文件监视器已启动")
        except Exception as e:
            logger.error(f"设置文件监视器失败: {e}")
    
    def handle_external_data_change(self):
        """处理外部数据变化"""
        try:
            # 重新加载数据
            self.load_data()
            # 更新界面
            self.update_display()
            logger.info("已处理外部数据变化")
        except Exception as e:
            logger.error(f"处理外部数据变化失败: {e}")
    
    def play_system_sound(self, sound_type='bingo'):
        """根据平台播放系统音效"""
        if platform.system() == 'Windows':
            try:
                if sound_type == 'bingo':
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)
                elif sound_type == 'achievement':
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS)
                elif sound_type == 'levelup':
                    winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS)
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
                else:
                    winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
            except Exception as e:
                logger.error(f"播放系统音效失败: {e}")
        elif platform.system() == 'Darwin':
            self.mac_adapter.play_system_sound(sound_type)
    
    def add_to_startup(self):
        """根据平台添加到启动项"""
        if platform.system() == 'Windows':
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                winreg.SetValueEx(key, "Pimer", 0, winreg.REG_SZ, str(self.data_file.parent / "Pimer.exe"))
                winreg.CloseKey(key)
                return True
            except Exception as e:
                logger.error(f"添加到启动项失败: {e}")
                return False
        elif platform.system() == 'Darwin':
            return self.mac_adapter.add_to_startup()
    
    def remove_from_startup(self):
        """根据平台从启动项移除"""
        if platform.system() == 'Windows':
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(key, "Pimer")
                winreg.CloseKey(key)
                return True
            except Exception as e:
                logger.error(f"从启动项移除失败: {e}")
                return False
        elif platform.system() == 'Darwin':
            return self.mac_adapter.remove_from_startup()

def main():
    try:
        app = CrossPlatformWorkTimer()
        app.root.mainloop()
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        messagebox.showerror("错误", f"程序运行出错: {e}")

if __name__ == "__main__":
    main() 