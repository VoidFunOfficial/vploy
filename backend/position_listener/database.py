# -*- coding: utf-8 -*-
"""
Position Listener 数据库管理模块

提供持仓、交易记录、订单状态的数据库操作功能。
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .models import Position, Trade, Order, PositionStatus, OrderStatus
from ..sys_configs.global_event_reg import vlogger


class PositionDatabase:
    """
    持仓数据库管理器
    
    提供持仓、交易记录、订单状态的CRUD操作和数据库初始化功能。
    """
    
    def __init__(self, db_path: str = "./backend/position_listener/positions.db"):
        """
        初始化数据库管理器
        
        参数:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保数据库目录存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        
        vlogger.info(
            "POSITION.DB.INIT",
            msg="持仓数据库初始化完成",
            extra={"db_path": db_path}
        )
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建持仓表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    shares REAL NOT NULL,
                    invest_amount REAL NOT NULL,
                    settle_day INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    current_price REAL,
                    pnl REAL,
                    is_settled INTEGER DEFAULT 0,
                    settlement_result TEXT,
                    settlement_payout REAL,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    close_time TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # 创建交易记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id INTEGER,
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    shares REAL NOT NULL,
                    amount REAL NOT NULL,
                    trade_type TEXT NOT NULL,
                    order_id TEXT,
                    trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions (id)
                )
            """)
            
            # 创建订单状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL UNIQUE,
                    position_id INTEGER,
                    market_id TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    filled_size REAL DEFAULT 0,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    filled_time TIMESTAMP,
                    cancelled_time TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions (id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_market_id 
                ON positions(market_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_status 
                ON positions(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_position_id 
                ON trades(position_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_market_id 
                ON trades(market_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_order_id 
                ON orders(order_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status 
                ON orders(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_position_id 
                ON orders(position_id)
            """)
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.DB.INIT.ERROR",
                msg="数据库初始化失败",
                error_code="E-POSITION-001",
                extra={"error": str(e)}
            )
            raise
        finally:
            conn.close()
    
    # ==================== Position CRUD ====================
    
    def create_position(self, position: Position) -> int:
        """
        创建新持仓记录
        
        参数:
            position: Position对象
            
        返回:
            int: 新创建的持仓ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO positions (
                    market_id, side, entry_price, shares, invest_amount,
                    settle_day, status, current_price, pnl, is_settled,
                    settlement_result, settlement_payout, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.market_id,
                position.side,
                position.entry_price,
                position.shares,
                position.invest_amount,
                position.settle_day,
                position.status.value,
                position.current_price,
                position.pnl,
                1 if position.is_settled else 0,
                position.settlement_result,
                position.settlement_payout,
                json.dumps(position.metadata)
            ))
            
            conn.commit()
            position_id = cursor.lastrowid
            
            vlogger.info(
                "POSITION.CREATE",
                msg="创建持仓记录",
                extra={
                    "position_id": position_id,
                    "market_id": position.market_id,
                    "side": position.side,
                    "shares": position.shares
                }
            )
            
            return position_id
            
        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.CREATE.ERROR",
                msg="创建持仓记录失败",
                error_code="E-POSITION-002",
                extra={"error": str(e), "market_id": position.market_id}
            )
            raise
        finally:
            conn.close()
    
    def get_position(self, position_id: int) -> Optional[Position]:
        """
        获取持仓记录
        
        参数:
            position_id: 持仓ID
            
        返回:
            Optional[Position]: Position对象，如果不存在则返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_position(row)
            return None
            
        finally:
            conn.close()
    
    def get_positions_by_market(self, market_id: str) -> List[Position]:
        """
        获取指定市场的所有持仓

        参数:
            market_id: 市场ID

        返回:
            List[Position]: Position对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM positions WHERE market_id = ? ORDER BY create_time DESC",
                (market_id,)
            )
            rows = cursor.fetchall()

            return [self._row_to_position(row) for row in rows]

        finally:
            conn.close()

    def get_open_positions(self) -> List[Position]:
        """
        获取所有未平仓的持仓

        返回:
            List[Position]: Position对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM positions WHERE status = ? ORDER BY create_time DESC",
                (PositionStatus.OPEN.value,)
            )
            rows = cursor.fetchall()

            return [self._row_to_position(row) for row in rows]

        finally:
            conn.close()

    def update_position(self, position: Position) -> bool:
        """
        更新持仓记录

        参数:
            position: Position对象

        返回:
            bool: 是否更新成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE positions SET
                    status = ?,
                    current_price = ?,
                    pnl = ?,
                    is_settled = ?,
                    settlement_result = ?,
                    settlement_payout = ?,
                    update_time = CURRENT_TIMESTAMP,
                    close_time = ?,
                    metadata = ?
                WHERE id = ?
            """, (
                position.status.value,
                position.current_price,
                position.pnl,
                1 if position.is_settled else 0,
                position.settlement_result,
                position.settlement_payout,
                position.close_time.isoformat() if position.close_time else None,
                json.dumps(position.metadata),
                position.id
            ))

            conn.commit()
            success = cursor.rowcount > 0

            if success:
                vlogger.info(
                    "POSITION.UPDATE",
                    msg="更新持仓记录",
                    extra={
                        "position_id": position.id,
                        "status": position.status.value,
                        "current_price": position.current_price
                    }
                )

            return success

        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.UPDATE.ERROR",
                msg="更新持仓记录失败",
                error_code="E-POSITION-003",
                extra={"error": str(e), "position_id": position.id}
            )
            raise
        finally:
            conn.close()

    def _row_to_position(self, row: sqlite3.Row) -> Position:
        """将数据库行转换为Position对象"""
        return Position(
            id=row["id"],
            market_id=row["market_id"],
            side=row["side"],
            entry_price=row["entry_price"],
            shares=row["shares"],
            invest_amount=row["invest_amount"],
            settle_day=row["settle_day"],
            status=PositionStatus(row["status"]),
            current_price=row["current_price"],
            pnl=row["pnl"],
            is_settled=bool(row["is_settled"]),
            settlement_result=row["settlement_result"],
            settlement_payout=row["settlement_payout"],
            create_time=datetime.fromisoformat(row["create_time"]) if row["create_time"] else None,
            update_time=datetime.fromisoformat(row["update_time"]) if row["update_time"] else None,
            close_time=datetime.fromisoformat(row["close_time"]) if row["close_time"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )

    # ==================== Trade CRUD ====================

    def create_trade(self, trade: Trade) -> int:
        """
        创建交易记录

        参数:
            trade: Trade对象

        返回:
            int: 新创建的交易ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO trades (
                    position_id, market_id, side, price, shares,
                    amount, trade_type, order_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.position_id,
                trade.market_id,
                trade.side,
                trade.price,
                trade.shares,
                trade.amount,
                trade.trade_type,
                trade.order_id,
                json.dumps(trade.metadata)
            ))

            conn.commit()
            trade_id = cursor.lastrowid

            vlogger.trade(
                "POSITION.TRADE.CREATE",
                msg="记录交易",
                extra={
                    "trade_id": trade_id,
                    "market_id": trade.market_id,
                    "side": trade.side,
                    "price": trade.price,
                    "shares": trade.shares,
                    "amount": trade.amount
                }
            )

            return trade_id

        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.TRADE.CREATE.ERROR",
                msg="创建交易记录失败",
                error_code="E-POSITION-004",
                extra={"error": str(e), "market_id": trade.market_id}
            )
            raise
        finally:
            conn.close()

    def get_trades_by_position(self, position_id: int) -> List[Trade]:
        """
        获取指定持仓的所有交易记录

        参数:
            position_id: 持仓ID

        返回:
            List[Trade]: Trade对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM trades WHERE position_id = ? ORDER BY trade_time DESC",
                (position_id,)
            )
            rows = cursor.fetchall()

            return [self._row_to_trade(row) for row in rows]

        finally:
            conn.close()

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """将数据库行转换为Trade对象"""
        return Trade(
            id=row["id"],
            position_id=row["position_id"],
            market_id=row["market_id"],
            side=row["side"],
            price=row["price"],
            shares=row["shares"],
            amount=row["amount"],
            trade_type=row["trade_type"],
            order_id=row["order_id"],
            trade_time=datetime.fromisoformat(row["trade_time"]) if row["trade_time"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )

    # ==================== Order CRUD ====================

    def create_order(self, order: Order) -> int:
        """
        创建订单记录

        参数:
            order: Order对象

        返回:
            int: 新创建的订单记录ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO orders (
                    order_id, position_id, market_id, token_id, side,
                    price, size, status, filled_size, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id,
                order.position_id,
                order.market_id,
                order.token_id,
                order.side,
                order.price,
                order.size,
                order.status.value,
                order.filled_size,
                json.dumps(order.metadata)
            ))

            conn.commit()
            record_id = cursor.lastrowid

            vlogger.info(
                "POSITION.ORDER.CREATE",
                msg="创建订单记录",
                extra={
                    "record_id": record_id,
                    "order_id": order.order_id,
                    "market_id": order.market_id,
                    "side": order.side,
                    "size": order.size
                }
            )

            return record_id

        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.ORDER.CREATE.ERROR",
                msg="创建订单记录失败",
                error_code="E-POSITION-005",
                extra={"error": str(e), "order_id": order.order_id}
            )
            raise
        finally:
            conn.close()

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """
        根据订单ID获取订单记录

        参数:
            order_id: 订单ID

        返回:
            Optional[Order]: Order对象，如果不存在则返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_order(row)
            return None

        finally:
            conn.close()

    def get_pending_orders(self) -> List[Order]:
        """
        获取所有待成交的订单

        返回:
            List[Order]: Order对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY create_time DESC",
                (OrderStatus.PENDING.value,)
            )
            rows = cursor.fetchall()

            return [self._row_to_order(row) for row in rows]

        finally:
            conn.close()

    def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        filled_size: Optional[float] = None
    ) -> bool:
        """
        更新订单状态

        参数:
            order_id: 订单ID
            status: 新状态
            filled_size: 已成交数量（可选）

        返回:
            bool: 是否更新成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 构建更新语句
            update_fields = ["status = ?", "update_time = CURRENT_TIMESTAMP"]
            params = [status.value]

            if filled_size is not None:
                update_fields.append("filled_size = ?")
                params.append(filled_size)

            if status == OrderStatus.FILLED:
                update_fields.append("filled_time = CURRENT_TIMESTAMP")
            elif status == OrderStatus.CANCELLED:
                update_fields.append("cancelled_time = CURRENT_TIMESTAMP")

            params.append(order_id)

            query = f"UPDATE orders SET {', '.join(update_fields)} WHERE order_id = ?"
            cursor.execute(query, params)

            conn.commit()
            success = cursor.rowcount > 0

            if success:
                vlogger.info(
                    "POSITION.ORDER.UPDATE",
                    msg="更新订单状态",
                    extra={
                        "order_id": order_id,
                        "status": status.value,
                        "filled_size": filled_size
                    }
                )

            return success

        except Exception as e:
            conn.rollback()
            vlogger.error(
                "POSITION.ORDER.UPDATE.ERROR",
                msg="更新订单状态失败",
                error_code="E-POSITION-006",
                extra={"error": str(e), "order_id": order_id}
            )
            raise
        finally:
            conn.close()

    def _row_to_order(self, row: sqlite3.Row) -> Order:
        """将数据库行转换为Order对象"""
        return Order(
            id=row["id"],
            order_id=row["order_id"],
            position_id=row["position_id"],
            market_id=row["market_id"],
            token_id=row["token_id"],
            side=row["side"],
            price=row["price"],
            size=row["size"],
            status=OrderStatus(row["status"]),
            filled_size=row["filled_size"],
            create_time=datetime.fromisoformat(row["create_time"]) if row["create_time"] else None,
            update_time=datetime.fromisoformat(row["update_time"]) if row["update_time"] else None,
            filled_time=datetime.fromisoformat(row["filled_time"]) if row["filled_time"] else None,
            cancelled_time=datetime.fromisoformat(row["cancelled_time"]) if row["cancelled_time"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )

