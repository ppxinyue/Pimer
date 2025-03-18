import os
import json
from datetime import datetime
from pathlib import Path
import threading
import time

# 尝试导入可选依赖
try:
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import pymongo.errors
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

class CloudSync:
    def __init__(self, username):
        """初始化云同步管理器"""
        self.username = username
        self.is_connected = False  # 默认设置为离线状态
        
        # 本地数据路径
        self.local_data_path = Path(f'data/users/{username}/work_time.json')
        
        # 如果MongoDB可用，尝试连接
        if MONGODB_AVAILABLE:
            try:
                # 加载环境变量
                load_dotenv()
                
                # MongoDB配置
                self.uri = os.getenv('MONGODB_URI')
                self.db_name = os.getenv('MONGODB_DB', 'work_timer')
                self.collection_name = os.getenv('MONGODB_COLLECTION', 'user_data')
                
                if self.uri:
                    self.client = MongoClient(self.uri)
                    self.db = self.client[self.db_name]
                    self.collection = self.db[self.collection_name]
                    # 测试连接
                    self.client.admin.command('ping')
                    print("MongoDB连接成功")
                    self.is_connected = True  # 连接成功，设置为在线状态
                else:
                    print("未设置MongoDB URI，使用本地同步模式")
            except Exception as e:
                print(f"MongoDB连接失败: {e}，使用本地同步模式")
                self.is_connected = False  # 确保连接失败时设置为离线状态
        else:
            print("未安装MongoDB依赖，使用本地同步模式")
        
        # 启动自动同步线程
        self.start_auto_sync()
    
    def start_auto_sync(self):
        """启动自动同步线程"""
        def auto_sync():
            while True:
                try:
                    # 每10分钟同步一次
                    time.sleep(600)
                    self.sync_data()
                except Exception as e:
                    print(f"自动同步出错: {e}")
        
        # 启动后台线程
        sync_thread = threading.Thread(target=auto_sync, daemon=True)
        sync_thread.start()
    
    def load_local_data(self):
        """加载本地数据"""
        try:
            if self.local_data_path.exists():
                with open(self.local_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载本地数据失败: {e}")
            return {}
    
    def save_local_data(self, data):
        """保存数据到本地"""
        try:
            self.local_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.local_data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存本地数据失败: {e}")
            return False
    
    def upload_data(self, data):
        """上传数据到云端"""
        if not self.is_connected:
            return False
            
        try:
            # 添加同步时间戳
            data['last_sync'] = datetime.now().isoformat()
            data['username'] = self.username
            
            # 更新云端数据
            self.collection.update_one(
                {'username': self.username},
                {'$set': data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"上传数据失败: {e}")
            self.is_connected = False  # 连接可能已断开
            return False
    
    def download_data(self):
        """从云端下载数据"""
        if not self.is_connected:
            return None
            
        try:
            data = self.collection.find_one({'username': self.username})
            if data:
                del data['_id']  # 删除MongoDB的_id字段
            return data
        except Exception as e:
            print(f"下载数据失败: {e}")
            self.is_connected = False  # 连接可能已断开
            return None
    
    def sync_data(self):
        """同步数据
        1. 获取本地数据
        2. 获取云端数据
        3. 合并数据（使用最新的数据）
        4. 保存到本地和云端
        """
        local_data = self.load_local_data()
        
        # 如果未连接，尝试重新连接
        if not self.is_connected and MONGODB_AVAILABLE:
            try:
                # 测试连接
                if hasattr(self, 'client'):
                    self.client.admin.command('ping')
                    self.is_connected = True
                    print("MongoDB重新连接成功")
            except Exception as e:
                print(f"MongoDB重新连接失败: {e}")
                self.is_connected = False
        
        # 如果仍未连接，只使用本地数据
        if not self.is_connected:
            return local_data
            
        # 尝试下载云端数据
        try:
            cloud_data = self.download_data()
            
            if not cloud_data:
                # 如果没有云端数据，上传本地数据
                if local_data:
                    self.upload_data(local_data)
                return local_data
                
            if not local_data:
                # 如果没有本地数据，使用云端数据
                self.save_local_data(cloud_data)
                return cloud_data
                
            # 比较时间戳，使用最新的数据
            local_time = datetime.fromisoformat(local_data.get('last_sync', '2000-01-01T00:00:00'))
            cloud_time = datetime.fromisoformat(cloud_data.get('last_sync', '2000-01-01T00:00:00'))
            
            if local_time > cloud_time:
                # 本地数据更新，上传到云端
                self.upload_data(local_data)
                return local_data
            else:
                # 云端数据更新，保存到本地
                self.save_local_data(cloud_data)
                return cloud_data
        except Exception as e:
            print(f"同步数据时出错: {e}")
            self.is_connected = False  # 出错时设置为离线状态
            return local_data
    
    def close(self):
        """关闭MongoDB连接"""
        if self.is_connected:
            try:
                self.client.close()
            except:
                pass 