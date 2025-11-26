"""
序列号管理器

基于 SQLite 实现的线程安全序列号管理系统，为不同业务模块提供自增序列号服务。

特性:
- 线程安全的序列号获取（使用数据库事务保证原子性）
- 支持多种业务序列类型
- 单例模式管理数据库连接
- 集成 VLogger 日志系统
- 支持序列初始化、重置、查询等操作

使用示例:
    >>> from sequence_manager import get_sequence_manager
    >>> seq_mgr = get_sequence_manager()
    >>> seq_id = seq_mgr.get_next_sequence('filter_sequence')
    >>> print(f"获取到序列号: {seq_id}")
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# 导入 VLogger
try:
    from ..sys_configs.global_event_reg import vlogger
except ImportError:
    from backend.sys_configs.global_event_reg import vlogger


class SequenceManager:
    """
    序列号管理器
    
    提供线程安全的序列号管理功能，支持：
    - 原子性的序列号获取
    - 序列初始化和重置
    - 序列状态查询
    - 完整的日志记录
    """
    
    # 支持的序列类型
    SEQUENCE_TYPES = [
        'filter_sequence',      # 过滤系统序列号
        'analysis_sequence',    # 分析系统序列号
        'trade_sequence',       # 交易系统序列号
        'position_sequence',    # 持仓系统序列号
        'decision_sequence',    # 决策系统序列号
    ]
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "backend/sequence_manager/sequences.db"):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "backend/sequence_manager/sequences.db"):
        """
        初始化序列号管理器
        
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
        
        # 初始化数据库表
        self._init_tables()
        
        vlogger.info("SEQ.MANAGER.INIT", msg="序列号管理器初始化完成", extra={
            "db_path": db_path
        })
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取当前线程的数据库连接
        
        返回:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                isolation_level='IMMEDIATE'  # 使用 IMMEDIATE 事务级别确保并发安全
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
    
    def _init_tables(self):
        """
        初始化数据库表结构
        
        创建序列号管理表，包含以下字段：
        - sequence_name: 序列名称（主键）
        - current_value: 当前序列值
        - step: 步长（默认为1）
        - result: 完成结果/备注
        - created_at: 创建时间
        - updated_at: 最后更新时间
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建序列号管理表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sequences (
                    sequence_name TEXT PRIMARY KEY,
                    current_value INTEGER NOT NULL DEFAULT 0,
                    step INTEGER NOT NULL DEFAULT 1,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sequence_name 
                ON sequences(sequence_name)
            """)
            
            conn.commit()
            
            # 初始化默认序列
            self._init_default_sequences()
            
            vlogger.info("SEQ.DB.TABLES_CREATED", msg="序列号数据库表创建完成")
            
        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.DB.INIT_ERROR", msg="序列号数据库表创建失败", 
                         error_code="E-SEQ-001", extra={
                "error": str(e)
            })
            raise
    
    def _init_default_sequences(self):
        """
        初始化默认序列
        
        为所有预定义的序列类型创建初始记录（如果不存在）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for seq_name in self.SEQUENCE_TYPES:
                cursor.execute("""
                    INSERT OR IGNORE INTO sequences (sequence_name, current_value, step, result)
                    VALUES (?, 0, 1, '初始化')
                """, (seq_name,))
            
            conn.commit()
            
            vlogger.info("SEQ.DEFAULT.INIT", msg="默认序列初始化完成", extra={
                "sequences": self.SEQUENCE_TYPES
            })
            
        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.DEFAULT.INIT_ERROR", msg="默认序列初始化失败",
                         error_code="E-SEQ-002", extra={
                "error": str(e)
            })
            raise
    
    def get_next_sequence(self, sequence_name: str, result: Optional[str] = None) -> int:
        """
        获取下一个序列号（原子操作，线程安全）
        
        参数:
            sequence_name: 序列名称
            result: 完成结果/备注（可选）
            
        返回:
            int: 下一个序列号
            
        异常:
            ValueError: 如果序列名称不存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 开始事务
            conn.execute("BEGIN IMMEDIATE")
            
            # 查询当前序列值和步长
            cursor.execute("""
                SELECT current_value, step FROM sequences
                WHERE sequence_name = ?
            """, (sequence_name,))
            
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"序列 '{sequence_name}' 不存在")
            
            current_value = row['current_value']
            step = row['step']
            next_value = current_value + step
            
            # 更新序列值
            update_params = [next_value, datetime.now().isoformat(), sequence_name]
            if result:
                cursor.execute("""
                    UPDATE sequences
                    SET current_value = ?, updated_at = ?, result = ?
                    WHERE sequence_name = ?
                """, [next_value, datetime.now().isoformat(), result, sequence_name])
            else:
                cursor.execute("""
                    UPDATE sequences
                    SET current_value = ?, updated_at = ?
                    WHERE sequence_name = ?
                """, update_params)
            
            conn.commit()
            
            vlogger.debug("SEQ.GET_NEXT", msg="获取下一个序列号", extra={
                "sequence_name": sequence_name,
                "sequence_id": next_value,
                "result": result
            })
            
            return next_value
            
        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.GET_NEXT_ERROR", msg="获取序列号失败",
                         error_code="E-SEQ-003", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise
    
    def get_current_value(self, sequence_name: str) -> int:
        """
        查询当前序列值（不更新）
        
        参数:
            sequence_name: 序列名称
            
        返回:
            int: 当前序列值
            
        异常:
            ValueError: 如果序列名称不存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT current_value FROM sequences
                WHERE sequence_name = ?
            """, (sequence_name,))
            
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"序列 '{sequence_name}' 不存在")
            
            return row['current_value']
            
        except Exception as e:
            vlogger.error("SEQ.GET_CURRENT_ERROR", msg="查询序列值失败",
                         error_code="E-SEQ-004", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise
    
    def reset_sequence(self, sequence_name: str, value: int = 0, result: Optional[str] = None):
        """
        重置序列到指定值
        
        参数:
            sequence_name: 序列名称
            value: 重置后的值（默认为0）
            result: 重置原因/备注（可选）
            
        异常:
            ValueError: 如果序列名称不存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查序列是否存在
            cursor.execute("""
                SELECT 1 FROM sequences WHERE sequence_name = ?
            """, (sequence_name,))
            
            if cursor.fetchone() is None:
                raise ValueError(f"序列 '{sequence_name}' 不存在")
            
            # 重置序列值
            update_params = [value, datetime.now().isoformat(), sequence_name]
            if result:
                cursor.execute("""
                    UPDATE sequences
                    SET current_value = ?, updated_at = ?, result = ?
                    WHERE sequence_name = ?
                """, [value, datetime.now().isoformat(), result, sequence_name])
            else:
                cursor.execute("""
                    UPDATE sequences
                    SET current_value = ?, updated_at = ?
                    WHERE sequence_name = ?
                """, update_params)
            
            conn.commit()
            
            vlogger.info("SEQ.RESET", msg="序列重置成功", extra={
                "sequence_name": sequence_name,
                "reset_value": value,
                "result": result
            })
            
        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.RESET_ERROR", msg="序列重置失败",
                         error_code="E-SEQ-005", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise

    def init_sequence(self, sequence_name: str, initial_value: int = 0,
                     step: int = 1, result: Optional[str] = None):
        """
        初始化新序列（如果序列已存在则不做任何操作）

        参数:
            sequence_name: 序列名称
            initial_value: 初始值（默认为0）
            step: 步长（默认为1）
            result: 初始化备注（可选）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sequences (sequence_name, current_value, step, result)
                VALUES (?, ?, ?, ?)
            """, (sequence_name, initial_value, step, result or '初始化'))

            conn.commit()

            if cursor.rowcount > 0:
                vlogger.info("SEQ.INIT", msg="序列初始化成功", extra={
                    "sequence_name": sequence_name,
                    "initial_value": initial_value,
                    "step": step,
                    "result": result
                })
            else:
                vlogger.debug("SEQ.INIT.SKIP", msg="序列已存在，跳过初始化", extra={
                    "sequence_name": sequence_name
                })

        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.INIT_ERROR", msg="序列初始化失败",
                         error_code="E-SEQ-006", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise

    def get_sequence_info(self, sequence_name: str) -> Dict[str, Any]:
        """
        获取序列的完整信息

        参数:
            sequence_name: 序列名称

        返回:
            dict: 包含序列所有信息的字典

        异常:
            ValueError: 如果序列名称不存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT sequence_name, current_value, step, result, created_at, updated_at
                FROM sequences
                WHERE sequence_name = ?
            """, (sequence_name,))

            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"序列 '{sequence_name}' 不存在")

            return {
                'sequence_name': row['sequence_name'],
                'current_value': row['current_value'],
                'step': row['step'],
                'result': row['result'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

        except Exception as e:
            vlogger.error("SEQ.GET_INFO_ERROR", msg="获取序列信息失败",
                         error_code="E-SEQ-007", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise

    def list_all_sequences(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有序列及其信息

        返回:
            dict: 以序列名称为键的字典，值为序列信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT sequence_name, current_value, step, result, created_at, updated_at
                FROM sequences
                ORDER BY sequence_name
            """)

            sequences = {}
            for row in cursor.fetchall():
                sequences[row['sequence_name']] = {
                    'current_value': row['current_value'],
                    'step': row['step'],
                    'result': row['result'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }

            return sequences

        except Exception as e:
            vlogger.error("SEQ.LIST_ERROR", msg="列出序列失败",
                         error_code="E-SEQ-008", extra={
                "error": str(e)
            })
            raise

    def delete_sequence(self, sequence_name: str):
        """
        删除指定序列

        参数:
            sequence_name: 序列名称

        异常:
            ValueError: 如果序列名称不存在或为预定义序列
        """
        # 防止删除预定义序列
        if sequence_name in self.SEQUENCE_TYPES:
            raise ValueError(f"不能删除预定义序列 '{sequence_name}'")

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM sequences WHERE sequence_name = ?
            """, (sequence_name,))

            if cursor.rowcount == 0:
                raise ValueError(f"序列 '{sequence_name}' 不存在")

            conn.commit()

            vlogger.info("SEQ.DELETE", msg="序列删除成功", extra={
                "sequence_name": sequence_name
            })

        except Exception as e:
            conn.rollback()
            vlogger.error("SEQ.DELETE_ERROR", msg="序列删除失败",
                         error_code="E-SEQ-009", extra={
                "sequence_name": sequence_name,
                "error": str(e)
            })
            raise


# 全局序列管理器实例
_sequence_manager: Optional[SequenceManager] = None
_manager_lock = threading.Lock()


def get_sequence_manager(db_path: str = "backend/sequence_manager/sequences.db") -> SequenceManager:
    """
    获取序列管理器实例（单例模式）

    参数:
        db_path: 数据库文件路径

    返回:
        SequenceManager: 序列管理器实例
    """
    global _sequence_manager
    if _sequence_manager is None:
        with _manager_lock:
            if _sequence_manager is None:
                _sequence_manager = SequenceManager(db_path)
    return _sequence_manager

