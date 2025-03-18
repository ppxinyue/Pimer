import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from datetime import datetime, timedelta
import os
import sys
import winreg as reg
from tkinter import font as tkfont
import csv
import calendar
from PIL import Image, ImageTk
import pystray
import threading
import keyboard
from pathlib import Path
import shutil

class Settings:
    def __init__(self):
        self.config_file = 'settings.json'
        self.default_settings = {
            'theme': 'dark',
            'opacity': 1.0,
            'daily_goal': 8 * 3600,  # 8小时
            'auto_start': True,
            'show_seconds': True,
            'always_on_top': True,
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
    def __init__(self):
        self.settings = Settings()
        self.root = tk.Tk()
        self.root.title("Work Timer Pro")
        
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
        
        # 加载图标
        self.load_icons()
        
        # 绑定事件
        self.bind_events()
        
        # 先加载数据，再设置UI
        self.setup_variables()
        self.load_data()  # 确保在setup_ui之前加载数据
        
        self.setup_ui()
        self.setup_tray()
        self.setup_hotkeys()
        self.update_timer()  # 开始更新计时器
        
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
        self.window_visible = False
        
    def toggle_timer(self):
        if self.is_running:
            self.is_running = False
            self.toggle_button.configure(text=self.icons['play'])
            self.status_label.configure(text="Paused")
            if self.start_time:
                self.accumulated_time += time.time() - self.start_time
                self.save_data()
        else:
            self.is_running = True
            self.toggle_button.configure(text=self.icons['pause'])
            self.status_label.configure(text="Working...")
            self.start_time = time.time()
        # 更新进度条
        self.update_progress()
        
    def reset_timer(self):
        if self.is_running:
            self.toggle_timer()
        self.accumulated_time = 0
        self.start_time = None
        self.save_data()
        self.time_label.configure(text="00:00:00")
        self.status_label.configure(text="Ready")
        self.progress['value'] = 0
        self.toggle_button.configure(text=self.icons['play'])  # 确保显示播放图标
        if hasattr(self, 'target_completed'):
            delattr(self, 'target_completed')
        
    def load_data(self):
        try:
            with open('work_time.json', 'r') as f:
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
            
        # 保存当前状态
        self.save_data()
        
    def save_data(self):
        try:
            # 读取现有数据
            with open('work_time.json', 'r') as f:
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
        with open('work_time.json', 'w') as f:
            json.dump(data, f)
            
    def add_to_startup(self):
        script_path = os.path.abspath(sys.argv[0])
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
            reg.SetValueEx(key, "WorkTimer", 0, reg.REG_SZ, script_path)
            reg.CloseKey(key)
            return True
        except WindowsError:
            return False
        
    def setup_ui(self):
        # 设置窗口样式和初始大小
        self.root.configure(bg='#2c2c2e')  # 深空灰背景色
        self.root.geometry('500x300+50+50')  # 进一步增大初始窗口尺寸
        
        # 创建自定义字体
        self.time_font = tkfont.Font(family="Calibri", size=52, weight="bold")
        self.status_font = tkfont.Font(family="Calibri", size=24)
        self.button_font = tkfont.Font(family="Segoe UI Emoji", size=18)
        self.input_font = tkfont.Font(family="Calibri", size=24, weight="bold")  # 加大目标输入框字体
        
        # 设置主题样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 配置自定义样式
        self.style.configure(
            'Custom.TFrame',
            background='#2c2c2e'
        )
        
        # 时间显示样式
        self.style.configure(
            'Timer.TLabel',
            background='#2c2c2e',
            foreground='#ffffff',  # 纯白色
            font=self.time_font,
            padding=5
        )
        
        # 状态标签样式
        self.style.configure(
            'Status.TLabel',
            background='#2c2c2e',
            foreground='#98989d',  # 浅灰色
            font=self.status_font  # 使用更大的字体
        )
        
        # 输入框样式
        self.style.configure(
            'Target.TEntry',
            fieldbackground='#3a3a3c',
            foreground='#ffffff',
            insertcolor='#ffffff',
            font=('Calibri', 24, 'bold'),  # 增大输入框字体
            padding=5
        )
        
        # 按钮样式 - 更新按钮样式使图标更突出
        self.style.configure(
            'Icon.TButton',
            background='#2c2c2e',
            foreground='#ffffff',  # 改为白色使图标更清晰
            font=self.button_font,
            padding=4,  # 增加内边距
            relief='flat',  # 扁平化设计
            borderwidth=0  # 移除边框
        )
        
        self.style.map('Icon.TButton',
            background=[('active', '#3a3a3c')],  # 悬停时稍微变亮
            foreground=[('active', '#ffffff')]   # 保持图标颜色
        )

        # 进度条样式 - 修复进度条显示
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#3a3a3c',  # 进度条背景色
            background='#0a84ff',   # 使用纯色而不是渐变
            thickness=4,  # 保持厚度
            borderwidth=0,  # 无边框
            pbarrelief='flat'  # 扁平化
        )

        # 创建主框架
        self.main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        self.main_frame.pack(expand=True, fill='both', padx=25, pady=20)  # 增加边距

        # 时间显示框架
        self.time_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        self.time_frame.pack(expand=True, fill='both')

        # 时间标签
        self.time_label = ttk.Label(
            self.time_frame,
            text="00:00:00",
            style='Timer.TLabel',
            anchor='center'
        )
        self.time_label.pack(expand=True, fill='both')

        # 状态标签
        self.status_label = ttk.Label(
            self.time_frame,
            text="Ready",
            style='Status.TLabel',
            anchor='center'
        )
        self.status_label.pack(fill='x', pady=(0, 10))  # 增加底部间距

        # 创建进度条和目标时间输入框的容器
        progress_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        progress_frame.pack(fill='x', padx=20, pady=(5, 15))

        # 进度条
        self.progress = ttk.Progressbar(
            progress_frame,
            style="Custom.Horizontal.TProgressbar",
            mode='determinate',
            length=200
        )
        self.progress.pack(side='left', fill='x', expand=True, padx=(0, 10))

        # 创建时间输入容器
        time_input_frame = ttk.Frame(progress_frame, style='Custom.TFrame')
        time_input_frame.pack(side='right')

        # 添加 Goal 提示标签
        goal_label = ttk.Label(
            time_input_frame,
            text='Goal:',
            style='Status.TLabel',
            font=('Calibri', 20)
        )
        goal_label.pack(side='left', padx=(0, 5))

        # 目标时长输入框
        self.target_time_var = tk.StringVar(value='1.0')
        self.target_entry = ttk.Entry(
            time_input_frame,
            textvariable=self.target_time_var,
            style='Target.TEntry',
            width=4,
            justify='right'
        )
        self.target_entry.pack(side='left')
        
        # 绑定输入框验证
        self.target_entry.bind('<FocusOut>', self.validate_target_time)
        self.target_entry.bind('<Return>', self.validate_target_time)

        # 控制按钮框架
        self.button_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        self.button_frame.pack(fill='x')

        # 控制按钮样式
        button_style = {'style': 'Icon.TButton', 'width': 3}

        # 开始/暂停按钮
        self.toggle_button = ttk.Button(
            self.button_frame,
            text=self.icons['pause'] if self.is_running else self.icons['play'],  # 修正图标显示逻辑
            command=self.toggle_timer,
            **button_style
        )
        self.toggle_button.pack(side='left', padx=3)

        # 重置按钮
        self.reset_button = ttk.Button(
            self.button_frame,
            text=self.icons['reset'],
            command=self.reset_timer,
            **button_style
        )
        self.reset_button.pack(side='left', padx=3)

        # 右侧控制按钮
        self.close_button = ttk.Button(
            self.button_frame,
            text=self.icons['close'],
            command=self.quit_app,
            **button_style
        )
        self.close_button.pack(side='right', padx=3)

        self.pin_button = ttk.Button(
            self.button_frame,
            text=self.icons['pin'] if self.topmost else self.icons['unpin'],
            command=self.toggle_topmost,
            **button_style
        )
        self.pin_button.pack(side='right', padx=3)

        self.settings_button = ttk.Button(
            self.button_frame,
            text=self.icons['settings'],
            command=self.show_settings,
            **button_style
        )
        self.settings_button.pack(side='right', padx=3)

        self.stats_button = ttk.Button(
            self.button_frame,
            text=self.icons['stats'],
            command=self.show_statistics,
            **button_style
        )
        self.stats_button.pack(side='right', padx=3)
        
    def setup_variables(self):
        self.is_running = False
        self.start_time = None
        self.accumulated_time = 0
        self.today = datetime.now().date()
        self.is_dragging = False
        self.resize_edge = None
        self.window_visible = True
        
    def setup_tray(self):
        # 创建系统托盘图标
        image = Image.new('RGB', (64, 64), color='#1e1e2e')
        menu = pystray.Menu(
            pystray.MenuItem("显示/隐藏", self.toggle_window),
            pystray.MenuItem("开始/暂停", self.toggle_timer),
            pystray.MenuItem("统计", self.show_statistics),
            pystray.MenuItem("设置", self.show_settings),
            pystray.MenuItem("退出", self.quit_app)
        )
        self.tray_icon = pystray.Icon(
            "work_timer",
            image,
            "Work Timer Pro",
            menu
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
    def setup_hotkeys(self):
        keyboard.add_hotkey(
            self.settings.get('hotkeys')['toggle_timer'],
            self.toggle_timer
        )
        keyboard.add_hotkey(
            self.settings.get('hotkeys')['show_hide'],
            self.toggle_window
        )
        
    def show_statistics(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Statistics")
        stats_window.geometry("500x700")  # 增大统计窗口尺寸
        stats_window.configure(bg='#2c2c2e')
        
        # 设置样式
        style = ttk.Style(stats_window)
        style.configure('Stats.TLabel',
            background='#2c2c2e',
            foreground='#ffffff',
            font=('Calibri', 16),  # 加大字体
            padding=10
        )
        style.configure('StatsValue.TLabel',
            background='#2c2c2e',
            foreground='#666666',  # 改为灰色
            font=('Calibri', 28, 'bold'),  # 加大字体
            padding=10
        )
        style.configure('Stats.TButton',
            font=('Calibri', 12),
            padding=10
        )
        
        # 创建统计数据
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # 获取统计数据
        daily_stats = self.get_period_stats(today, today)
        weekly_stats = self.get_period_stats(week_start, today)
        monthly_stats = self.get_period_stats(month_start, today)
        
        # 创建统计卡片
        def create_stat_card(parent, title, value, icon):
            frame = ttk.Frame(parent, style='Custom.TFrame')
            frame.pack(fill='x', pady=10, padx=20)
            
            # 标题行带图标
            title_frame = ttk.Frame(frame, style='Custom.TFrame')
            title_frame.pack(fill='x')
            
            icon_label = ttk.Label(
                title_frame,
                text=icon,
                style='Stats.TLabel',
                font=('Segoe UI Emoji', 18)
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
            ).pack(fill='x')
            
        # 显示统计信息
        create_stat_card(stats_window, "Today's Work Time", self.format_duration(daily_stats), "📅")
        create_stat_card(stats_window, "This Week", self.format_duration(weekly_stats), "📊")
        create_stat_card(stats_window, "This Month", self.format_duration(monthly_stats), "📈")
        
        # 添加导出按钮
        export_frame = ttk.Frame(stats_window, style='Custom.TFrame')
        export_frame.pack(fill='x', pady=20, padx=20)
        
        ttk.Button(
            export_frame,
            text="Export Data",
            command=self.export_data,
            style='Stats.TButton'
        ).pack(fill='x')
        
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x700")  # 增大设置窗口尺寸
        settings_window.configure(bg='#2c2c2e')
        
        # 设置样式
        style = ttk.Style(settings_window)
        style.configure('Settings.TLabel',
            background='#2c2c2e',
            foreground='#ffffff',
            font=('Calibri', 16),  # 加大字体
            padding=10
        )
        style.configure('Settings.TCheckbutton',
            background='#2c2c2e',
            foreground='#ffffff',
            font=('Calibri', 14)  # 加大字体
        )
        style.configure('Settings.TButton',
            font=('Calibri', 12),
            padding=10
        )
        
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
            
        # 主题设置
        theme_frame = create_setting_section(settings_window, "Theme", "🎨")
        theme_var = tk.StringVar(value=self.settings.get('theme'))
        ttk.Radiobutton(
            theme_frame,
            text="Dark Mode",
            value="dark",
            variable=theme_var,
            style='Settings.TCheckbutton'
        ).pack(pady=5)
        ttk.Radiobutton(
            theme_frame,
            text="Light Mode",
            value="light",
            variable=theme_var,
            style='Settings.TCheckbutton'
        ).pack(pady=5)
        
        # 透明度设置
        opacity_frame = create_setting_section(settings_window, "Opacity", "🔍")
        opacity_var = tk.DoubleVar(value=self.settings.get('opacity'))
        opacity_scale = ttk.Scale(
            opacity_frame,
            from_=0.3,
            to=1.0,
            variable=opacity_var,
            orient='horizontal'
        )
        opacity_scale.pack(fill='x', pady=5)
        
        # 每日目标设置
        goal_frame = create_setting_section(settings_window, "Daily Goal", "🎯")
        goal_var = tk.IntVar(value=max(1, self.settings.get('daily_goal') // 3600))
        ttk.Spinbox(
            goal_frame,
            from_=1,
            to=24,
            textvariable=goal_var,
            style='Settings.TSpinbox'
        ).pack(pady=5)
        
        # 其他设置
        other_frame = create_setting_section(settings_window, "Other Settings", "⚙️")
        
        auto_start_var = tk.BooleanVar(value=self.settings.get('auto_start'))
        ttk.Checkbutton(
            other_frame,
            text="Start with Windows",
            variable=auto_start_var,
            style='Settings.TCheckbutton'
        ).pack(pady=5)
        
        show_seconds_var = tk.BooleanVar(value=self.settings.get('show_seconds'))
        ttk.Checkbutton(
            other_frame,
            text="Show Seconds",
            variable=show_seconds_var,
            style='Settings.TCheckbutton'
        ).pack(pady=5)
        
        always_top_var = tk.BooleanVar(value=self.settings.get('always_on_top'))
        ttk.Checkbutton(
            other_frame,
            text="Always on Top",
            variable=always_top_var,
            style='Settings.TCheckbutton'
        ).pack(pady=5)
        
        # 保存按钮
        def save_settings():
            self.settings.set('theme', theme_var.get())
            self.settings.set('opacity', opacity_var.get())
            self.settings.set('daily_goal', max(3600, goal_var.get() * 3600))
            self.settings.set('auto_start', auto_start_var.get())
            self.settings.set('show_seconds', show_seconds_var.get())
            self.settings.set('always_on_top', always_top_var.get())
            self.apply_settings()
            settings_window.destroy()
            
        save_frame = ttk.Frame(settings_window, style='Custom.TFrame')
        save_frame.pack(fill='x', pady=20, padx=20)
        
        ttk.Button(
            save_frame,
            text="Save Changes",
            command=save_settings,
            style='Settings.TButton'
        ).pack(fill='x')
        
    def apply_settings(self):
        self.root.attributes('-alpha', self.settings.get('opacity'))
        self.root.attributes('-topmost', self.settings.get('always_on_top'))
        self.update_theme()
        
    def update_theme(self):
        theme = self.settings.get('theme')
        if theme == 'light':
            # 浅色主题 - 更优雅的银灰色调
            bg_color = '#f5f5f7'  # 淡银灰色背景
            fg_color = '#1d1d1f'  # 深灰色文本
            accent_color = '#666666'  # 中灰色强调
            text_color = '#86868b'  # 浅灰色次要文本
            button_bg = '#e8e8ed'  # 按钮背景
            progress_bg = '#666666'  # 进度条
            progress_trough = '#e8e8ed'  # 进度条背景
        else:
            # 深色主题 - 优雅的深灰色调
            bg_color = '#2c2c2e'  # 深空灰背景
            fg_color = '#ffffff'  # 白色文本
            accent_color = '#666666'  # 中灰色强调
            text_color = '#98989d'  # 浅灰色次要文本
            button_bg = '#3a3a3c'  # 按钮背景
            progress_bg = '#666666'  # 进度条
            progress_trough = '#3a3a3c'  # 进度条背景
            
        self.root.configure(bg=bg_color)
        self.style.configure('Custom.TFrame', background=bg_color)
        self.style.configure('Timer.TLabel', background=bg_color, foreground=fg_color)
        self.style.configure('Status.TLabel', background=bg_color, foreground=text_color)
        self.style.configure('Icon.TButton', background=button_bg)
        self.style.configure('Custom.Horizontal.TProgressbar',
                           troughcolor=progress_trough,
                           background=progress_bg)
            
    def toggle_window(self):
        if self.window_visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
        self.window_visible = not self.window_visible
        
    def get_period_stats(self, start_date, end_date):
        total_seconds = 0
        try:
            with open('work_time.json', 'r') as f:
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
        
    def export_data(self):
        try:
            with open('work_time.json', 'r') as f:
                data = json.load(f)
            
            filename = f"work_time_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['日期', '工作时长（小时）'])
                for date, seconds in sorted(data.items()):
                    writer.writerow([date, round(seconds/3600, 2)])
            messagebox.showinfo("导出成功", f"数据已导出到：{filename}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            
    def backup_data(self):
        backup_dir = self.data_dir / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'work_time_{timestamp}.json'
        
        try:
            shutil.copy2('work_time.json', backup_file)
        except Exception as e:
            print(f"备份失败：{e}")
            
    def update_timer(self):
        # 检查是否需要重置（新的一天）
        current_date = datetime.now().date()
        if current_date != self.today:
            # 在天数变更时进行备份
            self.backup_data()
            
            # 保存昨天的最终数据
            self.save_data()
            
            # 重置为新的一天
            self.today = current_date
            self.accumulated_time = 0
            self.start_time = None
            self.is_running = False
            self.toggle_button.configure(text=self.icons['play'])
            self.status_label.configure(text="New Day")
            self.progress['value'] = 0
            if hasattr(self, 'target_completed'):
                delattr(self, 'target_completed')
            if hasattr(self, 'last_celebration_hour'):
                delattr(self, 'last_celebration_hour')
                
            # 保存新的一天的初始状态
            self.save_data()
            
        # 计算总时间
        total_seconds = self.accumulated_time
        if self.is_running and self.start_time:
            total_seconds += time.time() - self.start_time
            
        # 检查是否完成一小时
        hours_completed = int(total_seconds // 3600)
        if hasattr(self, 'last_celebration_hour') and hours_completed > self.last_celebration_hour:
            self.show_celebration(is_target_completed=False)
        self.last_celebration_hour = hours_completed
            
        # 检查目标完成情况
        try:
            target_hours = float(self.target_time_var.get())
            if target_hours > 0:  # 只在目标时间大于0时检查
                target_seconds = target_hours * 3600
                # 检查是否达到目标
                if total_seconds >= target_seconds and not hasattr(self, 'target_completed'):
                    self.target_completed = True
                    self.show_celebration(is_target_completed=True)
                    # 延长目标时间1小时
                    new_target = target_hours + 1.0
                    self.target_time_var.set(f'{new_target:.1f}')
                    self.update_progress()  # 立即更新进度条
        except ValueError:
            pass
            
        # 转换为时分秒
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        # 更新显示
        if self.settings.get('show_seconds'):
            time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_text = f"{hours:02d}:{minutes:02d}"
        self.time_label.configure(text=time_text)
        
        # 保存数据
        self.save_data()
        
        # 每秒更新一次
        self.root.after(1000, self.update_timer)
        
    def run(self):
        if self.settings.get('auto_start'):
            self.add_to_startup()
        self.root.mainloop()
        
    def quit_app(self):
        if self.is_running:
            self.toggle_timer()
        self.backup_data()
        self.tray_icon.stop()
        self.root.quit()

    def update_status(self):
        """更新状态显示"""
        if self.is_running:
            self.status_label.configure(text="Working...")  # 更改状态文本
        else:
            self.status_label.configure(text="Paused")

    def validate_target_time(self, event=None):
        """验证目标时间输入"""
        try:
            value = float(self.target_time_var.get())
            if value <= 0:
                raise ValueError
            if value > 12:  # 限制最大时间为12小时
                value = 12.0
            # 格式化为一位小数
            self.target_time_var.set(f'{value:.1f}')
            # 只在按下回车或失去焦点时更新进度条
            if event and (event.type == '9' or event.keysym == 'Return'):  # FocusOut or Return
                self.update_progress()
                self.root.focus()  # 移除文本框焦点
        except ValueError:
            self.target_time_var.set('1.0')
            if event and (event.type == '9' or event.keysym == 'Return'):
                self.update_progress()
                self.root.focus()  # 移除文本框焦点
        return True

    def update_progress(self):
        """更新进度条"""
        if hasattr(self, 'progress'):
            try:
                target_hours = float(self.target_time_var.get())
                if target_hours <= 0:
                    target_hours = 1.0
                    self.target_time_var.set('1.0')
                target_seconds = target_hours * 3600  # 转换小时为秒
                total_seconds = self.accumulated_time
                if self.is_running and self.start_time:
                    total_seconds += time.time() - self.start_time
                progress = min(100, (total_seconds / target_seconds) * 100)
                self.progress['value'] = progress
            except (ValueError, AttributeError):
                self.target_time_var.set('1.0')
                self.progress['value'] = 0

    def show_celebration(self, is_target_completed=False):
        """显示庆祝动画"""
        # 如果目标时间为0，不显示庆祝
        if is_target_completed and float(self.target_time_var.get()) <= 0:
            return
            
        celebration = tk.Toplevel(self.root)
        celebration.overrideredirect(True)
        celebration.attributes('-topmost', True)
        celebration.attributes('-alpha', 0.0)  # 初始透明
        celebration.configure(bg='#2c2c2e')
        
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
        
        if is_target_completed:
            # 目标完成庆祝
            emojis = "🎉 🌟 🎊 ⭐"
            congrats_label = ttk.Label(
                celebration,
                text=emojis,
                font=('Segoe UI Emoji', 36),
                background='#2c2c2e',
                foreground='#ffffff'
            )
            congrats_label.pack(pady=(10, 5))
            
            title_label = ttk.Label(
                celebration,
                text="Congratulations!",
                font=('Calibri', 32, 'bold'),
                background='#2c2c2e',
                foreground='#ffffff'
            )
            title_label.pack(pady=5)
            
            message_label = ttk.Label(
                celebration,
                text=f"You've completed your {self.target_time_var.get()}-hour goal!",
                font=('Calibri', 18),
                background='#2c2c2e',
                foreground='#ffffff',
                justify='center'
            )
            message_label.pack(pady=5)
            
            # 继续工作的提示
            continue_label = ttk.Label(
                celebration,
                text="Timer extended for another hour.\nKeep up the great work!",
                font=('Calibri', 14),
                background='#2c2c2e',
                foreground='#98989d',
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
                background='#2c2c2e',
                foreground='#ffffff'
            )
            congrats_label.pack(pady=(20, 10))
            
            message_label = ttk.Label(
                celebration,
                text=f"Great job!\n{hours_completed} {'hour' if hours_completed == 1 else 'hours'} completed!",
                font=('Calibri', 18, 'bold'),
                background='#2c2c2e',
                foreground='#ffffff',
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

if __name__ == "__main__":
    app = WorkTimer()
    app.run() 