import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time
from datetime import datetime, timedelta
import os
import sys
import winreg as reg
from tkinter import font as tkfont
import csv
import calendar
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pystray
import threading
import queue
import keyboard
from pathlib import Path
import shutil
import watchdog.observers
import watchdog.events
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from user_manager import UserManager
from login_window import LoginWindow
from cloud_sync import CloudSync
import winsound  # 添加音效支持
try:
    from playsound import playsound  # 添加更多音效支持
    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False
    print("playsound库未安装，将使用系统默认音效")

class CloudConfig:
    def __init__(self):
        self.config_file = 'cloud_config.json'
        self.default_config = {
            'sync_enabled': False,
            'sync_path': '',
            'last_sync_time': None,
            'device_id': None
        }
        self.load_config()
        
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = self.default_config
            self.save_config()
            
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def get(self, key):
        return self.config.get(key, self.default_config.get(key))
        
    def set(self, key, value):
        self.config[key] = value
        self.save_config()
        
    def setup_device_id(self):
        if not self.get('device_id'):
            import uuid
            self.set('device_id', str(uuid.uuid4()))

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.last_modified = 0
        self.cooldown = 1  # 冷却时间（秒）
        
    def on_modified(self, event):
        if event.src_path.endswith('work_time.json'):
            current_time = time.time()
            # 检查是否在冷却期内
            if current_time - self.last_modified > self.cooldown:
                self.last_modified = current_time
                self.app.handle_external_data_change()

class Settings:
    def __init__(self):
        self.config_file = 'settings.json'
        self.default_settings = {
            'opacity': 0.75,
            'daily_goal': 8 * 3600,  # 8小时
            'auto_start': True,
            'show_seconds': True,
            'always_on_top': False,  # 默认不置顶
            'theme': 'dark',  # 默认使用深色主题
            'timer_mode': 'up',  # 默认使用正计时模式，'up'为正计时，'down'为倒计时
            'hotkeys': {
                'toggle_timer': 'ctrl+shift+space',
                'show_hide': 'ctrl+shift+h'
            }
        }
        self.load_settings()
        
    def load_settings(self):
        try:
            with open(self.config_file, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = self.default_settings
            self.save_settings()
            
    def save_settings(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
            
    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))
        
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

