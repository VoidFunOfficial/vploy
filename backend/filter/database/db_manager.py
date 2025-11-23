"""
数据库管理模块

提供 SQLite 数据库的初始化、连接管理和 CRUD 操作。
支持黑名单配置管理和已处理事件记录。
"""

import sqlite3
import threading
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

# 导入 VLogger 日志系统
from backend.sys_configs.global_event_reg import vlogger


class DatabaseManager:
    """
    数据库管理器
    
    提供线程安全的数据库连接管理和操作接口。
    使用单例模式确保全局只有一个数据库连接池。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "backend/filter/database/filter.db"):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "backend/filter/database/filter.db"):
        """
        初始化数据库管理器
        
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

        vlogger.info("FILTER.DB.INIT", msg="数据库管理器初始化完成", extra={
            "db_path": db_path
        })
    
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
            vlogger.error("FILTER.DB.QUERY_ERROR", msg="查询执行失败", error_code="E-FILTER-001", extra={
                "query": query,
                "error": str(e)
            })
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
            vlogger.error("FILTER.DB.UPDATE_ERROR", msg="更新执行失败", error_code="E-FILTER-002", extra={
                "query": query,
                "error": str(e)
            })
            raise
    
    def init_tables(self):
        """
        初始化数据库表结构
        
        创建以下表：
        1. processed_markets: 已处理事件表
        2. blacklist_config: 黑名单配置表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建已处理事件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_markets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL UNIQUE,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_id 
                ON processed_markets(market_id)
            """)
            
            # 创建黑名单配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blacklist_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(blacklist_type, value)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_blacklist_type 
                ON blacklist_config(blacklist_type, is_active)
            """)
            
            conn.commit()

            vlogger.info("FILTER.DB.TABLES_CREATED", msg="数据库表创建完成")

        except Exception as e:
            conn.rollback()
            vlogger.error("FILTER.DB.INIT_ERROR", msg="数据库表创建失败", error_code="E-FILTER-003", extra={
                "error": str(e)
            })
            raise
    
    def insert_default_blacklist(self):
        """
        插入默认黑名单配置

        默认配置：
        - Tag黑名单: china, sports, elections
        - 标题关键词黑名单: (空)
        - 描述关键词黑名单: (空)
        """
        default_blacklist = [
            # Tag 黑名单
            ('tag', 'china'),
            ('tag', 'sports'),
            ('tag', 'elections'),
            # 标题关键词黑名单（可根据需要添加）
            # ('title_keyword', 'example'),
            # 描述关键词黑名单（可根据需要添加）
            # ('description_keyword', 'example'),
        ]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for blacklist_type, value in default_blacklist:
                cursor.execute("""
                    INSERT OR IGNORE INTO blacklist_config (blacklist_type, value, is_active)
                    VALUES (?, ?, 1)
                """, (blacklist_type, value))
            
            conn.commit()

            vlogger.info("FILTER.DB.DEFAULT_BLACKLIST", msg="默认黑名单配置插入完成", extra={
                "count": len(default_blacklist)
            })

        except Exception as e:
            conn.rollback()
            vlogger.error("FILTER.DB.INSERT_ERROR", msg="默认黑名单插入失败", error_code="E-FILTER-004", extra={
                "error": str(e)
            })
            raise


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None
_manager_lock = threading.Lock()


def get_db_manager(db_path: str = "backend/filter/database/filter.db") -> DatabaseManager:
    """
    获取数据库管理器实例（单例模式）
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        DatabaseManager: 数据库管理器实例
    """
    global _db_manager
    if _db_manager is None:
        with _manager_lock:
            if _db_manager is None:
                _db_manager = DatabaseManager(db_path)
    return _db_manager


def init_database(db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    初始化数据库（创建表结构并插入默认配置）

    参数:
        db_path: 数据库文件路径

    返回:
        bool: 初始化是否成功
    """
    try:
        db_manager = get_db_manager(db_path)
        db_manager.init_tables()
        db_manager.insert_default_blacklist()
        return True
    except Exception:
        return False


# ==================== 黑名单管理函数 ====================

def get_blacklist(blacklist_type: Optional[str] = None, db_path: str = "backend/filter/database/filter.db") -> Dict[str, List[str]]:
    """
    获取黑名单配置（仅返回激活的配置）

    参数:
        blacklist_type: 黑名单类型（'category' / 'tag' / 'description_keyword'），None 表示获取所有类型
        db_path: 数据库文件路径

    返回:
        dict: 黑名单配置字典，格式为 {blacklist_type: [value1, value2, ...]}
    """
    db_manager = get_db_manager(db_path)

    if blacklist_type:
        query = """
            SELECT value FROM blacklist_config
            WHERE blacklist_type = ? AND is_active = 1
        """
        rows = db_manager.execute_query(query, (blacklist_type,))
        return {blacklist_type: [row['value'] for row in rows]}
    else:
        query = """
            SELECT blacklist_type, value FROM blacklist_config
            WHERE is_active = 1
            ORDER BY blacklist_type, value
        """
        rows = db_manager.execute_query(query)

        result: Dict[str, List[str]] = {}
        for row in rows:
            bl_type = row['blacklist_type']
            if bl_type not in result:
                result[bl_type] = []
            result[bl_type].append(row['value'])

        return result


