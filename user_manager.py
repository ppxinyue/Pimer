import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
import threading
import time

# 尝试导入可选依赖
try:
    from dotenv import load_dotenv
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    import pymongo.errors
    MONGODB_AVAILABLE = True
    
    # 自定义JSON编码器，处理MongoDB的ObjectId
    class MongoJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            return super().default(obj)
except ImportError:
    MONGODB_AVAILABLE = False

class UserManager:
    def __init__(self):
        self.users_file = Path('data/users.json')
        self.auto_login_file = Path('data/auto_login.json')
        self.users_file.parent.mkdir(exist_ok=True)
        self.current_user = None
        self.is_connected = False  # 云连接状态
        
        # 初始化MongoDB连接
        self.init_cloud_connection()
        
        # 加载本地用户数据
        self.load_users()
        
        # 检查自动登录
        self.check_auto_login()
        
        # 启动自动同步线程
        self.start_auto_sync()
        
    def init_cloud_connection(self):
        """初始化云连接"""
        print("初始化MongoDB连接")
        self.is_connected = False
        
        if not MONGODB_AVAILABLE:
            print("MongoDB依赖不可用")
            return
            
        try:
            # 加载环境变量
            load_dotenv()
            
            # MongoDB配置
            self.uri = os.getenv('MONGODB_URI')
            self.db_name = os.getenv('MONGODB_DB', 'work_timer')
            self.users_collection_name = 'users'  # 用户集合名称
            
            if not self.uri:
                print("未设置MongoDB URI，使用本地用户管理")
                return
                
            print(f"尝试连接MongoDB: {self.uri[:20]}...")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.users_collection = self.db[self.users_collection_name]
            
            # 测试连接
            print("测试MongoDB连接...")
            self.client.admin.command('ping')
            print("MongoDB用户管理连接成功")
            self.is_connected = True
            
            # 确保用户集合有索引
            self.users_collection.create_index("username", unique=True)
        except Exception as e:
            print(f"MongoDB用户管理连接失败: {str(e)}，使用本地用户管理")
            self.is_connected = False
    
    def start_auto_sync(self):
        """启动自动同步线程"""
        def auto_sync():
            while True:
                try:
                    # 每30分钟同步一次用户数据
                    time.sleep(1800)
                    self.sync_users()
                except Exception as e:
                    print(f"自动同步用户数据出错: {e}")
        
        # 启动后台线程
        sync_thread = threading.Thread(target=auto_sync, daemon=True)
        sync_thread.start()
        
    def load_users(self):
        """加载用户数据"""
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.users = {}
            self.save_users()
            
    def save_users(self):
        """保存用户数据"""
        # 使用自定义编码器处理MongoDB的ObjectId
        if MONGODB_AVAILABLE:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=4, cls=MongoJSONEncoder)
        else:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=4)
            
    def hash_password(self, password):
        """密码加密"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def sync_users(self, force=False, progress_callback=None):
        """同步用户数据到云端
        
        Args:
            force: 是否强制同步所有用户数据，忽略时间戳比较
            progress_callback: 进度回调函数，接收一个0-100的整数表示进度
        """
        if not self.is_connected:
            if progress_callback:
                progress_callback(0)
            return
            
        try:
            if progress_callback:
                progress_callback(10)
                
            # 上传本地用户到云端
            local_users = list(self.users.items())
            total_users = len(local_users)
            
            for i, (username, user_data) in enumerate(local_users):
                # 创建用户数据的副本，避免修改原始数据
                user_data_copy = user_data.copy()
                
                # 检查云端是否已存在该用户
                cloud_user = self.users_collection.find_one({"username": username})
                
                if not cloud_user:
                    # 如果云端不存在，则上传
                    user_data_copy['username'] = username
                    user_data_copy['last_sync'] = datetime.now().isoformat()
                    self.users_collection.insert_one(user_data_copy)
                else:
                    # 如果云端存在，比较时间戳或强制更新
                    if force:
                        should_update = True
                    else:
                        local_time = datetime.fromisoformat(user_data.get('last_login', '2000-01-01T00:00:00'))
                        cloud_time = datetime.fromisoformat(cloud_user.get('last_login', '2000-01-01T00:00:00'))
                        should_update = local_time > cloud_time
                        
                    if should_update:
                        # 本地数据更新，更新云端
                        user_data_copy['last_sync'] = datetime.now().isoformat()
                        # 删除可能存在的_id字段，避免更新时出错
                        if '_id' in user_data_copy:
                            del user_data_copy['_id']
                        self.users_collection.update_one(
                            {"username": username},
                            {"$set": user_data_copy}
                        )
                
                # 更新进度
                if progress_callback and total_users > 0:
                    progress = 10 + int(40 * (i + 1) / total_users)
                    progress_callback(progress)
            
            if progress_callback:
                progress_callback(50)
                
            # 下载云端用户到本地
            cloud_users = list(self.users_collection.find({}))
            total_cloud_users = len(cloud_users)
            
            for i, cloud_user in enumerate(cloud_users):
                username = cloud_user.get('username')
                if username:
                    # 创建云端用户数据的副本
                    cloud_user_copy = dict(cloud_user)
                    
                    # 删除MongoDB的_id字段
                    if '_id' in cloud_user_copy:
                        del cloud_user_copy['_id']
                    
                    if username not in self.users:
                        # 如果本地不存在，则添加
                        self.users[username] = cloud_user_copy
                    else:
                        # 如果本地存在，比较时间戳或强制更新
                        if force:
                            should_update = True
                        else:
                            local_time = datetime.fromisoformat(self.users[username].get('last_login', '2000-01-01T00:00:00'))
                            cloud_time = datetime.fromisoformat(cloud_user.get('last_login', '2000-01-01T00:00:00'))
                            should_update = cloud_time > local_time
                            
                        if should_update:
                            # 云端数据更新，更新本地
                            self.users[username] = cloud_user_copy
                
                # 更新进度
                if progress_callback and total_cloud_users > 0:
                    progress = 50 + int(40 * (i + 1) / total_cloud_users)
                    progress_callback(progress)
            
            # 保存本地用户数据
            self.save_users()
            
            if progress_callback:
                progress_callback(100)
                
            print("用户数据同步完成")
        except Exception as e:
            print(f"同步用户数据失败: {e}")
            self.is_connected = False
            
            if progress_callback:
                progress_callback(-1)  # 表示同步失败
            
    def register(self, username, password):
        """注册新用户"""
        # 先检查本地是否存在
        if username in self.users:
            return False, "用户名已存在"
        
        # 如果连接到云端，检查云端是否存在
        if self.is_connected:
            try:
                cloud_user = self.users_collection.find_one({"username": username})
                if cloud_user:
                    # 如果云端存在，同步到本地
                    cloud_user_copy = dict(cloud_user)
                    if '_id' in cloud_user_copy:
                        del cloud_user_copy['_id']
                    self.users[username] = cloud_user_copy
                    self.save_users()
                    return False, "用户名已存在（云端）"
            except Exception as e:
                print(f"检查云端用户失败: {e}")
                self.is_connected = False
        
        # 创建新用户
        user_data = {
            'username': username,
            'password': self.hash_password(password),
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # 保存到本地
        self.users[username] = user_data
        self.save_users()
        
        # 如果连接到云端，保存到云端
        if self.is_connected:
            try:
                user_data_copy = user_data.copy()
                user_data_copy['last_sync'] = datetime.now().isoformat()
                self.users_collection.insert_one(user_data_copy)
            except Exception as e:
                print(f"保存用户到云端失败: {e}")
                self.is_connected = False
        
        return True, "注册成功"
        
    def login(self, username, password):
        """用户登录"""
        print(f"尝试登录用户: {username}")
        print(f"本地用户列表: {list(self.users.keys())}")
        
        # 如果连接到云端，优先从云端验证
        if self.is_connected:
            try:
                # 尝试重新连接
                if not self.is_connected:
                    self.init_cloud_connection()
                
                if self.is_connected:
                    print(f"尝试从云端验证用户: {username}")
                    # 从云端获取用户
                    cloud_user = self.users_collection.find_one({"username": username})
                    if cloud_user:
                        print(f"云端找到用户: {username}")
                        # 验证密码
                        if cloud_user.get('password') == self.hash_password(password):
                            print(f"云端密码验证成功: {username}")
                            # 登录成功，更新本地用户
                            cloud_user_copy = dict(cloud_user)
                            if '_id' in cloud_user_copy:
                                del cloud_user_copy['_id']
                            
                            # 更新登录时间
                            login_time = datetime.now().isoformat()
                            cloud_user_copy['last_login'] = login_time
                            
                            # 更新云端
                            self.users_collection.update_one(
                                {"username": username},
                                {"$set": {"last_login": login_time}}
                            )
                            
                            # 更新本地
                            self.users[username] = cloud_user_copy
                            self.save_users()
                            
                            # 设置当前用户
                            self.current_user = username
                            return True, "登录成功（云端验证）"
                        else:
                            print(f"云端密码验证失败: {username}")
                            return False, "密码错误（云端验证）"
                    else:
                        print(f"云端未找到用户: {username}")
            except Exception as e:
                print(f"云端登录验证失败: {e}")
                self.is_connected = False
                # 失败后尝试本地验证
        
        # 本地验证
        if username not in self.users:
            print(f"本地未找到用户: {username}")
            # 如果本地不存在，但之前尝试云端验证失败，再次尝试同步用户
            if self.is_connected:
                try:
                    print(f"尝试同步用户数据后再次验证: {username}")
                    # 尝试从云端获取用户
                    self.sync_users()
                    print(f"同步后本地用户列表: {list(self.users.keys())}")
                    # 再次检查本地是否有该用户
                    if username in self.users:
                        print(f"同步后找到用户: {username}")
                        # 如果同步后找到了用户，继续验证
                        if self.users[username]['password'] == self.hash_password(password):
                            print(f"同步后密码验证成功: {username}")
                            self.current_user = username
                            self.users[username]['last_login'] = datetime.now().isoformat()
                            self.save_users()
                            return True, "登录成功（同步后验证）"
                        else:
                            print(f"同步后密码验证失败: {username}")
                            return False, "密码错误"
                except Exception as e:
                    print(f"同步用户数据失败: {e}")
            
            return False, "用户不存在"
            
        # 检查用户数据结构是否包含password字段
        if 'password' not in self.users[username]:
            # 旧数据结构，更新为新结构
            self.users[username]['password'] = self.hash_password(password)
            self.save_users()
            self.current_user = username
            self.users[username]['last_login'] = datetime.now().isoformat()
            self.save_users()
            return True, "登录成功"
            
        if self.users[username]['password'] != self.hash_password(password):
            print(f"本地密码验证失败: {username}")
            return False, "密码错误"
            
        print(f"本地密码验证成功: {username}")
        self.current_user = username
        self.users[username]['last_login'] = datetime.now().isoformat()
        self.save_users()
        return True, "登录成功"
        
    def set_auto_login(self, enable=True):
        """设置自动登录"""
        if not self.is_logged_in():
            return False
            
        try:
            auto_login_data = {}
            if enable:
                auto_login_data = {
                    'username': self.current_user,
                    'enabled': True
                }
                
            with open(self.auto_login_file, 'w') as f:
                json.dump(auto_login_data, f, indent=4)
            return True
        except Exception as e:
            print(f"设置自动登录失败: {e}")
            return False
            
    def check_auto_login(self):
        """检查是否有自动登录设置"""
        try:
            if self.auto_login_file.exists():
                with open(self.auto_login_file, 'r') as f:
                    auto_login = json.load(f)
                    
                if auto_login.get('enabled') and auto_login.get('username') in self.users:
                    self.current_user = auto_login.get('username')
                    self.users[self.current_user]['last_login'] = datetime.now().isoformat()
                    self.save_users()
                    return True
        except Exception as e:
            print(f"检查自动登录失败: {e}")
        return False
        
    def get_user_data_file(self, username):
        """获取用户数据文件路径"""
        return Path(f'data/users/{username}/work_time.json')
        
    def ensure_user_data_dir(self, username):
        """确保用户数据目录存在"""
        user_dir = Path(f'data/users/{username}')
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
        
    def is_logged_in(self):
        """检查是否已登录"""
        return self.current_user is not None
        
    def get_current_user(self):
        """获取当前登录用户"""
        return self.current_user
        
    def logout(self):
        """登出当前用户"""
        self.current_user = None
        # 清除自动登录
        self.set_auto_login(False)
        
    def close(self):
        """关闭MongoDB连接"""
        if hasattr(self, 'client') and self.is_connected:
            try:
                self.client.close()
            except:
                pass

    def get_cloud_user(self, username):
        """从云端获取指定用户名的用户数据
        
        Args:
            username: 要获取的用户名
            
        Returns:
            dict: 用户数据，如果不存在或出错则返回None
        """
        print(f"尝试从云端获取用户: {username}")
        
        # 检查MongoDB是否可用
        if not MONGODB_AVAILABLE:
            print("MongoDB依赖不可用")
            return None
            
        # 检查连接状态
        if not hasattr(self, 'is_connected') or not self.is_connected:
            print("MongoDB未连接")
            # 尝试初始化连接
            self.init_cloud_connection()
            
        if not hasattr(self, 'is_connected') or not self.is_connected:
            print("MongoDB连接失败")
            return None
            
        try:
            # 确保有users_collection属性
            if not hasattr(self, 'users_collection'):
                print("MongoDB集合未初始化")
                return None
                
            # 从云端获取用户
            print(f"执行MongoDB查询: {username}")
            cloud_user = self.users_collection.find_one({"username": username})
            
            if cloud_user:
                print(f"MongoDB查询成功，找到用户: {username}")
                # 创建云端用户数据的副本
                cloud_user_copy = dict(cloud_user)
                
                # 删除MongoDB的_id字段
                if '_id' in cloud_user_copy:
                    del cloud_user_copy['_id']
                    
                return cloud_user_copy
            else:
                print(f"MongoDB查询成功，但未找到用户: {username}")
                return None
        except Exception as e:
            print(f"从云端获取用户数据失败: {str(e)}")
            self.is_connected = False
            return None 