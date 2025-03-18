import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import sys

def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LoginWindow:
    def __init__(self, parent, user_manager, on_login_success):
        self.window = tk.Toplevel(parent)
        self.window.title("Pimer - 登录")
        self.window.geometry("400x600")  # 增加窗口高度到600像素
        self.window.configure(bg='#2c2c2e')
        
        self.user_manager = user_manager
        self.on_login_success = on_login_success
        self.show_register = False  # 初始不显示注册表单
        
        # 使用resource_path获取图标文件的正确路径
        ico_path = resource_path('pig_nose_icon.ico')
        if os.path.exists(ico_path):
            self.window.iconbitmap(ico_path)
        else:
            print(f"图标文件不存在: {ico_path}")    


        # 设置窗口样式
        style = ttk.Style()
        style.configure('Login.TFrame',
            background='#2c2c2e'
        )
        style.configure('Login.TLabel',
            background='#2c2c2e',
            foreground='#ffffff',
            font=('Microsoft YaHei', 12),
            padding=5
        )
        style.configure('Login.TButton',
            font=('Microsoft YaHei', 11),
            padding=8
        )
        style.configure('Login.TCheckbutton',
            background='#2c2c2e',
            foreground='#ffffff',
            font=('Microsoft YaHei', 11)
        )
        
        # 设置复选框样式
        style.map('Login.TCheckbutton',
            background=[('active', '#3a3a3c')],
            indicatorcolor=[('selected', '#0a84ff'), ('!selected', '#3a3a3c')]
        )
        
        # 创建主容器
        self.main_frame = ttk.Frame(self.window, style='Login.TFrame')
        self.main_frame.pack(expand=True, fill='both', padx=30, pady=30)
        
        # 标题
        ttk.Label(
            self.main_frame,
            text="Pimer",
            style='Login.TLabel',
            font=('Microsoft YaHei', 24, 'bold')
        ).pack(pady=(0, 20))
        
        # 创建内容框架（用于切换登录和注册表单）
        self.content_frame = ttk.Frame(self.main_frame, style='Login.TFrame')
        self.content_frame.pack(fill='both', expand=True)
        
        # 创建登录表单
        self.create_login_form()
        
    def create_login_form(self):
        """创建登录表单"""
        # 清空内容框架
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        login_frame = ttk.Frame(self.content_frame, style='Login.TFrame')
        login_frame.pack(fill='x', pady=10)
        
        # 标题
        ttk.Label(
            login_frame,
            text="登录",
            style='Login.TLabel',
            font=('Microsoft YaHei', 16, 'bold')
        ).pack(anchor='w', pady=(0, 10))
        
        # 用户名
        ttk.Label(
            login_frame,
            text="用户名",
            style='Login.TLabel'
        ).pack(anchor='w')
        
        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(
            login_frame,
            textvariable=self.username_var,
            font=('Microsoft YaHei', 11),
            bg='#3a3a3c',
            fg='white',
            insertbackground='white',
            relief='flat',
            bd=1
        )
        self.username_entry.pack(fill='x', pady=(0, 15))
        
        # 密码
        ttk.Label(
            login_frame,
            text="密码",
            style='Login.TLabel'
        ).pack(anchor='w')
        
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            login_frame,
            textvariable=self.password_var,
            font=('Microsoft YaHei', 11),
            bg='#3a3a3c',
            fg='white',
            insertbackground='white',
            relief='flat',
            bd=1,
            show='*'
        )
        self.password_entry.pack(fill='x', pady=(0, 15))
        
        # 自动登录选项
        self.auto_login_var = tk.BooleanVar(value=False)
        auto_login_cb = ttk.Checkbutton(
            login_frame,
            text="自动登录",
            variable=self.auto_login_var,
            style='Login.TCheckbutton'
        )
        auto_login_cb.pack(anchor='w', pady=(0, 15))
        
        # 登录按钮
        ttk.Button(
            login_frame,
            text="登录",
            command=self.handle_login,
            style='Login.TButton'
        ).pack(fill='x', pady=(10, 20))
        
        # 注册链接
        register_frame = ttk.Frame(login_frame, style='Login.TFrame')
        register_frame.pack(fill='x')
        
        ttk.Label(
            register_frame,
            text="没有账号？",
            style='Login.TLabel',
            font=('Microsoft YaHei', 11)
        ).pack(side='left')
        
        register_link = ttk.Label(
            register_frame,
            text="注册新账号",
            style='Login.TLabel',
            font=('Microsoft YaHei', 11),
            foreground='#0a84ff'
        )
        register_link.pack(side='left', padx=(5, 0))
        register_link.bind("<Button-1>", lambda e: self.show_register_form())
        register_link.bind("<Enter>", lambda e: register_link.configure(foreground='#4da6ff', cursor="hand2"))
        register_link.bind("<Leave>", lambda e: register_link.configure(foreground='#0a84ff'))
        
        # 绑定回车键
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self.handle_login())
        
        # 设置焦点
        self.username_entry.focus_set()
        
    def show_register_form(self):
        """显示注册表单"""
        # 清空内容框架
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        register_frame = ttk.Frame(self.content_frame, style='Login.TFrame')
        register_frame.pack(fill='x', pady=10)
        
        # 添加返回按钮
        back_frame = ttk.Frame(register_frame, style='Login.TFrame')
        back_frame.pack(fill='x', pady=(0, 10))
        
        back_button = ttk.Label(
            back_frame,
            text="← 返回登录",
            style='Login.TLabel',
            font=('Microsoft YaHei', 11),
            foreground='#0a84ff'
        )
        back_button.pack(side='left')
        back_button.bind("<Button-1>", lambda e: self.create_login_form())
        back_button.bind("<Enter>", lambda e: back_button.configure(foreground='#4da6ff', cursor="hand2"))
        back_button.bind("<Leave>", lambda e: back_button.configure(foreground='#0a84ff'))
        
        # 标题
        ttk.Label(
            register_frame,
            text="注册新账号",
            style='Login.TLabel',
            font=('Microsoft YaHei', 16, 'bold')
        ).pack(anchor='w', pady=(10, 15))
        
        # 用户名
        ttk.Label(
            register_frame,
            text="用户名",
            style='Login.TLabel'
        ).pack(anchor='w')
        
        self.reg_username_var = tk.StringVar()
        self.reg_username_entry = tk.Entry(
            register_frame,
            textvariable=self.reg_username_var,
            font=('Microsoft YaHei', 11),
            bg='#3a3a3c',
            fg='white',
            insertbackground='white',
            relief='flat',
            bd=1
        )
        self.reg_username_entry.pack(fill='x', pady=(0, 15))
        
        # 密码
        ttk.Label(
            register_frame,
            text="密码",
            style='Login.TLabel'
        ).pack(anchor='w')
        
        self.reg_password_var = tk.StringVar()
        self.reg_password_entry = tk.Entry(
            register_frame,
            textvariable=self.reg_password_var,
            font=('Microsoft YaHei', 11),
            bg='#3a3a3c',
            fg='white',
            insertbackground='white',
            relief='flat',
            bd=1,
            show='*'
        )
        self.reg_password_entry.pack(fill='x', pady=(0, 15))
        
        # 确认密码
        ttk.Label(
            register_frame,
            text="确认密码",
            style='Login.TLabel'
        ).pack(anchor='w')
        
        self.reg_confirm_var = tk.StringVar()
        self.reg_confirm_entry = tk.Entry(
            register_frame,
            textvariable=self.reg_confirm_var,
            font=('Microsoft YaHei', 11),
            bg='#3a3a3c',
            fg='white',
            insertbackground='white',
            relief='flat',
            bd=1,
            show='*'
        )
        self.reg_confirm_entry.pack(fill='x', pady=(0, 15))
        
        # 注册按钮
        ttk.Button(
            register_frame,
            text="注册",
            command=self.handle_register,
            style='Login.TButton'
        ).pack(fill='x', pady=(15, 0))
        
        # 绑定回车键
        self.reg_username_entry.bind('<Return>', lambda e: self.reg_password_entry.focus())
        self.reg_password_entry.bind('<Return>', lambda e: self.reg_confirm_entry.focus())
        self.reg_confirm_entry.bind('<Return>', lambda e: self.handle_register())
        
        # 设置焦点
        self.reg_username_entry.focus_set()
        
    def handle_login(self):
        """处理登录"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        print(f"登录窗口 - 尝试登录用户: {username}")
        
        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return
        
        # 尝试在登录前同步用户数据
        if hasattr(self.user_manager, 'is_connected') and self.user_manager.is_connected:
            try:
                # 显示同步中提示
                self.window.config(cursor="wait")
                self.window.update()
                
                # 尝试直接从云端获取用户
                print(f"尝试直接从云端获取用户: {username}")
                cloud_user = self.user_manager.get_cloud_user(username)
                
                if cloud_user:
                    print(f"云端找到用户: {username}")
                    hashed_password = self.user_manager.hash_password(password)
                    cloud_password = cloud_user.get('password')
                    print(f"云端密码: {cloud_password[:10]}...")
                    print(f"输入密码哈希: {hashed_password[:10]}...")
                    
                    if cloud_user.get('password') == self.user_manager.hash_password(password):
                        print(f"云端密码验证成功: {username}")
                        # 如果云端验证成功，更新本地用户
                        login_time = datetime.now().isoformat()
                        cloud_user['last_login'] = login_time
                        
                        # 更新云端
                        try:
                            self.user_manager.users_collection.update_one(
                                {"username": username},
                                {"$set": {"last_login": login_time}}
                            )
                        except Exception as e:
                            print(f"更新云端用户登录时间失败: {e}")
                        
                        # 更新本地
                        self.user_manager.users[username] = cloud_user
                        self.user_manager.save_users()
                        
                        # 设置当前用户
                        self.user_manager.current_user = username
                        
                        # 设置自动登录
                        if self.auto_login_var.get():
                            self.user_manager.set_auto_login(True)
                        
                        # 恢复光标
                        self.window.config(cursor="")
                        
                        # 关闭窗口并回调
                        self.window.destroy()
                        self.on_login_success()
                        
                        # 显示云端登录状态提示
                        messagebox.showinfo("登录成功", "已通过云端验证登录，您的数据将自动同步")
                        return
                    else:
                        print(f"云端密码验证失败: {username}")
                else:
                    print(f"云端未找到用户: {username}")
                
                # 如果直接云端验证失败，尝试静默同步用户数据
                print("开始静默同步用户数据")
                self.user_manager.sync_users(force=True)
                
                # 恢复光标
                self.window.config(cursor="")
            except Exception as e:
                print(f"登录前同步用户数据失败: {e}")
                # 恢复光标
                self.window.config(cursor="")
            
        # 执行常规登录
        print("执行常规登录流程")
        success, message = self.user_manager.login(username, password)
        print(f"登录结果: {success}, {message}")
        
        if success:
            # 设置自动登录
            if self.auto_login_var.get():
                self.user_manager.set_auto_login(True)
            self.window.destroy()
            self.on_login_success()
            
            # 显示云端登录状态提示
            if "云端验证" in message or "同步后验证" in message:
                messagebox.showinfo("登录成功", "已通过云端验证登录，您的数据将自动同步")
        else:
            # 根据错误信息显示不同的提示
            if "密码错误" in message:
                messagebox.showerror("登录失败", "密码错误")
            elif "用户不存在" in message:
                messagebox.showerror("登录失败", "用户不存在")
            else:
                messagebox.showerror("登录失败", message)
            
    def handle_register(self):
        """处理注册"""
        username = self.reg_username_var.get().strip()
        password = self.reg_password_var.get()
        confirm = self.reg_confirm_var.get()
        
        if not username or not password or not confirm:
            messagebox.showerror("错误", "请填写所有字段")
            return
            
        if password != confirm:
            messagebox.showerror("错误", "两次输入的密码不一致")
            return
            
        success, message = self.user_manager.register(username, password)
        if success:
            # 检查是否连接到云端
            cloud_connected = hasattr(self.user_manager, 'is_connected') and self.user_manager.is_connected
            
            # 显示成功消息，包含云端状态
            if cloud_connected:
                messagebox.showinfo("成功", f"{message}（已同步到云端）")
            else:
                messagebox.showinfo("成功", f"{message}（本地注册）")
                
            # 返回登录界面并填入注册的用户名
            self.create_login_form()
            self.username_var.set(username)
            self.password_entry.focus_set()
        else:
            messagebox.showerror("注册失败", message) 