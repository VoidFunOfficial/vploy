"""
统一配置管理器

提供 SQLite 数据库的初始化、连接管理和配置 CRUD 操作。
支持多模块配置的统一管理。
"""

import sqlite3
import threading
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime


class ConfigManager:
    """
    配置管理器
    
    提供线程安全的配置数据库连接管理和操作接口。
    使用单例模式确保全局只有一个数据库连接池。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "backend/sys_configs/system_config.db"):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "backend/sys_configs/system_config.db"):
        """
        初始化配置管理器
        
        参数:
            db_path: 数据库文件路径
        """
        if self._initialized:
            return
        
        self.db_path = db_path
        self._local = threading.local()
        
        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取当前线程的数据库连接
        
        返回:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        执行查询语句
        
        参数:
            query: SQL 查询语句
            params: 查询参数
            
        返回:
            List[sqlite3.Row]: 查询结果列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            print(f"[ConfigManager] 查询执行失败: {str(e)}")
            raise
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        参数:
            query: SQL 更新语句
            params: 更新参数
            
        返回:
            int: 受影响的行数
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            print(f"[ConfigManager] 更新执行失败: {str(e)}")
            raise
    
    def init_tables(self):
        """
        初始化数据库表结构

        创建以下表：
        1. vlogger_config: VLogger 日志配置表
        2. email_config: 邮件配置表
        3. filter_blacklist: Filter 黑名单配置表
        4. processed_markets: 已处理事件表
        5. config_metadata: 配置元数据表
        6. position_listen_list: 持仓监听列表表
        7. sys_settings: 系统设置表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 1. VLogger 日志配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vlogger_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value TEXT NOT NULL,
                    config_type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 邮件配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value TEXT NOT NULL,
                    config_type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Filter 黑名单配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS filter_blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blacklist_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(blacklist_type, value)
                )
            """)

            # 4. 已处理事件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_markets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL UNIQUE,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. 配置元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL UNIQUE,
                    version TEXT DEFAULT '1.0.0',
                    last_migration TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. 持仓监听列表表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_listen_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    marks TEXT,
                    buy_price REAL NOT NULL,
                    buy_side TEXT NOT NULL,
                    shares REAL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. 系统设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sys_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vlogger_config_key
                ON vlogger_config(config_key)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_config_key
                ON email_config(config_key)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_filter_blacklist_type
                ON filter_blacklist(blacklist_type, is_active)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_markets_id
                ON processed_markets(market_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_listen_market_id
                ON position_listen_list(market_id, is_active)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sys_settings_key
                ON sys_settings(key)
            """)

            conn.commit()
            print("[ConfigManager] 数据库表创建完成")
                
        except Exception as e:
            conn.rollback()
            print(f"[ConfigManager] 数据库表创建失败: {str(e)}")
            raise
    
    def insert_default_configs(self):
        """插入默认配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 插入默认 VLogger 配置
            default_vlogger_configs = [
                ('service_name', 'core', 'string', '服务名称'),
                ('log_dir', './logs', 'string', '日志文件目录'),
                ('log_file_prefix', 'vlogger', 'string', '日志文件前缀'),
                ('rotation', '500 MB', 'string', '日志轮转策略'),
                ('retention', '30 days', 'string', '日志保留策略'),
                ('compression', 'zip', 'string', '压缩格式'),
                ('enable_console', 'true', 'boolean', '是否输出到控制台'),
                ('enable_file', 'true', 'boolean', '是否输出到文件'),
                ('enable_json', 'true', 'boolean', '是否使用 JSON 格式'),
                ('min_level', 'INFO', 'string', '最小日志等级'),
                ('sample_rates', '{}', 'json', '各等级的采样率配置'),
                ('enable_sanitization', 'true', 'boolean', '是否启用敏感信息脱敏'),
                ('enable_alerts', 'true', 'boolean', '是否启用告警'),
                ('extra_fields', '{}', 'json', '额外的全局字段'),
            ]
            
            for key, value, config_type, description in default_vlogger_configs:
                cursor.execute("""
                    INSERT OR IGNORE INTO vlogger_config (config_key, config_value, config_type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, value, config_type, description))
            
            # 插入默认邮件配置
            default_email_configs = [
                ('smtp_server', 'smtp.163.com', 'string', 'SMTP 服务器地址'),
                ('smtp_port', '465', 'integer', 'SMTP 端口'),
                ('username', 'imzfat@163.com', 'string', '发件人邮箱'),
                ('password', 'VUnyu33GQ3guVmct', 'string', '邮箱密码或授权码'),
                ('from_name', 'VLogger 告警系统', 'string', '发件人名称'),
                ('to_emails', '["imzfat@163.com"]', 'json', '收件人邮箱列表'),
                ('use_ssl', 'true', 'boolean', '是否使用 SSL'),
            ]
            
            for key, value, config_type, description in default_email_configs:
                cursor.execute("""
                    INSERT OR IGNORE INTO email_config (config_key, config_value, config_type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, value, config_type, description))
            
            # 插入默认黑名单配置
            default_blacklist = [
                ('tag', 'china'),
                ('tag', 'sports'),
                ('tag', 'elections'),
            ]
            
            for blacklist_type, value in default_blacklist:
                cursor.execute("""
                    INSERT OR IGNORE INTO filter_blacklist (blacklist_type, value, is_active)
                    VALUES (?, ?, 1)
                """, (blacklist_type, value))
            
            conn.commit()
            print("[ConfigManager] 默认配置插入完成")
                
        except Exception as e:
            conn.rollback()
            print(f"[ConfigManager] 默认配置插入失败: {str(e)}")
            raise


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None
_manager_lock = threading.Lock()


def get_config_manager(db_path: str = "backend/sys_configs/system_config.db") -> ConfigManager:
    """
    获取配置管理器实例（单例模式）
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        with _manager_lock:
            if _config_manager is None:
                _config_manager = ConfigManager(db_path)
    return _config_manager


def init_config_database(db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    初始化配置数据库（创建表结构并插入默认配置）

    参数:
        db_path: 数据库文件路径

    返回:
        bool: 初始化是否成功
    """
    try:
        config_manager = get_config_manager(db_path)
        config_manager.init_tables()
        config_manager.insert_default_configs()
        return True
    except Exception:
        return False

