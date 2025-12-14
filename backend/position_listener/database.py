"""
仓位监听数据库管理模块

提供独立的listen.db数据库操作功能。
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

from ..vlogger import get_logger


# 初始化日志记录器
logger = get_logger("position_listener_db")


class PositionListenerDatabase:
    """
    仓位监听数据库管理器
    
    使用独立的listen.db数据库存储仓位监听数据。
    """
    
    def __init__(self, db_path: str = "backend/position_listener/listen.db"):
        """
        初始化数据库管理器
        
        参数:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库表结构
        self._init_database()
        
        logger.info(
            "POSITION_LISTENER_DB.INIT",
            msg="仓位监听数据库初始化成功",
            extra={"db_path": self.db_path}
        )
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        使用示例:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
                conn.commit()
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(
                "POSITION_LISTENER_DB.ERROR",
                msg="数据库操作失败",
                error_code="E-PLDB-001",
                extra={"error": str(e)}
            )
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """
        初始化数据库表结构
        
        创建position_listen表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建仓位监听表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_listen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    marks TEXT,
                    buy_price REAL NOT NULL,
                    buy_side TEXT NOT NULL,
                    shares REAL,
                    current_price REAL,
                    market_closed INTEGER DEFAULT 0,
                    threshold_config TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_listen_market_id
                ON position_listen(market_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_listen_is_active
                ON position_listen(is_active)
            """)
            
            conn.commit()
            
            logger.info(
                "POSITION_LISTENER_DB.TABLE_CREATED",
                msg="数据库表创建成功"
            )
    
    def add_position(
        self,
        market_id: str,
        buy_price: float,
        buy_side: str,
        marks: Optional[str] = None,
        shares: Optional[float] = None,
        threshold_config: Optional[str] = None
    ) -> int:
        """
        添加仓位监听记录
        
        参数:
            market_id: 市场ID
            buy_price: 买入价格
            buy_side: 买入方向 (YES/NO)
            marks: 标记/备注信息
            shares: 持仓份额
            threshold_config: 阈值配置(JSON字符串)
        
        返回:
            int: 新增记录的ID
        """
        # 验证参数
        if buy_side not in ['YES', 'NO']:
            raise ValueError(f"buy_side必须是'YES'或'NO', 当前值: {buy_side}")
        
        if not (0.0 < buy_price < 1.0):
            raise ValueError(f"buy_price必须在0到1之间, 当前值: {buy_price}")
        
        if shares is not None and shares < 0:
            raise ValueError(f"shares必须大于等于0, 当前值: {shares}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO position_listen 
                (market_id, marks, buy_price, buy_side, shares, threshold_config, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (market_id, marks, buy_price, buy_side, shares, threshold_config))
            
            conn.commit()
            position_id = cursor.lastrowid
            
            logger.info(
                "POSITION_LISTENER_DB.ADD",
                msg=f"添加仓位监听记录: {position_id}",
                extra={
                    "position_id": position_id,
                    "market_id": market_id,
                    "buy_side": buy_side,
                    "buy_price": buy_price
                }
            )
            
            return position_id
    
    def get_positions(
        self,
        market_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        获取仓位监听列表
        
        参数:
            market_id: 市场ID (可选，用于筛选特定市场)
            is_active: 是否激活 (可选，True=仅激活, False=仅未激活, None=全部)
        
        返回:
            List[Dict]: 仓位记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询语句
            query = "SELECT * FROM position_listen WHERE 1=1"
            params = []
            
            if market_id is not None:
                query += " AND market_id = ?"
                params.append(market_id)
            
            if is_active is not None:
                query += " AND is_active = ?"
                params.append(1 if is_active else 0)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            # 转换为字典列表
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'market_id': row['market_id'],
                    'marks': row['marks'],
                    'buy_price': row['buy_price'],
                    'buy_side': row['buy_side'],
                    'shares': row['shares'],
                    'current_price': row['current_price'],
                    'market_closed': bool(row['market_closed']),
                    'threshold_config': row['threshold_config'],
                    'is_active': bool(row['is_active']),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return result
    
    def update_position(
        self,
        position_id: int,
        marks: Optional[str] = None,
        buy_price: Optional[float] = None,
        buy_side: Optional[str] = None,
        shares: Optional[float] = None,
        current_price: Optional[float] = None,
        market_closed: Optional[bool] = None,
        threshold_config: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """
        更新仓位监听记录
        
        参数:
            position_id: 仓位记录ID
            marks: 标记/备注信息 (可选)
            buy_price: 买入价格 (可选)
            buy_side: 买入方向 (可选)
            shares: 持仓份额 (可选)
            current_price: 当前价格 (可选)
            market_closed: 市场是否已结束 (可选)
            threshold_config: 阈值配置 (可选)
            is_active: 是否激活 (可选)
        
        返回:
            bool: 是否更新成功
        """
        # 构建更新语句
        updates = []
        params = []
        
        if marks is not None:
            updates.append("marks = ?")
            params.append(marks)
        
        if buy_price is not None:
            if not (0.0 < buy_price < 1.0):
                raise ValueError(f"buy_price必须在0到1之间, 当前值: {buy_price}")
            updates.append("buy_price = ?")
            params.append(buy_price)
        
        if buy_side is not None:
            if buy_side not in ['YES', 'NO']:
                raise ValueError(f"buy_side必须是'YES'或'NO', 当前值: {buy_side}")
            updates.append("buy_side = ?")
            params.append(buy_side)
        
        if shares is not None:
            if shares < 0:
                raise ValueError(f"shares必须大于等于0, 当前值: {shares}")
            updates.append("shares = ?")
            params.append(shares)
        
        if current_price is not None:
            updates.append("current_price = ?")
            params.append(current_price)
        
        if market_closed is not None:
            updates.append("market_closed = ?")
            params.append(1 if market_closed else 0)
        
        if threshold_config is not None:
            updates.append("threshold_config = ?")
            params.append(threshold_config)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return True  # 没有需要更新的字段
        
        # 添加updated_at字段
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"UPDATE position_listen SET {', '.join(updates)} WHERE id = ?"
            params.append(position_id)
            
            cursor.execute(query, tuple(params))
            conn.commit()
            
            logger.info(
                "POSITION_LISTENER_DB.UPDATE",
                msg=f"更新仓位记录: {position_id}",
                extra={"position_id": position_id}
            )
            
            return True
    
    def delete_position(self, position_id: int) -> bool:
        """
        删除仓位监听记录
        
        参数:
            position_id: 仓位记录ID
        
        返回:
            bool: 是否删除成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM position_listen WHERE id = ?", (position_id,))
            conn.commit()
            
            logger.info(
                "POSITION_LISTENER_DB.DELETE",
                msg=f"删除仓位记录: {position_id}",
                extra={"position_id": position_id}
            )
            
            return True
    
    def deactivate_position(self, position_id: int) -> bool:
        """
        停用仓位监听记录（软删除）
        
        参数:
            position_id: 仓位记录ID
        
        返回:
            bool: 是否停用成功
        """
        return self.update_position(position_id, is_active=False)
    
    def clear_all_positions(self) -> bool:
        """
        清空所有仓位监听记录
        
        返回:
            bool: 是否清空成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM position_listen")
            conn.commit()
            
            logger.info(
                "POSITION_LISTENER_DB.CLEAR",
                msg="清空所有仓位记录"
            )
            
            return True


# 全局数据库实例
_db_instance: Optional[PositionListenerDatabase] = None


def get_db(db_path: str = "backend/position_listener/listen.db") -> PositionListenerDatabase:
    """
    获取数据库实例（单例模式）
    
    参数:
        db_path: 数据库文件路径
    
    返回:
        PositionListenerDatabase: 数据库实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = PositionListenerDatabase(db_path)
    return _db_instance