def add_blacklist_item(blacklist_type: str, value: str, db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    添加黑名单配置项

    参数:
        blacklist_type: 黑名单类型
        value: 黑名单值
        db_path: 数据库文件路径

    返回:
        bool: 添加是否成功
    """
    db_manager = get_db_manager(db_path)

    try:
        query = """
            INSERT INTO blacklist_config (blacklist_type, value, is_active, created_at, updated_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        db_manager.execute_update(query, (blacklist_type, value))

        vlogger.info("FILTER.BLACKLIST.ADD", msg="添加黑名单配置项", extra={
            "blacklist_type": blacklist_type,
            "value": value
        })

        return True
    except sqlite3.IntegrityError:
        # 配置项已存在
        vlogger.warn("FILTER.BLACKLIST.DUPLICATE", msg="黑名单配置项已存在", extra={
            "blacklist_type": blacklist_type,
            "value": value
        })
        return False
    except Exception as e:
        vlogger.error("FILTER.BLACKLIST.ADD_ERROR", msg="添加黑名单配置项失败", error_code="E-FILTER-005", extra={
            "blacklist_type": blacklist_type,
            "value": value,
            "error": str(e)
        })
        return False


def remove_blacklist_item(blacklist_type: str, value: str, db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    删除黑名单配置项

    参数:
        blacklist_type: 黑名单类型
        value: 黑名单值
        db_path: 数据库文件路径

    返回:
        bool: 删除是否成功
    """
    db_manager = get_db_manager(db_path)

    try:
        query = """
            DELETE FROM blacklist_config
            WHERE blacklist_type = ? AND value = ?
        """
        rowcount = db_manager.execute_update(query, (blacklist_type, value))

        if rowcount > 0:
            vlogger.info("FILTER.BLACKLIST.REMOVE", msg="删除黑名单配置项", extra={
                "blacklist_type": blacklist_type,
                "value": value
            })
            return True
        else:
            vlogger.warn("FILTER.BLACKLIST.NOT_FOUND", msg="黑名单配置项不存在", extra={
                "blacklist_type": blacklist_type,
                "value": value
            })
            return False
    except Exception as e:
        vlogger.error("FILTER.BLACKLIST.REMOVE_ERROR", msg="删除黑名单配置项失败", error_code="E-FILTER-006", extra={
            "blacklist_type": blacklist_type,
            "value": value,
            "error": str(e)
        })
        return False


def update_blacklist_item(item_id: int, is_active: bool, db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    更新黑名单配置项的激活状态

    参数:
        item_id: 配置项 ID
        is_active: 是否激活
        db_path: 数据库文件路径

    返回:
        bool: 更新是否成功
    """
    db_manager = get_db_manager(db_path)

    try:
        query = """
            UPDATE blacklist_config
            SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        rowcount = db_manager.execute_update(query, (1 if is_active else 0, item_id))

        if rowcount > 0:
            vlogger.info("FILTER.BLACKLIST.UPDATE", msg="更新黑名单配置项", extra={
                "item_id": item_id,
                "is_active": is_active
            })
            return True
        else:
            vlogger.warn("FILTER.BLACKLIST.NOT_FOUND", msg="黑名单配置项不存在", extra={
                "item_id": item_id
            })
            return False
    except Exception as e:
        vlogger.error("FILTER.BLACKLIST.UPDATE_ERROR", msg="更新黑名单配置项失败", error_code="E-FILTER-007", extra={
            "item_id": item_id,
            "error": str(e)
        })
        return False


# ==================== 已处理事件管理函数 ====================

def is_market_processed(market_id: str, db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    检查市场是否已处理

    参数:
        market_id: 市场 ID
        db_path: 数据库文件路径

    返回:
        bool: 是否已处理
    """
    db_manager = get_db_manager(db_path)

    try:
        query = """
            SELECT COUNT(*) as count FROM processed_markets
            WHERE market_id = ?
        """
        rows = db_manager.execute_query(query, (market_id,))
        return rows[0]['count'] > 0
    except Exception as e:
        vlogger.error("FILTER.PROCESSED.CHECK_ERROR", msg="检查市场处理状态失败", error_code="E-FILTER-008", extra={
            "market_id": market_id,
            "error": str(e)
        })
        return False


def mark_market_as_processed(market_id: str, db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    标记市场为已处理

    参数:
        market_id: 市场 ID
        db_path: 数据库文件路径

    返回:
        bool: 标记是否成功
    """
    db_manager = get_db_manager(db_path)

    try:
        query = """
            INSERT OR IGNORE INTO processed_markets (market_id, processed_at, created_at)
            VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        db_manager.execute_update(query, (market_id,))

        vlogger.debug("FILTER.PROCESSED.MARK", msg="标记市场为已处理", extra={
            "market_id": market_id
        })

        return True
    except Exception as e:
        vlogger.error("FILTER.PROCESSED.MARK_ERROR", msg="标记市场失败", error_code="E-FILTER-009", extra={
            "market_id": market_id,
            "error": str(e)
        })
        return False


def clear_processed_markets(before_date: Optional[datetime] = None, db_path: str = "backend/filter/database/filter.db") -> int:
    """
    清理已处理市场记录

    参数:
        before_date: 清理此日期之前的记录，None 表示清理所有记录
        db_path: 数据库文件路径

    返回:
        int: 清理的记录数量
    """
    db_manager = get_db_manager(db_path)

    try:
        if before_date:
            query = """
                DELETE FROM processed_markets
                WHERE processed_at < ?
            """
            rowcount = db_manager.execute_update(query, (before_date.isoformat(),))
        else:
            query = "DELETE FROM processed_markets"
            rowcount = db_manager.execute_update(query)

        vlogger.info("FILTER.PROCESSED.CLEAR", msg="清理已处理市场记录", extra={
            "before_date": before_date.isoformat() if before_date else "all",
            "count": rowcount
        })

        return rowcount
    except Exception as e:
        vlogger.error("FILTER.PROCESSED.CLEAR_ERROR", msg="清理已处理市场记录失败", error_code="E-FILTER-010", extra={
            "error": str(e)
        })
        return 0

