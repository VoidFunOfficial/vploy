# -*- coding: utf-8 -*-
"""
Position Listener 数据模型

定义持仓、交易记录、订单状态等数据模型，使用SQLite存储。
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path

from ..sys_configs.global_event_reg import vlogger


class PositionStatus(str, Enum):
    """持仓状态枚举"""
    OPEN = "open"           # 持仓中
    CLOSED = "closed"       # 已平仓（结算）
    MONITORING = "monitoring"  # 监控中


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"     # 待成交
    FILLED = "filled"       # 已成交
    CANCELLED = "cancelled" # 已撤销
    FAILED = "failed"       # 失败


class Position:
    """
    持仓数据模型
    
    属性:
        id: 持仓ID（自增主键）
        market_id: 市场ID
        side: 交易方向（YES/NO）
        entry_price: 入场价格
        shares: 持有份额
        invest_amount: 投资金额
        settle_day: 预计结算日期（天数索引）
        status: 持仓状态
        current_price: 当前价格（实时更新）
        pnl: 盈亏（实时计算）
        is_settled: 是否已结算
        settlement_result: 结算结果（YES/NO/null）
        settlement_payout: 结算收益
        create_time: 创建时间
        update_time: 更新时间
        close_time: 平仓时间
        metadata: 额外元数据（JSON格式）
    """
    
    def __init__(
        self,
        id: Optional[int] = None,
        market_id: str = "",
        side: str = "",
        entry_price: float = 0.0,
        shares: float = 0.0,
        invest_amount: float = 0.0,
        settle_day: int = 0,
        status: PositionStatus = PositionStatus.OPEN,
        current_price: Optional[float] = None,
        pnl: Optional[float] = None,
        is_settled: bool = False,
        settlement_result: Optional[str] = None,
        settlement_payout: Optional[float] = None,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None,
        close_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.market_id = market_id
        self.side = side
        self.entry_price = entry_price
        self.shares = shares
        self.invest_amount = invest_amount
        self.settle_day = settle_day
        self.status = status if isinstance(status, PositionStatus) else PositionStatus(status)
        self.current_price = current_price or entry_price
        self.pnl = pnl
        self.is_settled = is_settled
        self.settlement_result = settlement_result
        self.settlement_payout = settlement_payout
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()
        self.close_time = close_time
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "market_id": self.market_id,
            "side": self.side,
            "entry_price": self.entry_price,
            "shares": self.shares,
            "invest_amount": self.invest_amount,
            "settle_day": self.settle_day,
            "status": self.status.value,
            "current_price": self.current_price,
            "pnl": self.pnl,
            "is_settled": self.is_settled,
            "settlement_result": self.settlement_result,
            "settlement_payout": self.settlement_payout,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "metadata": self.metadata
        }


class Trade:
    """
    交易记录数据模型
    
    属性:
        id: 交易ID（自增主键）
        position_id: 关联的持仓ID
        market_id: 市场ID
        side: 交易方向（YES/NO）
        price: 交易价格
        shares: 交易份额
        amount: 交易金额
        trade_type: 交易类型（OPEN/CLOSE）
        order_id: 关联的订单ID
        trade_time: 交易时间
        metadata: 额外元数据（JSON格式）
    """
    
    def __init__(
        self,
        id: Optional[int] = None,
        position_id: Optional[int] = None,
        market_id: str = "",
        side: str = "",
        price: float = 0.0,
        shares: float = 0.0,
        amount: float = 0.0,
        trade_type: str = "OPEN",
        order_id: Optional[str] = None,
        trade_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.position_id = position_id
        self.market_id = market_id
        self.side = side
        self.price = price
        self.shares = shares
        self.amount = amount
        self.trade_type = trade_type
        self.order_id = order_id
        self.trade_time = trade_time or datetime.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "position_id": self.position_id,
            "market_id": self.market_id,
            "side": self.side,
            "price": self.price,
            "shares": self.shares,
            "amount": self.amount,
            "trade_type": self.trade_type,
            "order_id": self.order_id,
            "trade_time": self.trade_time.isoformat() if self.trade_time else None,
            "metadata": self.metadata
        }


class Order:
    """
    订单状态数据模型
    
    属性:
        id: 记录ID（自增主键）
        order_id: 订单ID（CLOB订单ID）
        position_id: 关联的持仓ID
        market_id: 市场ID
        token_id: Token ID
        side: 交易方向（BUY/SELL）
        price: 订单价格
        size: 订单数量
        status: 订单状态
        filled_size: 已成交数量
        create_time: 创建时间
        update_time: 更新时间
        filled_time: 成交时间
        cancelled_time: 撤销时间
        metadata: 额外元数据（JSON格式）
    """
    
    def __init__(
        self,
        id: Optional[int] = None,
        order_id: str = "",
        position_id: Optional[int] = None,
        market_id: str = "",
        token_id: str = "",
        side: str = "",
        price: float = 0.0,
        size: float = 0.0,
        status: OrderStatus = OrderStatus.PENDING,
        filled_size: float = 0.0,
        create_time: Optional[datetime] = None,
        update_time: Optional[datetime] = None,
        filled_time: Optional[datetime] = None,
        cancelled_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.order_id = order_id
        self.position_id = position_id
        self.market_id = market_id
        self.token_id = token_id
        self.side = side
        self.price = price
        self.size = size
        self.status = status if isinstance(status, OrderStatus) else OrderStatus(status)
        self.filled_size = filled_size
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()
        self.filled_time = filled_time
        self.cancelled_time = cancelled_time
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": self.side,
            "price": self.price,
            "size": self.size,
            "status": self.status.value,
            "filled_size": self.filled_size,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "cancelled_time": self.cancelled_time.isoformat() if self.cancelled_time else None,
            "metadata": self.metadata
        }