class WorkTimer:
    # 深色主题颜色
    DARK_THEME = {
        'bg': '#2c2c2e',
        'fg': '#ffffff',
        'fg_secondary': '#98989d',
        'button_bg': '#2c2c2e',
        'button_hover': '#3a3a3c',
        'entry_bg': '#3a3a3c',
        'progress_bg': '#3a3a3c',
        'progress_fg': '#0a84ff'
    }
    
    # 浅色主题颜色
    LIGHT_THEME = {
        'bg': '#f2f2f7',
        'fg': '#000000',
        'fg_secondary': '#666666',
        'button_bg': '#f2f2f7',
        'button_hover': '#e5e5ea',
        'entry_bg': '#ffffff',
        'progress_bg': '#e5e5ea',
        'progress_fg': '#007aff'
    }
    
    def __init__(self):
        self.settings = Settings()
        self.user_manager = UserManager()
        self.root = tk.Tk()
        self.root.title("Pimer")  # 修改软件名称
        
        # 初始化音效管理器
        self.sound_manager = SoundManager()
        
        # 立即隐藏主窗口，防止出现半透明白色窗口
        self.root.withdraw()

        # 托盘和热键线程只投递操作，由 Tk 事件循环执行。
        self._ui_queue = queue.SimpleQueue()
        self._closing = False
        self._process_ui_queue()
        
        # 设置窗口样式
        self.root.attributes('-topmost', self.settings.get('always_on_top'))
        self.root.attributes('-alpha', self.settings.get('opacity'))
        self.root.overrideredirect(True)
        self.root.attributes('-transparentcolor', '#000001')  # 特殊的透明色值
        
        # 初始化置顶状态
        self.topmost = self.settings.get('always_on_top')
        
        # 创建数据目录
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        # 初始化变量
        self.setup_variables()
        
        # 加载图标
        self.load_icons()
        
        # 绑定事件
        self.bind_events()
        
        # 创建托盘图标（提前创建，避免quit_app中的错误）
        self.setup_tray()
        
        # 设置文件路径（提前设置，避免备份时的错误）
        self.setup_file_paths()
        
        # 显示登录窗口或直接加载数据
        if not self.user_manager.is_logged_in():
            self.show_login_window()
        else:
            self.on_login_success()
            
    def show_login_window(self):
        """显示登录窗口"""
        login_window = LoginWindow(self.root, self.user_manager, self.on_login_success)
        # 主窗口已经在__init__中隐藏，这里不需要再次隐藏
        # self.root.withdraw()  # 隐藏主窗口
        self.root.wait_window(login_window.window)  # 等待登录窗口关闭
        
        if not self.user_manager.is_logged_in():
            self.quit_app()  # 如果未登录，退出应用
            
    def on_login_success(self):
        """登录成功回调"""
        # 创建一个变量来控制是否显示加载窗口
        self.loading_completed = False
        self.loading_window = None
        
        # 使用线程执行耗时操作，避免界面卡死
        def load_app():
            try:
                # 重新设置文件路径（确保使用正确的用户目录）
                self.setup_file_paths()
                
                # 初始化云同步
                if self.user_manager.is_logged_in():
                    username = self.user_manager.get_current_user()
                    self.cloud_sync = CloudSync(username)
                    print(f"云同步已初始化，状态：{'已连接' if self.cloud_sync.is_connected else '未连接'}")
                
                # 加载数据
                self.load_data()
                
                # 设置UI和热键
                self.setup_ui()
                self.setup_hotkeys()
                
                # 标记加载完成
                self.loading_completed = True
                
                # 如果加载窗口已经显示，则关闭它
                if self.loading_window and self.loading_window.winfo_exists():
                    self.loading_window.destroy()
                
                # 显示主窗口
                self._post_ui(self.show_window)
                
                # 开始更新计时器
                self.update_timer()
            except Exception as e:
                # 标记加载完成（虽然是出错完成）
                self.loading_completed = True
                
                # 如果加载窗口已经显示，则显示错误信息
                if self.loading_window and self.loading_window.winfo_exists():
                    loading_label = self.loading_window.nametowidget(".loading_frame.loading_label")
                    loading_label.config(text=f"加载失败: {str(e)}")
                    # 3秒后关闭加载窗口
                    self.loading_window.after(3000, self.loading_window.destroy)
                else:
                    # 如果加载窗口未显示，则直接显示错误消息
                    messagebox.showerror("加载失败", f"加载应用程序时出错: {e}")
                
                print(f"加载应用程序时出错: {e}")
        
        # 启动加载线程
        loading_thread = threading.Thread(target=load_app, daemon=True)
        loading_thread.start()
        
        # 3秒后检查是否需要显示加载窗口
        def check_loading_status():
            if not self.loading_completed:
                # 如果3秒后仍未加载完成，显示加载窗口
                self.show_loading_window()
        
        # 3秒后检查加载状态
        self.root.after(3000, check_loading_status)
    
    def show_loading_window(self):
        """显示加载窗口"""
        # 如果已经加载完成，不显示加载窗口
        if self.loading_completed:
            return
            
        # 创建加载窗口
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("Pimer - loading")
        
        # 设置与主窗口相同的位置和大小
        self.loading_window.geometry('500x350+50+50')  # 与主窗口相同的大小和位置
        self.loading_window.resizable(False, False)
        
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        self.loading_window.configure(bg=colors['bg'])
        
        # 使加载窗口置于顶层
        self.loading_window.attributes('-topmost', True)
        
        # 居中显示加载提示
        loading_frame = tk.Frame(self.loading_window, bg=colors['bg'], name="loading_frame")
        loading_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        loading_label = tk.Label(
            loading_frame, 
            text="loading...", 
            font=("Microsoft YaHei", 18, "bold"),
            fg=colors['fg'],
            bg=colors['bg'],
            name="loading_label"
        )
        loading_label.pack(pady=(50, 20))
        
        # 添加进度条
        progress = ttk.Progressbar(loading_frame, mode="indeterminate", length=400)
        progress.pack(pady=30)
        progress.start(10)  # 启动进度条动画
        
        # 确保窗口显示在前台
        self.loading_window.lift()
        self.loading_window.focus_force()
        self.loading_window.update()

        icon_path = "pig_nose_icon.ico"
        if os.path.exists(icon_path):
            self.loading_window.iconbitmap(icon_path)
    

    def setup_file_paths(self):
        """设置文件路径"""
        if self.user_manager.is_logged_in():
            username = self.user_manager.get_current_user()
            self.user_manager.ensure_user_data_dir(username)
            self.data_file = self.user_manager.get_user_data_file(username)
        else:
            # 默认数据文件路径
            self.data_file = Path('data/work_time.json')
            # 确保目录存在
            self.data_file.parent.mkdir(exist_ok=True)
            
    def setup_file_watcher(self):
        """设置文件监听"""
        if self.user_manager.is_logged_in():
            username = self.user_manager.get_current_user()
            self.observer = Observer()
            self.event_handler = FileChangeHandler(self)
            self.observer.schedule(
                self.event_handler,
                str(self.data_file.parent),
                recursive=False
            )
            self.observer.start()
            
    def handle_external_data_change(self):
        """处理外部数据变化"""
        if not hasattr(self, 'is_saving'):  # 避免处理自己的保存操作
            self.is_saving = True
            try:
                self.merge_data()
                self.update_display()
            finally:
                self.is_saving = False
                
    def merge_data(self):
        """合并数据"""
        try:
            # 读取当前内存中的数据
            current_data = {
                str(self.today): {
                    'accumulated_time': self.accumulated_time,
                    'is_running': self.is_running,
                    'start_time': self.start_time if self.start_time else None
                }
            }
            
            # 读取文件中的数据
            with open(self.data_file, 'r') as f:
                file_data = json.load(f)
                
            # 合并数据
            for date, data in file_data.items():
                if date not in current_data:
                    current_data[date] = data
                elif date == str(self.today):
                    # 对于今天的数据，保留较大的累计时间
                    if isinstance(data, dict) and isinstance(current_data[date], dict):
                        if data['accumulated_time'] > current_data[date]['accumulated_time']:
                            current_data[date] = data
                            self.accumulated_time = data['accumulated_time']
                            
            # 保存合并后的数据
            with open(self.data_file, 'w') as f:
                json.dump(current_data, f, indent=4)
                
        except Exception as e:
            print(f"合并数据时出错：{e}")
            
    def update_display(self):
        """更新时间显示"""
        if not self.is_running:
            return
            
        # 计算总秒数
        total_seconds = self.accumulated_time
        if self.start_time:
            total_seconds += time.time() - self.start_time
            
        # 根据计时模式显示时间
        timer_mode = self.settings.get('timer_mode')
        
        if timer_mode == 'up':  # 正计时模式
            # 计算时分秒
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            # 更新时间标签
            if self.settings.get('show_seconds'):
                self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.time_label.configure(text=f"{hours:02d}:{minutes:02d}")
        else:  # 倒计时模式
            # 获取目标时间（小时）
            try:
                target_hours = float(self.target_time_var.get())
                target_seconds = target_hours * 3600
                
                # 计算剩余时间
                remaining_seconds = max(0, target_seconds - total_seconds)
                
                # 计算时分秒
                hours = int(remaining_seconds // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                seconds = int(remaining_seconds % 60)
                
                # 更新时间标签
                if self.settings.get('show_seconds'):
                    self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    self.time_label.configure(text=f"{hours:02d}:{minutes:02d}")
                    
                # 如果倒计时结束，停止计时器并显示庆祝
                # 只有当焦点不在目标输入框上时才检查
                if remaining_seconds <= 0 and self.is_running and self.root.focus_get() != self.target_entry:
                    # 避免重复触发
                    if not hasattr(self, 'countdown_completed') or not self.countdown_completed:
                        self.countdown_completed = True
                        
                        # 显示庆祝动画
                        self.show_celebration(is_target_completed=True)
                        
                        # 自动增加目标时间1小时，与正计时模式一致
                        new_target = target_hours + 1.0
                        if new_target > 12:  # 限制最大时间为12小时
                            new_target = 12.0
                        self.target_time_var.set(f'{new_target:.2f}')
                        
                        # 停止计时器
                        # self.toggle_timer()
            except (ValueError, AttributeError) as e:
                print(f"倒计时模式计算时间出错: {e}")
                # 出错时显示00:00:00
                self.time_label.configure(text="00:00:00")
            
        # 更新进度条
        self.update_progress(total_seconds)
        
        # 检查是否达到目标时间 - 只有当焦点不在目标输入框上时才检查
        # 在正计时模式下才检查目标完成情况
        if timer_mode == 'up' and self.root.focus_get() != self.target_entry:
            try:
                target_hours = float(self.target_time_var.get())
                target_seconds = target_hours * 3600
                
                # 检查是否完成目标
                if total_seconds >= target_seconds and target_hours > 0:
                    # 避免重复触发庆祝
                    if not hasattr(self, 'target_completed') or not self.target_completed:
                        self.target_completed = True
                        
                        # 显示庆祝动画
                        self.show_celebration(is_target_completed=True)
                        
                        # 自动增加目标时间1小时
                        new_target = target_hours + 1.0
                        if new_target > 12:  # 限制最大时间为12小时
                            new_target = 12.0
                        self.target_time_var.set(f'{new_target:.2f}')
                        
                        # 更新进度条
                        self.update_progress()
                else:
                    # 如果之前完成过目标，但现在目标变更了，重置标记
                    if hasattr(self, 'target_completed') and self.target_completed:
                        self.target_completed = False
            except (ValueError, AttributeError) as e:
                print(f"检查目标完成时出错: {e}")
        
        # 每秒更新一次
        self.root.after(1000, self.update_display)

    def load_data(self):
        """加载数据（优先从云端同步）"""
        try:
            if hasattr(self, 'cloud_sync') and self.cloud_sync.is_connected:
                # 尝试从云端同步数据
                cloud_data = self.cloud_sync.sync_data()
                if cloud_data:
                    current_date = datetime.now().date()
                    
                    # 检查是否是新的一天
                    if str(current_date) not in cloud_data:
                        # 新的一天从零开始
                        self.accumulated_time = 0
                        self.is_running = False
                        self.start_time = None
                    else:
                        # 直接使用云端数据
                        today_data = cloud_data[str(current_date)]
                        if isinstance(today_data, (int, float)):
                            self.accumulated_time = today_data
                            self.is_running = False
                            self.start_time = None
                        else:
                            # 直接使用云端数据中的累计时间
                            self.accumulated_time = today_data['accumulated_time']
                            self.is_running = today_data['is_running']
                            if self.is_running and today_data['start_time']:
                                elapsed = time.time() - today_data['start_time']
                                self.accumulated_time += elapsed
                                self.start_time = time.time()
                            else:
                                self.start_time = None
                                self.is_running = False
                    
                    # 设置当前日期
                    self.today = current_date
                    
                    # 将云端数据保存到本地
                    with open(self.data_file, 'w') as f:
                        json.dump(cloud_data, f, indent=4)
                    return
            
            # 如果没有云端数据或云同步失败，使用本地数据
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    current_date = datetime.now().date()
                    
                    # 检查是否是新的一天
                    if str(current_date) not in data:
                        # 新的一天从零开始
                        self.accumulated_time = 0
                        self.is_running = False
                        self.start_time = None
                    else:
                        # 加载当天的数据
                        today_data = data[str(current_date)]
                        if isinstance(today_data, (int, float)):
                            self.accumulated_time = today_data
                            self.is_running = False
                            self.start_time = None
                        else:
                            self.accumulated_time = today_data['accumulated_time']
                            self.is_running = today_data['is_running']
                            if self.is_running and today_data['start_time']:
                                elapsed = time.time() - today_data['start_time']
                                self.accumulated_time += elapsed
                                self.start_time = time.time()
                            else:
                                self.start_time = None
                                self.is_running = False
                    
                    # 设置当前日期
                    self.today = current_date
            except FileNotFoundError:
                # 文件不存在时初始化数据
                self.accumulated_time = 0
                self.is_running = False
                self.start_time = None
                self.today = datetime.now().date()
            
        except Exception as e:
            print(f"加载数据时出错: {e}")
            # 出错时初始化数据
            self.accumulated_time = 0
            self.is_running = False
            self.start_time = None
            self.today = datetime.now().date()
            
        # 保存当前状态
        self.save_data()
        
        # 立即更新显示，确保显示历史数据
        if hasattr(self, 'time_label'):
            self.update_display()
        
    def save_data(self):
        """保存数据（同时保存到本地和云端）"""
        if hasattr(self, 'is_saving') and self.is_saving:
            return
            
        self.is_saving = True
        try:
            # 读取现有数据
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {}
                
            # 更新当天的数据
            data[str(self.today)] = {
                'accumulated_time': self.accumulated_time,
                'is_running': self.is_running,
                'start_time': self.start_time if self.start_time else None
            }
            
            # 保存所有数据
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
                
            # 同步到云端
            if hasattr(self, 'cloud_sync'):
                # 如果未连接，尝试重新连接
                if not self.cloud_sync.is_connected and hasattr(self.cloud_sync, 'client'):
                    try:
                        self.cloud_sync.client.admin.command('ping')
                        self.cloud_sync.is_connected = True
                        print("MongoDB重新连接成功")
                        # 连接成功后立即更新状态栏
                        self.update_status_bar()
                    except Exception as e:
                        print(f"MongoDB重新连接失败: {e}")
                
                # 如果已连接，上传数据
                if self.cloud_sync.is_connected:
                    try:
                        self.cloud_sync.upload_data(data)
                        print("数据已上传到云端")
                    except Exception as e:
                        print(f"上传数据到云端失败: {e}")
                        self.cloud_sync.is_connected = False
                        # 连接失败后立即更新状态栏
                        self.update_status_bar()
                
        finally:
            self.is_saving = False
        
    def load_icons(self):
        # 使用彩色emoji图标
        self.icons = {
            'play': "▶️",  # 彩色播放图标
            'pause': "⏸️",  # 彩色暂停图标
            'reset': "🔄",  # 彩色重置图标
            'pin': "📌",   # 彩色图钉图标
            'unpin': "📍",  # 彩色未置顶图标
            'stats': "📊",  # 彩色统计图标
            'settings': "⚙️",  # 彩色设置图标
            'close': "❌"    # 彩色关闭图标
        }
        
    def bind_events(self):
        # 拖动和缩放事件绑定
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.on_move)
        self.root.bind('<ButtonRelease-1>', self.stop_move)
        
        # 鼠标进入窗口边缘时改变光标
        self.root.bind('<Motion>', self.check_resize_cursor)
        
    def check_resize_cursor(self, event):
        # 获取窗口大小
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # 定义边缘区域（10像素）
        edge = 10
        
        # 检查鼠标是否在右下角
        if width - edge <= event.x <= width and height - edge <= event.y <= height:
            self.root.config(cursor="sizing")  # 改变光标为缩放形状
            self.resize_mode = True
        else:
            self.root.config(cursor="")  # 恢复默认光标
            self.resize_mode = False
            
    def start_move(self, event):
        if not hasattr(self, 'resize_mode') or not self.resize_mode:
            # 记录鼠标相对于窗口的位置
            self.x = event.x_root - self.root.winfo_x()
            self.y = event.y_root - self.root.winfo_y()
            
    def on_move(self, event):
        if hasattr(self, 'resize_mode') and self.resize_mode:
            # 计算新的宽度和高度
            width = max(300, event.x_root - self.root.winfo_x())
            height = max(150, event.y_root - self.root.winfo_y())
            self.root.geometry(f'{width}x{height}')
        elif hasattr(self, 'x') and hasattr(self, 'y'):
            # 移动窗口
            x = event.x_root - self.x
            y = event.y_root - self.y
            self.root.geometry(f'+{x}+{y}')
            
    def stop_move(self, event):
        # 清除拖动和缩放状态
        if hasattr(self, 'x'): delattr(self, 'x')
        if hasattr(self, 'y'): delattr(self, 'y')
        self.resize_mode = False
        self.root.config(cursor="")
            
    def toggle_topmost(self):
        self.topmost = not self.topmost
        self.root.attributes('-topmost', self.topmost)
        self.pin_button.configure(text=self.icons['pin'] if self.topmost else self.icons['unpin'])
        # 保存置顶状态到设置
        self.settings.set('always_on_top', self.topmost)
        
    def minimize_window(self):
        self.root.withdraw()
        
    def toggle_timer(self):
        if self.is_running:
            self.is_running = False
            self.toggle_button.configure(text=self.icons['play'])
            self.status_label.configure(text="Paused")
            if self.start_time:
                self.accumulated_time += time.time() - self.start_time
                self.save_data()
        else:
            # 获取计时模式
            timer_mode = self.settings.get('timer_mode')
            
            # 在倒计时模式下，如果已经倒计时结束，需要重置
            if timer_mode == 'down' and hasattr(self, 'countdown_completed') and self.countdown_completed:
                # 重置倒计时
                self.accumulated_time = 0
                delattr(self, 'countdown_completed')
                
                # 如果目标时间为0，设置为1小时
                try:
                    target_hours = float(self.target_time_var.get())
                    if target_hours < 0:
                        self.target_time_var.set('1.00')
                        target_hours = 1.0
                except ValueError:
                    self.target_time_var.set('1.00')
                    target_hours = 1.0
                    
                # 更新显示
                try:
                    target_seconds = target_hours * 3600
                    hours = int(target_seconds // 3600)
                    minutes = int((target_seconds % 3600) // 60)
                    seconds = int(target_seconds % 60)
                    self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                except ValueError:
                    self.time_label.configure(text="00:00:00")
            
            self.is_running = True
            self.toggle_button.configure(text=self.icons['pause'])
            self.status_label.configure(text="Working...")
            self.start_time = time.time()
        # 更新进度条
        self.update_progress()
        
    def update_progress(self, total_seconds=None):
        """更新进度条"""
        try:
            # 只有当焦点不在目标输入框上时才更新进度条
            if self.root.focus_get() != self.target_entry:
                # 获取目标时间（小时）
                target_hours = float(self.target_time_var.get())
                if target_hours < 0:
                    target_hours = 1.0
                    self.target_time_var.set('1.00')
                
                # 转换为秒
                target_seconds = target_hours * 3600
                
                # 如果没有提供total_seconds，则计算当前累计时间
                if total_seconds is None:
                    total_seconds = self.accumulated_time
                    if self.is_running and self.start_time:
                        total_seconds += time.time() - self.start_time
                
                # 获取计时模式
                timer_mode = self.settings.get('timer_mode')
                
                # 计算进度百分比
                if timer_mode == 'up':  # 正计时模式
                    # 正计时模式下，进度是累计时间占目标时间的百分比
                    progress = min(100, (total_seconds / target_seconds) * 100)
                else:  # 倒计时模式
                    # 倒计时模式下，进度是已用时间占目标时间的百分比
                    remaining_seconds = max(0, target_seconds - total_seconds)
                    elapsed_seconds = target_seconds - remaining_seconds
                    progress = min(100, (elapsed_seconds / target_seconds) * 100)
                    
                # 更新进度条
                self.progress['value'] = progress
        except (ValueError, ZeroDivisionError) as e:
            # 处理异常情况
            print(f"更新进度条时出错: {e}")
            self.target_time_var.set('1.00')
            self.progress['value'] = 0

    def validate_target_time(self, event=None):
        """验证目标时间输入"""
        try:
            # 获取输入值
            value_str = self.target_time_var.get().strip()
            
            # 只在按下回车键或失去焦点时处理
            if event and (event.keysym == 'Return' or event.type == '9'):  # Return或FocusOut
                # 处理特殊情况：多个小数点
                if value_str.count('.') > 1:
                    # 只保留第一个小数点
                    parts = value_str.split('.')
                    value_str = parts[0] + '.' + ''.join(parts[1:])
                    
                # 空值处理
                if not value_str:
                    self.target_time_var.set('1.0')
                    value = 1.0
                else:
                    # 尝试转换为浮点数
                    value = float(value_str)
                
                # 验证范围
                if value < 0.01:
                    value = 0.01
                elif value > 12:  # 限制最大时间为12小时
                    value = 12.0
                    
                # 格式化为两位小数
                self.target_time_var.set(f'{value:.2f}')
                
                # 获取计时模式
                timer_mode = self.settings.get('timer_mode')
                
                # 在倒计时模式下，如果不在运行状态，更新显示的时间
                if timer_mode == 'down' and not self.is_running:
                    # 计算新的剩余时间
                    target_seconds = value * 3600
                    hours = int(target_seconds // 3600)
                    minutes = int((target_seconds % 3600) // 60)
                    seconds = int(target_seconds % 60)
                    self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    
                    # 重置倒计时完成标记
                    if hasattr(self, 'countdown_completed'):
                        delattr(self, 'countdown_completed')
                
                # 先移除焦点
                self.root.focus()
                
                # 使用after方法确保焦点已经转移后再更新进度条
                self.root.after(10, self.update_progress)
                
            return True
        except ValueError as e:
            # 处理无效输入，只在焦点移出或按下回车键时处理
            if event and (event.type == '9' or event.keysym == 'Return'):
                print(f"目标时间输入错误: {e}")
                self.target_time_var.set('1.00')
                self.root.focus()
                self.root.after(10, self.update_progress)
                
            return False

    def reset_timer(self):
        # 添加确认对话框
        icon_path = "pig_nose_icon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            if not messagebox.askyesno("确认清零", "确定要清零今天的工作时长吗？"):
                return
        else:
            print(f"图标文件不存在: {icon_path}")
            if not messagebox.askyesno("确认清零", "确定要清零今天的工作时长吗？"):
                return
        
        if self.is_running:
            self.toggle_timer()
        self.accumulated_time = 0
        self.start_time = None
        self.save_data()
        
        # 获取计时模式
        timer_mode = self.settings.get('timer_mode')
        
        # 根据计时模式设置重置后的显示
        if timer_mode == 'up':  # 正计时模式
            self.time_label.configure(text="00:00:00")
        else:  # 倒计时模式
            try:
                target_hours = float(self.target_time_var.get())
                target_seconds = target_hours * 3600
                hours = int(target_seconds // 3600)
                minutes = int((target_seconds % 3600) // 60)
                seconds = int(target_seconds % 60)
                self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            except ValueError:
                self.time_label.configure(text="00:00:00")
        
        self.status_label.configure(text="Ready")
        self.progress['value'] = 0
        self.toggle_button.configure(text=self.icons['play'])  # 确保显示播放图标
        
        # 重置完成标记
        if hasattr(self, 'target_completed'):
            delattr(self, 'target_completed')
        if hasattr(self, 'countdown_completed'):
            delattr(self, 'countdown_completed')
        
        # 重置小时检查变量
        if hasattr(self, 'last_hour'):
            delattr(self, 'last_hour')
        if hasattr(self, 'last_remaining_hour'):
            delattr(self, 'last_remaining_hour')

    def add_to_startup(self):
        script_path = os.path.abspath(sys.argv[0])
        key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
            reg.SetValueEx(key, "WorkTimer", 0, reg.REG_SZ, script_path)
            reg.CloseKey(key)
            return True
        except WindowsError:
            return False
        
    def setup_ui(self):
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        
        # 设置窗口样式和初始大小
        self.root.configure(bg=colors['bg'])
        self.root.geometry('500x350+50+50')  # 减小窗口高度到350像素
        
        # 创建自定义字体
        self.time_font = tkfont.Font(family="Calibri", size=52, weight="bold")
        self.status_font = tkfont.Font(family="Calibri", size=24)
        self.button_font = tkfont.Font(family="Segoe UI Emoji", size=18)
        self.input_font = tkfont.Font(family="Calibri", size=24, weight="bold")
        
        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 配置自定义样式
        self.style.configure(
            'Custom.TFrame',
            background=colors['bg']
        )
        
        # 时间显示样式
        self.style.configure(
            'Timer.TLabel',
            background=colors['bg'],
            foreground=colors['fg'],
            font=self.time_font,
            padding=5
        )
        
        # 状态标签样式
        self.style.configure(
            'Status.TLabel',
            background=colors['bg'],
            foreground=colors['fg_secondary'],
            font=self.status_font
        )
        
        # 按钮样式
        self.style.configure(
            'Icon.TButton',
            background=colors['button_bg'],
            foreground=colors['fg'],
            relief='flat',
            borderwidth=0,
            font=self.button_font
        )
        
        # 按钮悬停效果
        self.style.map('Icon.TButton',
            background=[('active', colors['button_hover'])],
            foreground=[('active', colors['fg'])]
        )
        
        # 进度条样式
        self.style.configure(
            'Custom.Horizontal.TProgressbar',
            troughcolor=colors['progress_bg'],
            background=colors['progress_fg'],
            thickness=10,
            borderwidth=0,
            relief='flat'
        )
        
        # 输入框样式
        self.style.configure(
            'Target.TEntry',
            fieldbackground=colors['entry_bg'],
            foreground=colors['fg'],
            insertcolor=colors['fg'],
            font=self.input_font,
            padding=5
        )
        
        # 清除现有的main_frame（如果存在）
        if hasattr(self, 'main_frame'):
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            self.main_frame.destroy()
        
        # 创建主容器
        self.main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        self.main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # 添加Pimer标题
        title_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        title_frame.pack(fill='x', pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="Pimer",
            style='Status.TLabel',
            font=('Microsoft YaHei', 18, 'bold'),
            foreground=colors['fg']
        )
        title_label.pack(side='left')
        
        # 添加GitHub链接到右侧
        github_link = ttk.Label(
            title_frame,
            text="GitHub",
            style='Status.TLabel',
            font=('Microsoft YaHei', 10, 'underline'),
            foreground=colors['fg_secondary'],
            cursor="hand2"
        )
        github_link.pack(side='right')
        github_link.bind("<Button-1>", lambda e: self.open_github())
        
        # 添加开发者信息到GitHub链接左侧
        dev_info = ttk.Label(
            title_frame,
            text="by pp & cursor",
            style='Status.TLabel',
            font=('Microsoft YaHei', 10),
            foreground=colors['fg_secondary']
        )
        dev_info.pack(side='right', padx=(0, 10))
        
        # 时间显示 - 居中显示
        time_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        time_frame.pack(fill='x')
        
        # 准备初始时间显示文本
        total_seconds = self.accumulated_time
        if self.is_running and self.start_time:
            total_seconds += time.time() - self.start_time
            
        # 根据计时模式显示时间
        timer_mode = self.settings.get('timer_mode')
        
        if timer_mode == 'up':  # 正计时模式
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            initial_time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:  # 倒计时模式
            try:
                target_hours = float(self.target_time_var.get())
                target_seconds = target_hours * 3600
                remaining_seconds = max(0, target_seconds - total_seconds)
                
                hours = int(remaining_seconds // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                seconds = int(remaining_seconds % 60)
                initial_time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except (ValueError, AttributeError):
                initial_time_text = "00:00:00"
        
        self.time_label = ttk.Label(
            time_frame,
            text=initial_time_text,  # 使用计算好的初始时间
            style='Timer.TLabel',
            anchor='center'
        )
        self.time_label.pack(expand=True, fill='x')
        
        # 状态标签 - 根据当前状态设置
        status_text = "Working..." if self.is_running else "Ready"
        
        self.status_label = ttk.Label(
            self.main_frame,
            text=status_text,  # 根据当前状态设置
            style='Status.TLabel',
            anchor='center',
            font=('Calibri', 24)
        )
        self.status_label.pack(fill='x', pady=(10, 10))
        
        # 进度条和目标时间框架
        progress_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        progress_frame.pack(fill='x', pady=(0, 10))
        
        # 进度条
        self.progress = ttk.Progressbar(
            progress_frame,
            style='Custom.Horizontal.TProgressbar',
            orient='horizontal',
            length=100,
            mode='determinate'
        )
        self.progress.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        # 目标时间输入框 - 放在进度条后面
        time_input_frame = ttk.Frame(progress_frame, style='Custom.TFrame')
        time_input_frame.pack(side='right')
        
        # 添加Goal标签
        goal_label = ttk.Label(
            time_input_frame,
            text='Goal:',
            style='Status.TLabel',
            font=('Calibri', 20)
        )
        goal_label.pack(side='left', padx=(0, 5))
        
        # 目标时间输入框
        self.target_time_var = tk.StringVar(value='1.00')
        self.target_entry = ttk.Entry(
            time_input_frame,
            textvariable=self.target_time_var,
            style='Target.TEntry',
            width=4,
            justify='right'
        )
        self.target_entry.pack(side='left')
        
        # 绑定输入框验证和更新事件
        self.target_entry.bind('<FocusOut>', self.validate_target_time)
        self.target_entry.bind('<Return>', self.validate_target_time)
        
        # 添加小时标签
        hour_label = ttk.Label(
            time_input_frame,
            text='h',
            style='Status.TLabel',
            font=('Calibri', 20)
        )
        hour_label.pack(side='left', padx=(2, 0))
        
        # 控制按钮框架
        button_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        button_frame.pack(fill='x')
        
        # 开始/暂停按钮 - 根据当前状态设置
        button_icon = self.icons['pause'] if self.is_running else self.icons['play']
        
        self.toggle_button = ttk.Button(
            button_frame,
            text=button_icon,  # 根据当前状态设置
            style='Icon.TButton',
            command=self.toggle_timer,
            width=3
        )
        self.toggle_button.pack(side='left', padx=(0, 10))
        
        # 重置按钮
        reset_button = ttk.Button(
            button_frame,
            text=self.icons['reset'],
            style='Icon.TButton',
            command=self.reset_timer,
            width=3
        )
        reset_button.pack(side='left')
        
        # 右侧控制按钮
        close_button = ttk.Button(
            button_frame,
            text=self.icons['close'],
            style='Icon.TButton',
            command=self.quit_app,
            width=3
        )
        close_button.pack(side='right', padx=3)
        
        # 保存pin_button为实例变量，修复toggle_topmost中的错误
        self.pin_button = ttk.Button(
            button_frame,
            text=self.icons['pin'] if self.topmost else self.icons['unpin'],
            style='Icon.TButton',
            command=self.toggle_topmost,
            width=3
        )
        self.pin_button.pack(side='right', padx=3)
        
        settings_button = ttk.Button(
            button_frame,
            text=self.icons['settings'],
            style='Icon.TButton',
            command=self.show_settings,
            width=3
        )
        settings_button.pack(side='right', padx=3)
        
        stats_button = ttk.Button(
            button_frame,
            text=self.icons['stats'],
            style='Icon.TButton',
            command=self.show_statistics,
            width=3
        )
        stats_button.pack(side='right', padx=3)
        
        # 添加打赏按钮到右侧控制按钮中
        donate_button = ttk.Button(
            button_frame,
            text="💰",
            style='Icon.TButton',
            command=self.show_donate,
            width=3
        )
        donate_button.pack(side='right', padx=3)
        
        # 拖动窗口的事件绑定
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.on_move)
        
        # 初始化时立即更新进度条
        self.update_progress()

    def setup_variables(self):
        self.is_running = False
        self.start_time = None
        self.accumulated_time = 0
        self.today = datetime.now().date()
        self.is_dragging = False
        self.resize_edge = None

    def _post_ui(self, callback):
        if not self._closing:
            self._ui_queue.put(callback)

    def _process_ui_queue(self):
        while not self._closing:
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                self.root.report_callback_exception(*sys.exc_info())
        if not self._closing:
            self.root.after(50, self._process_ui_queue)
        
    def setup_tray(self):
        # 创建系统托盘图标
        image = Image.new('RGB', (64, 64), color='#1e1e2e')
        ready = lambda item: (self.user_manager.is_logged_in() and
                              getattr(self, 'loading_completed', False))
        menu = pystray.Menu(
            pystray.MenuItem("显示 Pimer", lambda: self._post_ui(self.show_window), default=True),
            pystray.MenuItem("隐藏", lambda: self._post_ui(self.minimize_window), enabled=ready),
            pystray.MenuItem("开始/暂停", lambda: self._post_ui(self.toggle_timer), enabled=ready),
            pystray.MenuItem("统计", lambda: self._post_ui(self.show_statistics), enabled=ready),
            pystray.MenuItem("设置", lambda: self._post_ui(self.show_settings), enabled=ready),
            pystray.MenuItem("退出", lambda: self._post_ui(self.quit_app))
        )
        self.tray_icon = pystray.Icon(
            "Pimer",
            image,
            "Pimer",
            menu
        )
        # 将托盘图标线程设置为守护线程
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
        
    def setup_hotkeys(self):
        # 将热键监听设置为守护线程
        hotkey_thread = threading.Thread(target=self._setup_hotkeys, daemon=True)
        hotkey_thread.start()

    def _setup_hotkeys(self):
        keyboard.add_hotkey(
            self.settings.get('hotkeys')['toggle_timer'],
            lambda: self._post_ui(self.toggle_timer)
        )
        keyboard.add_hotkey(
            self.settings.get('hotkeys')['show_hide'],
            lambda: self._post_ui(self.toggle_window)
        )
        
    def show_statistics(self):
        """显示统计信息"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Pimer - 工作统计")
        stats_window.geometry("500x600")
        
        # 设置窗口图标
        self.set_window_icon(stats_window)
        
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        
        stats_window.configure(bg=colors['bg'])
        
        # 设置窗口样式
        style = ttk.Style()
        style.configure('Stats.TFrame',
            background=colors['bg']
        )
        style.configure('Stats.TLabel',
            background=colors['bg'],
            foreground=colors['fg'],
            font=('Microsoft YaHei', 16),
            padding=10
        )
        style.configure('StatsValue.TLabel',
            background=colors['bg'],
            foreground=colors['fg_secondary'],
            font=('Microsoft YaHei', 28, 'bold'),
            padding=10
        )
        style.configure('Stats.TButton',
            font=('Microsoft YaHei', 12),
            padding=10
        )
        
        # 创建主容器
        main_frame = ttk.Frame(stats_window, style='Stats.TFrame')
        main_frame.pack(expand=True, fill='both', padx=30, pady=30)
        
        # 创建统计卡片
        def create_stat_card(parent, title, value, icon):
            frame = ttk.Frame(parent, style='Stats.TFrame')
            frame.pack(fill='x', pady=15)
            
            # 标题行带图标
            title_frame = ttk.Frame(frame, style='Stats.TFrame')
            title_frame.pack(fill='x')
            
            icon_label = ttk.Label(
                title_frame,
                text=icon,
                style='Stats.TLabel',
                font=('Segoe UI Emoji', 24)
            )
            icon_label.pack(side='left', padx=(0, 10))
            
            ttk.Label(
                title_frame,
                text=title,
                style='Stats.TLabel'
            ).pack(side='left', fill='x')
            
            # 数值显示
            ttk.Label(
                frame,
                text=value,
                style='StatsValue.TLabel'
            ).pack(fill='x', pady=(5, 0))
            
        # 获取统计数据
        today = datetime.now().date()
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)
        
        # 计算各时期的统计数据
        today_seconds = self.get_period_stats(today, today)
        this_week_seconds = self.get_period_stats(this_week_start, today)
        this_month_seconds = self.get_period_stats(this_month_start, today)
        
        # 显示统计信息
        create_stat_card(main_frame, "今日工作时间", self.format_duration(today_seconds), "📅")
        create_stat_card(main_frame, "本周工作时间", self.format_duration(this_week_seconds), "📊")
        create_stat_card(main_frame, "本月工作时间", self.format_duration(this_month_seconds), "📈")
        
        # 创建按钮容器
        button_frame = ttk.Frame(main_frame, style='Stats.TFrame')
        button_frame.pack(fill='x', pady=20)
        
        # 添加导出按钮
        export_button = ttk.Button(
            button_frame,
            text="导出数据",
            command=lambda: self.handle_export(),
            style='Stats.TButton'
        )
        export_button.pack(side='left', padx=5, expand=True, fill='x')
        
        # 添加备份按钮
        backup_button = ttk.Button(
            button_frame,
            text="立即备份",
            command=self.backup_data,
            style='Stats.TButton'
        )
        backup_button.pack(side='right', padx=5, expand=True, fill='x')
        
        # 添加同步按钮
        sync_button = ttk.Button(
            button_frame,
            text="同步数据",
            command=self.manual_sync
        )
        sync_button.pack(pady=10)
        
        # 添加关闭按钮
        close_button = ttk.Button(
            main_frame,
            text="关闭",
            command=stats_window.destroy,
            style='Stats.TButton'
        )
        close_button.pack(fill='x', pady=(20, 0))

    def handle_export(self):
        """处理数据导出"""
        export_path = self.export_data()
        if export_path:
            messagebox.showinfo("导出成功", f"数据已导出到：\n{export_path}")
        else:
            messagebox.showerror("导出失败", "导出数据时发生错误")

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Pimer - 设置")
        settings_window.geometry("500x900")  # 增加窗口高度到650像素
        
        # 设置窗口图标
        self.set_window_icon(settings_window)
        
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        
        settings_window.configure(bg=colors['bg'])
        
        # 设置样式
        style = ttk.Style(settings_window)
        style.configure('Settings.TLabel',
            background=colors['bg'],
            foreground=colors['fg'],
            font=('Microsoft YaHei', 14),
            padding=10
        )
        style.configure('Settings.TButton',
            font=('Microsoft YaHei', 12),
            padding=10
        )
        style.configure('Settings.TCheckbutton',
            background=colors['bg'],
            foreground=colors['fg'],
            font=('Microsoft YaHei', 12)
        )
        style.configure('Settings.TRadiobutton',
            background=colors['bg'],
            foreground=colors['fg'],
            font=('Microsoft YaHei', 12)
        )
        
        # 设置复选框样式，使用勾选而不是打叉
        style.map('Settings.TCheckbutton',
            background=[('active', colors['button_hover'])],
            indicatorcolor=[('selected', colors['progress_fg']), ('!selected', colors['progress_bg'])]
        )
        
        style.map('Settings.TRadiobutton',
            background=[('active', colors['button_hover'])],
            indicatorcolor=[('selected', colors['progress_fg']), ('!selected', colors['progress_bg'])]
        )
        
        # 添加用户信息部分
        user_frame = ttk.Frame(settings_window, style='Custom.TFrame')
        user_frame.pack(fill='x', pady=10, padx=20)
        
        if self.user_manager.is_logged_in():
            username = self.user_manager.get_current_user()
            ttk.Label(
                user_frame,
                text=f"当前用户：{username}",
                style='Settings.TLabel'
            ).pack(side='left')
            
            ttk.Button(
                user_frame,
                text="退出登录",
                command=self.handle_logout,
                style='Settings.TButton'
            ).pack(side='right')
        else:
            ttk.Button(
                user_frame,
                text="登录",
                command=self.show_login_window,
                style='Settings.TButton'
            ).pack(fill='x')
            
        # 添加版本号信息
        version_frame = ttk.Frame(settings_window, style='Custom.TFrame')
        version_frame.pack(fill='x', pady=5, padx=20)
        
        version_info = ttk.Label(
            version_frame,
            text="当前版本：v2.0.4",
            style='Settings.TLabel'
        )
        version_info.pack(side='left')

        # 创建设置卡片
        def create_setting_section(parent, title, icon):
            frame = ttk.Frame(parent, style='Custom.TFrame')
            frame.pack(fill='x', pady=10, padx=20)
            
            # 标题行带图标
            title_frame = ttk.Frame(frame, style='Custom.TFrame')
            title_frame.pack(fill='x')
            
            icon_label = ttk.Label(
                title_frame,
                text=icon,
                style='Settings.TLabel',
                font=('Segoe UI Emoji', 18)
            )
            icon_label.pack(side='left', padx=(0, 10))
            
            ttk.Label(
                title_frame,
                text=title,
                style='Settings.TLabel'
            ).pack(side='left', fill='x')
            
            return frame
            
        # 云同步设置 - 放在最上面
        cloud_frame = create_setting_section(settings_window, "数据同步", "☁️")
        
        # 同步状态显示
        sync_status = "已启用" if hasattr(self, 'cloud_sync') and self.cloud_sync.is_connected else "未连接"
        ttk.Label(
            cloud_frame,
            text=f"云同步状态: {sync_status}",
            style='Settings.TLabel',
            font=('Microsoft YaHei', 12)
        ).pack(pady=5)
        
        # 创建一个框架来容纳两个同步按钮
        sync_buttons_frame = ttk.Frame(cloud_frame, style='Custom.TFrame')
        sync_buttons_frame.pack(fill='x', pady=5)
        
        # 手动同步按钮
        ttk.Button(
            sync_buttons_frame,
            text="立即同步数据",
            command=self.manual_sync,
            style='Settings.TButton'
        ).pack(side='left', padx=(0, 5), expand=True, fill='x')
        
        # 用户同步按钮
        if hasattr(self, 'user_manager') and self.user_manager.is_connected:
            ttk.Button(
                sync_buttons_frame,
                text="同步用户账户",
                command=self.sync_user_accounts,
                style='Settings.TButton'
            ).pack(side='right', padx=(5, 0), expand=True, fill='x')
        
        # 主题设置
        theme_frame = create_setting_section(settings_window, "主题设置", "🎨")
        
        theme_var = tk.StringVar(value=self.settings.get('theme'))
        
        # 创建单选按钮组
        theme_options_frame = ttk.Frame(theme_frame, style='Custom.TFrame')
        theme_options_frame.pack(fill='x', pady=5)
        
        dark_radio = ttk.Radiobutton(
            theme_options_frame,
            text="深色主题",
            variable=theme_var,
            value="dark",
            style='Settings.TRadiobutton'
        )
        dark_radio.pack(side='left', padx=(0, 20))
        
        light_radio = ttk.Radiobutton(
            theme_options_frame,
            text="浅色主题",
            variable=theme_var,
            value="light",
            style='Settings.TRadiobutton'
        )
        light_radio.pack(side='left')
        
        # 透明度设置
        opacity_frame = create_setting_section(settings_window, "透明度", "🔍")
        opacity_var = tk.DoubleVar(value=self.settings.get('opacity'))
        opacity_scale = ttk.Scale(
            opacity_frame,
            from_=0.3,
            to=1.0,
            variable=opacity_var,
            orient='horizontal'
        )
        opacity_scale.pack(fill='x', pady=5)
        
        # 其他设置
        other_frame = create_setting_section(settings_window, "其他设置", "⚙️")
        
        auto_start_var = tk.BooleanVar(value=self.settings.get('auto_start'))
        auto_start_cb = ttk.Checkbutton(
            other_frame,
            text="开机自启动",
            variable=auto_start_var,
            style='Settings.TCheckbutton'
        )
        auto_start_cb.pack(pady=5, anchor='w')
        
        show_seconds_var = tk.BooleanVar(value=self.settings.get('show_seconds'))
        show_seconds_cb = ttk.Checkbutton(
            other_frame,
            text="显示秒数",
            variable=show_seconds_var,
            style='Settings.TCheckbutton'
        )
        show_seconds_cb.pack(pady=5, anchor='w')
        
        always_top_var = tk.BooleanVar(value=self.settings.get('always_on_top'))
        always_top_cb = ttk.Checkbutton(
            other_frame,
            text="窗口置顶",
            variable=always_top_var,
            style='Settings.TCheckbutton'
        )
        always_top_cb.pack(pady=5, anchor='w')
        
        # 添加计时模式选项
        timer_mode_frame = ttk.Frame(other_frame, style='Custom.TFrame')
        timer_mode_frame.pack(fill='x', pady=5, anchor='w')
        
        ttk.Label(
            timer_mode_frame,
            text="计时模式:",
            style='Settings.TLabel',
            font=('Microsoft YaHei', 12)
        ).pack(side='left', padx=(0, 10))
        
        timer_mode_var = tk.StringVar(value=self.settings.get('timer_mode'))
        
        up_radio = ttk.Radiobutton(
            timer_mode_frame,
            text="正计时",
            variable=timer_mode_var,
            value="up",
            style='Settings.TRadiobutton'
        )
        up_radio.pack(side='left', padx=(0, 20))
        
        down_radio = ttk.Radiobutton(
            timer_mode_frame,
            text="倒计时",
            variable=timer_mode_var,
            value="down",
            style='Settings.TRadiobutton'
        )
        down_radio.pack(side='left')
        
        # 保存按钮
        def save_settings():
            # 保存当前goal值
            current_goal = self.target_time_var.get()
            
            # 获取当前计时模式
            old_timer_mode = self.settings.get('timer_mode')
            new_timer_mode = timer_mode_var.get()
            
            # 保存设置
            self.settings.set('opacity', opacity_var.get())
            self.settings.set('auto_start', auto_start_var.get())
            self.settings.set('show_seconds', show_seconds_var.get())
            self.settings.set('always_on_top', always_top_var.get())
            self.settings.set('theme', theme_var.get())
            self.settings.set('timer_mode', new_timer_mode)
            
            # 应用设置
            self.apply_settings()
            
            # 如果计时模式发生变化，更新显示
            if old_timer_mode != new_timer_mode:
                # 恢复goal值
                self.target_time_var.set(current_goal)
                
                # 更新时间显示
                if new_timer_mode == 'down' and not self.is_running:
                    try:
                        target_hours = float(current_goal)
                        target_seconds = target_hours * 3600
                        hours = int(target_seconds // 3600)
                        minutes = int((target_seconds % 3600) // 60)
                        seconds = int(target_seconds % 60)
                        self.time_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    except ValueError:
                        pass
            
            # 如果启用了自启动，添加到启动项
            if auto_start_var.get():
                self.add_to_startup()
                
            settings_window.destroy()
        
        save_frame = ttk.Frame(settings_window, style='Custom.TFrame')
        save_frame.pack(fill='x', pady=20, padx=20)
        
        ttk.Button(
            save_frame,
            text="保存设置",
            command=save_settings,
            style='Settings.TButton'
        ).pack(fill='x')

    def apply_settings(self):
        """应用设置"""
        # 应用透明度和置顶设置
        self.root.attributes('-alpha', self.settings.get('opacity'))
        self.root.attributes('-topmost', self.settings.get('always_on_top'))
        self.topmost = self.settings.get('always_on_top')
        
        # 重新设置UI
        self.setup_ui()

    def show_window(self):
        window = self.root
        if not (self.user_manager.is_logged_in() and
                getattr(self, 'loading_completed', False)):
            # 登录或加载期间唤起现有对话框，避免露出空窗口或旧用户界面。
            window = next((child for child in reversed(self.root.winfo_children())
                           if isinstance(child, tk.Toplevel)), None)
            if window is None:
                return
        window.deiconify()
        window.lift()
        window.focus_force()

    def toggle_window(self):
        focused = self.root.focus_displayof()
        if (self.root.state() == 'normal' and focused is not None and
                focused.winfo_toplevel() == self.root):
            self.minimize_window()
        else:
            self.show_window()
        
    def get_period_stats(self, start_date, end_date):
        total_seconds = 0
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                current = start_date
                while current <= end_date:
                    if str(current) in data:
                        # 处理新旧两种数据格式
                        day_data = data[str(current)]
                        if isinstance(day_data, (int, float)):
                            # 旧格式：直接是秒数
                            total_seconds += day_data
                        else:
                            # 新格式：字典格式
                            total_seconds += day_data['accumulated_time']
                            # 如果当天正在计时，加上当前运行的时间
                            if day_data['is_running'] and day_data['start_time']:
                                if current == datetime.now().date():  # 只对今天的数据处理正在运行的时间
                                    elapsed = time.time() - day_data['start_time']
                                    total_seconds += elapsed
                    current += timedelta(days=1)
        except FileNotFoundError:
            pass
        return total_seconds
        
    def format_duration(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分钟"
        
    def backup_data(self):
        """备份数据文件"""
        try:
            # 创建备份目录
            backup_dir = Path('backups')
            backup_dir.mkdir(exist_ok=True)
            
            # 生成备份文件名（使用时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'work_time_{timestamp}.json'
            
            # 复制数据文件
            if self.data_file.exists():
                with open(self.data_file, 'r') as src, open(backup_file, 'w') as dst:
                    data = json.load(src)
                    json.dump(data, dst, indent=4)
                    
                # 清理旧备份（保留最近30个备份）
                backup_files = sorted(backup_dir.glob('work_time_*.json'))
                if len(backup_files) > 30:
                    for old_file in backup_files[:-30]:
                        old_file.unlink()
                        
        except Exception as e:
            print(f"备份数据时出错：{e}")

    def export_data(self, export_file=None):
        """导出数据为CSV格式"""
        try:
            if not export_file:
                # 默认导出文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_file = Path(f'work_time_export_{timestamp}.csv')
            
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # 写入CSV文件
            with open(export_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['日期', '工作时长（小时）', '是否完成目标'])
                
                for date, day_data in sorted(data.items()):
                    if isinstance(day_data, dict):
                        hours = day_data['accumulated_time'] / 3600
                        writer.writerow([
                            date,
                            f'{hours:.2f}',
                            '是' if hours >= float(self.target_time_var.get()) else '否'
                        ])
                    else:
                        # 处理旧格式数据
                        hours = day_data / 3600
                        writer.writerow([
                            date,
                            f'{hours:.2f}',
                            '是' if hours >= float(self.target_time_var.get()) else '否'
                        ])
                        
            return str(export_file)
        except Exception as e:
            print(f"导出数据时出错：{e}")
            return None

    def run(self):
        if self.settings.get('auto_start'):
            self.add_to_startup()
        try:
            # 确保在主线程中运行主循环
            self.root.mainloop()
        except Exception as e:
            print(f"主循环运行出错: {e}")
            self.quit_app()

    def quit_app(self):
        """退出应用"""
        if self._closing:
            return
        self._closing = True
        try:
            # 保存当前状态
            if hasattr(self, 'is_running') and self.is_running:
                self.toggle_timer()
                
            # 备份数据
            if hasattr(self, 'data_file'):
                self.backup_data()
                
            # 停止文件监听器
            if hasattr(self, 'observer'):
                self.observer.stop()
                self.observer.join()
                
            # 停止托盘图标
            if hasattr(self, 'tray_icon'):
                self.tray_icon.stop()
                
            # 退出主窗口
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"退出应用时出错: {e}")
            # 强制退出
            self.root.destroy()
            sys.exit(0)

    def update_status(self):
        """更新状态显示"""
        if self.is_running:
            self.status_label.configure(text="Working...")  # 更改状态文本
        else:
            self.status_label.configure(text="Paused")

    def show_celebration(self, is_target_completed=False):
        """显示庆祝动画"""
        # 如果目标时间为0或焦点在目标输入框上，不显示庆祝
        if (is_target_completed and float(self.target_time_var.get()) <= 0) or \
           self.root.focus_get() == self.target_entry:
            return
            
        # 播放庆祝音效
        try:
            if is_target_completed:
                # 目标完成时播放"bingo"风格音效
                self.sound_manager.play_sound('bingo')
            else:
                # 每小时完成时播放"levelup"风格音效
                self.sound_manager.play_sound('levelup')
        except Exception as e:
            print(f"播放音效失败: {e}")
            
        # 创建庆祝窗口
        celebration = tk.Toplevel(self.root)
        celebration.overrideredirect(True)
        celebration.attributes('-topmost', True)
        celebration.attributes('-alpha', 0.0)  # 初始透明
        
        # 设置窗口图标
        self.set_window_icon(celebration)
        
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        
        celebration.configure(bg=colors['bg'])
        
        # 设置窗口位置（在屏幕中心）
        screen_width = celebration.winfo_screenwidth()
        screen_height = celebration.winfo_screenheight()
        
        if is_target_completed:
            window_width = 500  # 增大庆祝窗口尺寸
            window_height = 400
        else:
            window_width = 400
            window_height = 300
            
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        celebration.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # 创建关闭按钮
        close_button = ttk.Button(
            celebration,
            text="✕",
            style='Icon.TButton',
            command=celebration.destroy,
            width=2
        )
        close_button.pack(side='top', anchor='ne', padx=10, pady=5)
        
        # 判断是否是倒计时完成
        timer_mode = self.settings.get('timer_mode')
        is_countdown_completed = timer_mode == 'down' and hasattr(self, 'countdown_completed') and self.countdown_completed
        
        if is_target_completed:
            # 目标完成庆祝
            emojis = "🎉 🌟 🎊 ⭐"
            congrats_label = ttk.Label(
                celebration,
                text=emojis,
                font=('Segoe UI Emoji', 36),
                background=colors['bg'],
                foreground=colors['fg']
            )
            congrats_label.pack(pady=(10, 5))
            
            title_label = ttk.Label(
                celebration,
                text="恭喜你！",
                font=('Microsoft YaHei', 32, 'bold'),
                background=colors['bg'],
                foreground=colors['fg']
            )
            title_label.pack(pady=5)
            
            # 根据计时模式显示不同消息
            if is_countdown_completed:
                message_text = f"你已完成 {self.target_time_var.get()} 小时的目标！"
            else:
                message_text = f"你已完成 {self.target_time_var.get()} 小时的目标！"
                
            message_label = ttk.Label(
                celebration,
                text=message_text,
                font=('Microsoft YaHei', 18),
                background=colors['bg'],
                foreground=colors['fg'],
                justify='center'
            )
            message_label.pack(pady=5)
            
            # 继续工作的提示
            continue_label = ttk.Label(
                celebration,
                text="You are the best!",
                font=('Microsoft YaHei', 14),
                background=colors['bg'],
                foreground=colors['fg_secondary'],
                justify='center'
            )
            continue_label.pack(pady=10)
        else:
            # 每小时庆祝
            hours_completed = int(self.accumulated_time // 3600)
            if self.is_running and self.start_time:
                hours_completed = int((self.accumulated_time + time.time() - self.start_time) // 3600)
                
            congrats_label = ttk.Label(
                celebration,
                text="🎉",
                font=('Segoe UI Emoji', 48),
                background=colors['bg'],
                foreground=colors['fg']
            )
            congrats_label.pack(pady=(20, 10))
            
            message_label = ttk.Label(
                celebration,
                text=f"太棒了！\n已完成 {hours_completed} 小时！",
                font=('Microsoft YaHei', 18, 'bold'),
                background=colors['bg'],
                foreground=colors['fg'],
                justify='center'
            )
            message_label.pack(pady=10)
        
        # 渐入动画
        def fade_in():
            alpha = celebration.attributes('-alpha')
            if alpha < 1.0:
                celebration.attributes('-alpha', min(alpha + 0.1, 1.0))
                celebration.after(20, fade_in)
                
        fade_in()
        
        # 如果不是目标完成，5秒后自动关闭
        if not is_target_completed:
            celebration.after(5000, celebration.destroy)

    def handle_logout(self):
        """处理登出"""
        if messagebox.askyesno("确认", "确定要退出登录吗？"):
            # 保存当前数据
            self.save_data()
            
            # 关闭云同步
            if hasattr(self, 'cloud_sync'):
                self.cloud_sync.close()
                delattr(self, 'cloud_sync')
            
            # 登出用户
            self.user_manager.logout()
            
            # 重置计时器
            self.reset_timer()
            
            # 关闭设置窗口（如果存在）
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            
            # 隐藏主窗口
            self.root.withdraw()
            
            # 显示登录窗口
            self.show_login_window()

    def manual_sync(self):
        """手动同步数据"""
        try:
            data = self.cloud_sync.sync_data()
            if data:
                self.work_time_data = data
                messagebox.showinfo("同步成功", "数据已同步")
            else:
                messagebox.showwarning("同步失败", "无法连接到云端，请检查网络连接")
        except Exception as e:
            messagebox.showerror("同步错误", f"同步过程中出现错误：{str(e)}")

    def on_closing(self):
        """关闭程序时的处理"""
        self._closing = True
        self.save_data()  # 保存并同步数据
        if hasattr(self, 'cloud_sync'):
            self.cloud_sync.close()  # 关闭MongoDB连接
        if hasattr(self, 'user_manager'):
            self.user_manager.close()  # 关闭用户管理器的MongoDB连接
        self.root.destroy()

    def update_timer(self):
        """更新计时器显示"""
        if self.is_running:
            # 更新当前时间
            current_time = time.time()
            elapsed = current_time - self.start_time
            self.accumulated_time += elapsed
            self.start_time = current_time
            
            # 获取计时模式
            timer_mode = self.settings.get('timer_mode')
            
            # 检查是否达到整小时，显示每小时庆祝
            if timer_mode == 'up':  # 正计时模式
                # 正计时模式下，检查累计时间是否达到整小时
                if not hasattr(self, 'last_hour'):
                    self.last_hour = int(self.accumulated_time // 3600)
                
                current_hour = int(self.accumulated_time // 3600)
                if current_hour > self.last_hour:
                    # 每小时庆祝一次
                    self.show_celebration(is_target_completed=False)
                    self.last_hour = current_hour
            else:  # 倒计时模式
                # 倒计时模式下，检查剩余时间的整小时变化
                try:
                    target_hours = float(self.target_time_var.get())
                    target_seconds = target_hours * 3600
                    remaining_seconds = max(0, target_seconds - self.accumulated_time)
                    remaining_hours = int(remaining_seconds // 3600)
                    
                    # 初始化上次检查的剩余小时数
                    if not hasattr(self, 'last_remaining_hour'):
                        self.last_remaining_hour = remaining_hours
                    
                    # 当剩余小时数减少1时触发庆祝
                    if remaining_hours < self.last_remaining_hour and remaining_hours >= 0:
                        self.show_celebration(is_target_completed=False)
                        self.last_remaining_hour = remaining_hours
                except (ValueError, AttributeError) as e:
                    print(f"倒计时模式检查小时变化出错: {e}")
            
            # 更新显示
            self.update_display()
            
            # 自动保存数据
            if not hasattr(self, 'last_save_time'):
                self.last_save_time = current_time
                self.auto_save_interval = 60  # 60秒自动保存一次
                
            if current_time - self.last_save_time >= self.auto_save_interval:
                self.save_data()
                self.last_save_time = current_time
        else:
            # 即使不在运行状态，也更新显示，确保显示历史数据
            self.update_display()
        
        # 更新状态栏
        if hasattr(self, 'status_bar'):
            self.update_status_bar()
        
        # 每60秒检查一次云同步状态
        current_time = time.time()
        if hasattr(self, 'last_cloud_check_time'):
            if current_time - self.last_cloud_check_time >= 60:
                self.check_cloud_connection()
                self.last_cloud_check_time = current_time
        else:
            self.last_cloud_check_time = current_time
        
        # 继续更新
        self.root.after(1000, self.update_timer)
    
    def check_cloud_connection(self):
        """检查云连接状态"""
        connection_changed = False
        
        # 检查数据同步云连接
        if hasattr(self, 'cloud_sync'):
            # 如果云同步对象存在，尝试ping服务器
            if hasattr(self.cloud_sync, 'client'):
                try:
                    # 尝试ping服务器
                    if not self.cloud_sync.is_connected:
                        self.cloud_sync.client.admin.command('ping')
                        self.cloud_sync.is_connected = True
                        print("MongoDB重新连接成功")
                        connection_changed = True
                except Exception as e:
                    # 如果之前是连接状态，现在连接失败，更新状态
                    if self.cloud_sync.is_connected:
                        self.cloud_sync.is_connected = False
                        print(f"MongoDB连接已断开: {e}")
                        connection_changed = True
                    else:
                        print(f"MongoDB连接检查失败: {e}")
        
        # 检查用户管理器云连接
        if hasattr(self, 'user_manager') and hasattr(self.user_manager, 'client'):
            try:
                # 尝试ping服务器
                if not self.user_manager.is_connected:
                    self.user_manager.client.admin.command('ping')
                    self.user_manager.is_connected = True
                    print("用户管理MongoDB重新连接成功")
                    connection_changed = True
                    
                    # 连接恢复后，尝试同步用户数据
                    self.user_manager.sync_users()
            except Exception as e:
                # 如果之前是连接状态，现在连接失败，更新状态
                if self.user_manager.is_connected:
                    self.user_manager.is_connected = False
                    print(f"用户管理MongoDB连接已断开: {e}")
                    connection_changed = True
                else:
                    print(f"用户管理MongoDB连接检查失败: {e}")
        
        # 如果连接状态有变化，更新状态栏
        if connection_changed:
            self.update_status_bar()

    def show_donate(self):
        """显示打赏二维码"""
        donate_window = tk.Toplevel(self.root)
        donate_window.title("you are the best!")
        
        # 设置窗口图标
        self.set_window_icon(donate_window)
        
        # 获取当前主题
        theme = self.settings.get('theme')
        colors = self.DARK_THEME if theme == 'dark' else self.LIGHT_THEME
        
        donate_window.configure(bg=colors['bg'])
        donate_window.geometry("400x500")
        
        # 创建主容器
        main_frame = ttk.Frame(donate_window, style='Custom.TFrame')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # 添加标题
        title_label = ttk.Label(
            main_frame,
            text="you are the best!",
            font=('Calibri', 18, 'bold'),
            foreground=colors['fg'],
            background=colors['bg']
        )
        title_label.pack(pady=(0, 20))
        
        # 加载并显示二维码图片
        # 尝试多个可能的路径
        qr_paths = []
        
        # 添加PyInstaller打包后的路径
        if getattr(sys, 'frozen', False):
            # 如果是PyInstaller打包的应用
            base_path = sys._MEIPASS
            qr_paths.append(os.path.join(base_path, "donate_qr.png"))
        
        # 添加其他可能的路径
        qr_paths.extend([
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "donate_qr.png"),  # 脚本所在目录
            os.path.join(os.getcwd(), "donate_qr.png"),  # 当前工作目录
            "donate_qr.png",  # 当前目录
            os.path.join(os.path.dirname(sys.executable), "donate_qr.png"),  # 可执行文件所在目录
        ])
        
        # 打印当前路径信息，帮助调试
        print(f"当前工作目录: {os.getcwd()}")
        print(f"脚本所在目录: {os.path.dirname(os.path.abspath(__file__))}")
        print(f"可执行文件所在目录: {os.path.dirname(sys.executable)}")
        if getattr(sys, 'frozen', False):
            print(f"PyInstaller临时目录: {sys._MEIPASS}")
        
        qr_path = None
        for path in qr_paths:
            print(f"尝试查找二维码图片: {path}")
            if os.path.exists(path):
                qr_path = path
                print(f"找到二维码图片: {qr_path}")
                break
        
        if not qr_path:
            # 如果所有路径都不存在，使用第一个路径作为默认
            qr_path = qr_paths[0]
            print(f"未找到二维码图片，将尝试在以下路径创建默认图片: {qr_path}")
            try:
                # 创建一个简单的图片作为默认二维码
                from PIL import Image, ImageDraw, ImageFont
                
                # 创建一个白色背景的图片
                img = Image.new('RGB', (300, 300), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                # 添加文字
                try:
                    font = ImageFont.truetype("simhei.ttf", 20)
                except:
                    font = ImageFont.load_default()
                    
                # 绘制边框
                draw.rectangle([(10, 10), (290, 290)], outline=(0, 0, 0), width=2)
                
                # 添加文字
                draw.text((50, 120), "感谢您的支持！", fill=(0, 0, 0), font=font)
                draw.text((50, 160), "请添加二维码图片", fill=(0, 0, 0), font=font)
                
                # 保存图片
                img.save(qr_path)
                print(f"已创建默认二维码图片: {qr_path}")
            except Exception as e:
                print(f"创建默认二维码图片失败: {e}")
        
        try:
            # 尝试加载图片
            from PIL import Image, ImageTk
            qr_image = Image.open(qr_path)
            
            # 将图片缩小到适当大小
            qr_image = qr_image.resize((300, 300))
            qr_photo = ImageTk.PhotoImage(qr_image)
            
            # 创建图片标签
            qr_label = ttk.Label(
                main_frame,
                image=qr_photo,
                background=colors['bg']
            )
            qr_label.image = qr_photo  # 保持引用，防止被垃圾回收
            qr_label.pack(pady=10)
        except Exception as e:
            # 如果图片加载失败，创建一个内存中的图片
            print(f"加载打赏二维码失败: {e}，将创建内存中的图片")
            try:
                # 创建一个简单的图片作为默认二维码
                from PIL import Image, ImageTk, ImageDraw, ImageFont
                img = Image.new('RGB', (300, 300), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                # 绘制边框
                draw.rectangle([(10, 10), (290, 290)], outline=(0, 0, 0), width=2)
                
                # 添加文字
                try:
                    font = ImageFont.truetype("simhei.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                draw.text((50, 120), "感谢您的支持！", fill=(0, 0, 0), font=font)
                draw.text((50, 160), "二维码加载失败", fill=(0, 0, 0), font=font)
                
                # 直接使用内存中的图片
                qr_photo = ImageTk.PhotoImage(img)
                
                # 创建图片标签
                qr_label = ttk.Label(
                    main_frame,
                    image=qr_photo,
                    background=colors['bg']
                )
                qr_label.image = qr_photo  # 保持引用，防止被垃圾回收
                qr_label.pack(pady=10)
            except Exception as inner_e:
                # 如果内存图片也失败，显示错误文本
                error_label = ttk.Label(
                    main_frame,
                    text=f"二维码图片加载失败\n尝试路径: {qr_path}\n错误: {str(e)}",
                    foreground=colors['fg'],
                    background=colors['bg'],
                    font=('Microsoft YaHei', 14)
                )
                error_label.pack(pady=50)
                print(f"创建内存图片也失败: {inner_e}")
        
        # 添加说明文字
        desc_label = ttk.Label(
            main_frame,
            text="您的支持是我们持续改进的动力！",
            foreground=colors['fg'],
            background=colors['bg'],
            font=('Microsoft YaHei', 12),
            wraplength=350,
            justify='center'
        )
        desc_label.pack(pady=10)
        
        # 添加关闭按钮
        close_button = ttk.Button(
            main_frame,
            text="关闭",
            command=donate_window.destroy,
            style='Settings.TButton'
        )
        close_button.pack(pady=20)

    def update_status_bar(self):
        """更新状态栏信息"""
        try:
            # 检查status_bar是否存在
            if not hasattr(self, 'status_bar'):
                # 如果不存在，可能是在UI初始化之前调用了此方法
                return
                
            # 构建状态栏文本
            status_parts = []
            
            # 添加用户信息
            if self.user_manager.is_logged_in():
                username = self.user_manager.get_current_user()
                status_parts.append(f"用户: {username}")
            
            # 添加云同步状态
            if hasattr(self, 'cloud_sync'):
                sync_status = "已连接" if self.cloud_sync.is_connected else "未连接"
                status_parts.append(f"云同步: {sync_status}")
            
            # 添加最后保存时间
            if hasattr(self, 'last_save_time'):
                last_save = time.strftime("%H:%M:%S", time.localtime(self.last_save_time))
                status_parts.append(f"最后保存: {last_save}")
            
            # 组合状态文本
            status_text = " | ".join(status_parts)
            
            # 更新状态栏
            self.status_bar.config(text=status_text)
        except Exception as e:
            print(f"更新状态栏时出错: {e}")
            # 错误不应影响主程序运行

    def sync_user_accounts(self):
        """同步用户账户数据"""
        try:
            if hasattr(self, 'user_manager') and self.user_manager.is_connected:
                # 显示同步中提示
                self.root.config(cursor="wait")
                self.root.update()
                
                # 执行同步，强制同步所有用户
                self.user_manager.sync_users(force=True)
                
                # 恢复光标
                self.root.config(cursor="")
                
                # 显示成功消息
                messagebox.showinfo("同步成功", "用户账户数据已同步")
            else:
                messagebox.showwarning("同步失败", "无法连接到云端，请检查网络连接")
        except Exception as e:
            # 恢复光标
            if hasattr(self, 'root'):
                self.root.config(cursor="")
            messagebox.showerror("同步错误", f"同步用户账户时出现错误：{str(e)}")

    def open_github(self):
        """打开GitHub项目页面"""
        try:
            import webbrowser
            webbrowser.open("https://github.com/ppxinyue/Pimer")
        except Exception as e:
            print(f"打开GitHub链接失败: {e}")
            messagebox.showerror("错误", f"无法打开链接: {e}")
            
    def get_icon_path(self):
        """获取图标文件路径，支持开发环境和PyInstaller环境"""
        # 尝试多个可能的路径
        icon_paths = []
        
        # 添加PyInstaller打包后的路径
        if getattr(sys, 'frozen', False):
            # 如果是PyInstaller打包的应用
            base_path = sys._MEIPASS
            icon_paths.append(os.path.join(base_path, "pig_nose_icon.ico"))
        
        # 添加其他可能的路径
        icon_paths.extend([
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "pig_nose_icon.ico"),  # 脚本所在目录
            os.path.join(os.getcwd(), "pig_nose_icon.ico"),  # 当前工作目录
            "pig_nose_icon.ico",  # 当前目录
            os.path.join(os.path.dirname(sys.executable), "pig_nose_icon.ico"),  # 可执行文件所在目录
        ])
        
        # 遍历所有可能的路径
        for path in icon_paths:
            if os.path.exists(path):
                return path
                
        return None  # 如果找不到图标文件，返回None

    def set_window_icon(self, window):
        """设置窗口图标"""
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            try:
                window.iconbitmap(icon_path)
            except Exception as e:
                print(f"设置窗口图标失败: {e}")

class SoundManager:
    """音效管理器类，用于管理和播放不同类型的音效"""
    
    def __init__(self):
        # 音效文件目录
        self.sounds_dir = self.get_sounds_dir()
        
        # 确保音效目录存在
        self.sounds_dir.mkdir(exist_ok=True)
        
        # 定义音效文件路径
        self.sound_files = {
            'bingo': self.sounds_dir / 'bingo.wav',
            'achievement': self.sounds_dir / 'achievement.wav',
            'levelup': self.sounds_dir / 'levelup.wav',
            'success': self.sounds_dir / 'success.wav'
        }
        
        # 检查音效文件是否存在，不存在则创建默认音效
        self.check_sound_files()
        
    def get_sounds_dir(self):
        """获取音效目录路径，支持开发环境和PyInstaller环境"""
        # 尝试多个可能的路径
        possible_paths = []
        
        # 添加PyInstaller打包后的路径
        if getattr(sys, 'frozen', False):
            # 如果是PyInstaller打包的应用
            base_path = sys._MEIPASS
            possible_paths.append(os.path.join(base_path, "sounds"))
        
        # 添加其他可能的路径
        possible_paths.extend([
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds"),  # 脚本所在目录
            os.path.join(os.getcwd(), "sounds"),  # 当前工作目录
            "sounds",  # 当前目录
            os.path.join(os.path.dirname(sys.executable), "sounds"),  # 可执行文件所在目录
        ])
        
        # 遍历所有可能的路径
        for path in possible_paths:
            if os.path.exists(path):
                return Path(path)
                
        # 如果找不到目录，返回当前目录下的sounds文件夹
        return Path("sounds")
        
    def check_sound_files(self):
        """检查音效文件是否存在，不存在则使用系统音效"""
        for sound_name, sound_path in self.sound_files.items():
            if not sound_path.exists():
                print(f"音效文件 {sound_name} 不存在: {sound_path}")
    
    def play_system_sound(self, sound_type='bingo'):
        """播放系统音效"""
        try:
            if sound_type == 'bingo':
                # 播放"bingo"风格的系统音效组合
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
                time.sleep(0.25)
                winsound.PlaySound("SystemStart", winsound.SND_ASYNC)
                time.sleep(0.35)
                winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                time.sleep(0.4)
                winsound.PlaySound("SystemQuestion", winsound.SND_ASYNC)
            elif sound_type == 'achievement':
                # 播放"成就"风格的系统音效组合
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
                time.sleep(0.3)
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
                time.sleep(0.3)
                winsound.PlaySound("SystemStart", winsound.SND_ASYNC)
            elif sound_type == 'levelup':
                # 播放"升级"风格的系统音效组合
                winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                time.sleep(0.3)
                winsound.PlaySound("SystemStart", winsound.SND_ASYNC)
                time.sleep(0.3)
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
            else:
                # 默认音效
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
        except Exception as e:
            print(f"播放系统音效失败: {e}")
    
    def play_custom_sound(self, sound_type='bingo'):
        """播放自定义音效"""
        if not PLAYSOUND_AVAILABLE:
            self.play_system_sound(sound_type)
            return
            
        try:
            sound_path = self.sound_files.get(sound_type)
            if sound_path and sound_path.exists():
                # 修复路径格式，使用正斜杠而不是反斜杠
                sound_path_str = str(sound_path.absolute()).replace('\\', '/')
                # 使用winsound播放音效，避免playsound的路径问题
                winsound.PlaySound(sound_path_str, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # 如果自定义音效不存在，使用系统音效
                self.play_system_sound(sound_type)
        except Exception as e:
            print(f"播放自定义音效失败: {e}")
            # 失败时尝试使用系统音效
            self.play_system_sound(sound_type)
    
    def play_sound(self, sound_type='bingo', use_custom=True):
        """播放音效，可选择使用自定义音效或系统音效"""
        if use_custom:
            # 在单独的守护线程中播放音效
            sound_thread = threading.Thread(target=self.play_custom_sound, args=(sound_type,), daemon=True)
            sound_thread.start()
        else:
            # 在单独的守护线程中播放系统音效
            sound_thread = threading.Thread(target=self.play_system_sound, args=(sound_type,), daemon=True)
            sound_thread.start()

if __name__ == "__main__":
    try:
        app = WorkTimer()
        app.run()
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)
