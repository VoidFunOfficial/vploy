"""
用户认证配置管理模块

提供用户认证相关的数据库操作，包括：
- 用户表管理
- 用户认证
- 会话管理
"""

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .config_manager import get_config_manager


class AuthConfig:
    """用户认证配置管理器"""
    
    def __init__(self, db_path: str = "backend/sys_configs/system_config.db"):
        """
        初始化认证配置管理器
        
        参数:
            db_path: 数据库文件路径
        """
        self.config_manager = get_config_manager(db_path)
        self._ensure_tables_exist()
        self._create_default_admin()
    
    def _ensure_tables_exist(self):
        """确保用户认证相关表存在"""
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_token 
                ON sessions(token)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON sessions(user_id)
            """)
            
            conn.commit()
            print("[AuthConfig] 用户认证表创建成功")
            
        except Exception as e:
            conn.rollback()
            print(f"[AuthConfig] 创建用户认证表失败: {str(e)}")
            raise
    
    def _create_default_admin(self):
        """创建默认管理员账户（如果不存在）"""
        try:
            # 检查是否已存在管理员账户
            if self.get_user_by_username("admin"):
                return
            
            # 创建默认管理员账户: admin / admin123
            self.create_user("admin", "admin123", role="admin")
            print("[AuthConfig] 默认管理员账户创建成功 (admin/admin123)")
            
        except Exception as e:
            print(f"[AuthConfig] 创建默认管理员账户失败: {str(e)}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        使用 SHA256 + salt 哈希密码
        
        参数:
            password: 明文密码
            salt: 盐值
            
        返回:
            str: 哈希后的密码
        """
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _generate_salt(self) -> str:
        """生成随机盐值"""
        return secrets.token_hex(16)
    
    def _generate_token(self) -> str:
        """生成会话令牌"""
        return secrets.token_urlsafe(32)
    
    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        """
        创建新用户
        
        参数:
            username: 用户名
            password: 密码
            role: 角色 (admin/user)
            
        返回:
            bool: 是否创建成功
        """
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, role)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, salt, role))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # 用户名已存在
            return False
        except Exception as e:
            conn.rollback()
            print(f"[AuthConfig] 创建用户失败: {str(e)}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        根据用户名获取用户信息
        
        参数:
            username: 用户名
            
        返回:
            Optional[Dict]: 用户信息字典，不存在则返回 None
        """
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, password_hash, salt, role, is_active, 
                   created_at, updated_at, last_login
            FROM users
            WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "salt": row[3],
            "role": row[4],
            "is_active": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "last_login": row[8]
        }
    
    def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户密码
        
        参数:
            username: 用户名
            password: 密码
            
        返回:
            Optional[Dict]: 验证成功返回用户信息，失败返回 None
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not user["is_active"]:
            return None
        
        password_hash = self._hash_password(password, user["salt"])
        if password_hash != user["password_hash"]:
            return None
        
        # 更新最后登录时间
        self._update_last_login(user["id"])
        
        return user
    
    def _update_last_login(self, user_id: int):
        """更新用户最后登录时间"""
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        
        conn.commit()
    
    def create_session(self, user_id: int, expires_hours: int = 24) -> str:
        """
        创建用户会话
        
        参数:
            user_id: 用户 ID
            expires_hours: 会话过期时间（小时）
            
        返回:
            str: 会话令牌
        """
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        token = self._generate_token()
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        cursor.execute("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at.isoformat()))
        
        conn.commit()
        return token
    
    def verify_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证会话令牌
        
        参数:
            token: 会话令牌
            
        返回:
            Optional[Dict]: 验证成功返回用户信息，失败返回 None
        """
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.user_id, s.expires_at, u.username, u.role, u.is_active
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        user_id, expires_at, username, role, is_active = row
        
        # 检查会话是否过期
        if datetime.fromisoformat(expires_at) < datetime.now():
            self.delete_session(token)
            return None
        
        # 检查用户是否激活
        if not is_active:
            return None
        
        return {
            "user_id": user_id,
            "username": username,
            "role": role
        }
    
    def delete_session(self, token: str) -> bool:
        """
        删除会话
        
        参数:
            token: 会话令牌
            
        返回:
            bool: 是否删除成功
        """
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    def cleanup_expired_sessions(self):
        """清理过期的会话"""
        conn = self.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM sessions
            WHERE expires_at < ?
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            print(f"[AuthConfig] 清理了 {deleted_count} 个过期会话")


# 全局认证配置实例
_auth_config = None


def get_auth_config(db_path: str = "backend/sys_configs/system_config.db") -> AuthConfig:
    """
    获取认证配置管理器实例（单例模式）
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        AuthConfig: 认证配置管理器实例
    """
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig(db_path)
    return _auth_config

