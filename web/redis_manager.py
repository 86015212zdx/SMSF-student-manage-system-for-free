# -*- coding: utf-8 -*-
"""
Redis 会话管理器 - 实现用户登录状态保持功能
"""
import redis
import json
import uuid
from datetime import datetime, timedelta
import time
from typing import Optional, Dict, Any

class RedisSessionManager:
    """Redis 会话管理类"""
    
    def __init__(self):
        """初始化 Redis 连接"""
        # Redis 配置
        self.host = ''  # 你的 Redis 服务器 IP
        self.port = 6379              # Redis 端口
        self.password = '' # Redis 密码
        self.db = 0                   # 数据库编号
        self.prefix = 'smsf_session:' # 键前缀
        
        # 连接池配置（性能优化）
        self.connection_pool = None
        self.redis_client = None
        self._connection_status = None  # 缓存连接状态
        self._last_check_time = 0       # 上次检查时间
        self._check_interval = 30       # 检查间隔（秒）
        
        self._initialize_connection()
    
    def _initialize_connection(self):
        """初始化 Redis 连接池"""
        try:
            # 创建连接池（复用连接，提高性能）
            self.connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                max_connections=20,      # 最大连接数
                retry_on_timeout=True,   # 超时重试
                socket_connect_timeout=3, # 连接超时
                socket_timeout=3,        # 读写超时
                health_check_interval=30,
                decode_responses=True    # 自动解码
            )
            
            # 创建客户端
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # 快速测试连接
            self.redis_client.ping()
            self._connection_status = True
            self._last_check_time = time.time()
            print(f"✅ Redis 连接池初始化成功: {self.host}:{self.port}")
            
        except Exception as e:
            print(f"❌ Redis 连接池初始化失败: {e}")
            self.redis_client = None
            self._connection_status = False
    
    def is_connected(self) -> bool:
        """检查 Redis 是否连接成功（带缓存优化）"""
        current_time = time.time()
        
        # 如果距离上次检查时间较短，使用缓存结果
        if (current_time - self._last_check_time) < self._check_interval:
            return self._connection_status if self._connection_status is not None else False
        
        # 执行实际连接检查
        if not self.redis_client:
            self._connection_status = False
        else:
            try:
                # 使用较小的超时时间进行快速检查
                result = self.redis_client.ping()
                self._connection_status = bool(result)
            except Exception:
                self._connection_status = False
        
        self._last_check_time = current_time
        return self._connection_status
    
    def generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return str(uuid.uuid4())
    
    def create_session(self, user_account: str, expires_in_hours: int = 24) -> Optional[str]:
        """
        创建用户会话
        
        Args:
            user_account: 用户账号
            expires_in_hours: 会话过期时间（小时），默认24小时
            
        Returns:
            session_id: 会话ID，失败返回None
        """
        if not self.is_connected():
            return None
            
        try:
            # 生成会话ID
            session_id = self.generate_session_id()
            
            # 准备会话数据
            session_data = {
                'user_account': user_account,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=expires_in_hours)).isoformat(),
                'last_activity': datetime.now().isoformat(),
                'ip_address': None,  # 可以记录用户IP
                'user_agent': None   # 可以记录用户浏览器信息
            }
            
            # 存储到 Redis (使用 EXPIRE 设置过期时间)
            key = f"{self.prefix}{session_id}"
            self.redis_client.setex(
                key, 
                expires_in_hours * 3600,  # 转换为秒
                json.dumps(session_data, ensure_ascii=False)
            )
            
            # 同时存储用户的会话映射（用于单点登录控制）
            user_sessions_key = f"user_sessions:{user_account}"
            self.redis_client.sadd(user_sessions_key, session_id)
            self.redis_client.expire(user_sessions_key, expires_in_hours * 3600)
            
            print(f"✅ 用户 {user_account} 会话创建成功: {session_id}")
            return session_id
            
        except Exception as e:
            print(f"❌ 创建用户会话失败: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            session_data: 会话数据字典，不存在或过期返回None
        """
        if not self.is_connected():
            return None
            
        try:
            key = f"{self.prefix}{session_id}"
            session_json = self.redis_client.get(key)
            
            if session_json:
                session_data = json.loads(session_json)
                
                # 检查是否过期
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if datetime.now() > expires_at:
                    # 会话已过期，删除它
                    self.delete_session(session_id)
                    return None
                
                # 更新最后活动时间
                session_data['last_activity'] = datetime.now().isoformat()
                # 重新设置过期时间（延长会话有效期）
                remaining_time = int((expires_at - datetime.now()).total_seconds())
                if remaining_time > 0:
                    self.redis_client.setex(
                        key, 
                        remaining_time,
                        json.dumps(session_data, ensure_ascii=False)
                    )
                
                return session_data
            else:
                return None
                
        except Exception as e:
            print(f"❌ 获取会话失败: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 删除是否成功
        """
        if not self.is_connected():
            return False
            
        try:
            # 先获取会话信息以获取用户账号
            key = f"{self.prefix}{session_id}"
            session_json = self.redis_client.get(key)
            
            if session_json:
                session_data = json.loads(session_json)
                user_account = session_data.get('user_account')
                
                # 从用户的会话集合中移除
                if user_account:
                    user_sessions_key = f"user_sessions:{user_account}"
                    self.redis_client.srem(user_sessions_key, session_id)
                
                # 删除会话
                self.redis_client.delete(key)
                print(f"✅ 会话 {session_id} 已删除")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ 删除会话失败: {e}")
            return False
    
    def delete_user_all_sessions(self, user_account: str) -> int:
        """
        删除用户的所有会话（强制下线）
        
        Args:
            user_account: 用户账号
            
        Returns:
            int: 删除的会话数量
        """
        if not self.is_connected():
            return 0
            
        try:
            user_sessions_key = f"user_sessions:{user_account}"
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            deleted_count = 0
            for session_id in session_ids:
                if self.delete_session(session_id):
                    deleted_count += 1
            
            # 删除用户的会话集合
            self.redis_client.delete(user_sessions_key)
            
            print(f"✅ 用户 {user_account} 的 {deleted_count} 个会话已全部删除")
            return deleted_count
            
        except Exception as e:
            print(f"❌ 删除用户所有会话失败: {e}")
            return 0
    
    def extend_session(self, session_id: str, additional_hours: int = 24) -> bool:
        """
        延长会话有效期（优化版 - 减少不必要的操作）
        
        Args:
            session_id: 会话ID
            additional_hours: 额外延长的小时数
            
        Returns:
            bool: 延长是否成功
        """
        if not self.is_connected():
            return False
            
        try:
            key = f"{self.prefix}{session_id}"
            
            # 使用 pipeline 批量操作
            pipe = self.redis_client.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            results = pipe.execute()
            
            session_json = results[0]
            current_ttl = results[1]
            
            if session_json and current_ttl > 0:
                session_data = json.loads(session_json)
                
                # 只有当剩余时间小于12小时时才延长（避免频繁操作）
                if current_ttl < 12 * 3600:  # 12小时
                    # 更新过期时间
                    current_expires = datetime.fromisoformat(session_data['expires_at'])
                    new_expires = current_expires + timedelta(hours=additional_hours)
                    session_data['expires_at'] = new_expires.isoformat()
                    session_data['last_activity'] = datetime.now().isoformat()
                    
                    # 重新设置过期时间
                    pipe = self.redis_client.pipeline()
                    pipe.setex(
                        key,
                        int((new_expires - datetime.now()).total_seconds()),
                        json.dumps(session_data, ensure_ascii=False)
                    )
                    pipe.execute()
                    
                    print(f"✅ 会话 {session_id} 已延长 {additional_hours} 小时")
                else:
                    # 剩余时间充足，只需更新最后活动时间
                    session_data['last_activity'] = datetime.now().isoformat()
                    self.redis_client.setex(
                        key,
                        current_ttl,  # 保持原有过期时间
                        json.dumps(session_data, ensure_ascii=False)
                    )
                    print(f"✅ 会话 {session_id} 活动时间已更新")
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ 延长会话失败: {e}")
            return False
    
    def get_user_active_sessions(self, user_account: str) -> int:
        """
        获取用户当前活跃的会话数量
        
        Args:
            user_account: 用户账号
            
        Returns:
            int: 活跃会话数量
        """
        if not self.is_connected():
            return 0
            
        try:
            user_sessions_key = f"user_sessions:{user_account}"
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            active_count = 0
            for session_id in session_ids:
                if self.get_session(session_id):
                    active_count += 1
                    
            return active_count
            
        except Exception as e:
            print(f"❌ 获取活跃会话数量失败: {e}")
            return 0
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理所有过期的会话（定时任务使用）
        
        Returns:
            int: 清理的会话数量
        """
        if not self.is_connected():
            return 0
            
        try:
            # 获取所有会话键
            pattern = f"{self.prefix}*"
            session_keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            for key in session_keys:
                session_json = self.redis_client.get(key)
                if session_json:
                    try:
                        session_data = json.loads(session_json)
                        expires_at = datetime.fromisoformat(session_data['expires_at'])
                        if datetime.now() > expires_at:
                            # 会话已过期
                            session_id = key.replace(self.prefix, '')
                            self.delete_session(session_id)
                            cleaned_count += 1
                    except:
                        # 数据格式错误，删除无效键
                        self.redis_client.delete(key)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"✅ 已清理 {cleaned_count} 个过期会话")
            return cleaned_count
            
        except Exception as e:
            print(f"❌ 清理会话失败: {e}")
            return 0

# 全局 Redis 会话管理器实例
redis_session_manager = RedisSessionManager()

# 便捷函数
def create_user_session(user_account: str, expires_in_hours: int = 24) -> Optional[str]:
    """创建会话的便捷函数"""
    return redis_session_manager.create_session(user_account, expires_in_hours)

def get_user_session(session_id: str) -> Optional[Dict[str, Any]]:
    """获取会话的便捷函数"""
    return redis_session_manager.get_session(session_id)

def delete_user_session(session_id: str) -> bool:
    """删除会话的便捷函数"""
    return redis_session_manager.delete_session(session_id)

def force_logout_user(user_account: str) -> int:
    """强制用户下线的便捷函数"""
    return redis_session_manager.delete_user_all_sessions(user_account)

def extend_user_session(session_id: str, additional_hours: int = 24) -> bool:
    """延长时间的便捷函数"""
    return redis_session_manager.extend_session(session_id, additional_hours)