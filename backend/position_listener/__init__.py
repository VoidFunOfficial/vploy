# -*- coding: utf-8 -*-
"""
Position Listener - 持仓监听系统

提供交易记录、市场监控、订单状态追踪等功能。

主要功能:
1. 交易记录 - 根据TradeAllocation记录交易信息
2. 市场监控 - 实时监控已交易市场的价格变化和结算状态
3. 订单监控 - 追踪订单成交和撤销状态

使用示例:
    # 记录交易
    >>> from backend.position_listener import record_trade, get_position_summary
    >>> position_id = record_trade(allocation, order_id="ORDER-123", token_id="TOKEN-456")
    
    # 获取持仓汇总
    >>> summary = get_position_summary()
    
    # 手动触发监控
    >>> from backend.position_listener import monitor_position, monitor_order
    >>> monitor_position(position_id)
    >>> monitor_order("ORDER-123")
"""

from .models import Position, Trade, Order, PositionStatus, OrderStatus
from .database import PositionDatabase
from .trade_recorder import TradeRecorder
from .market_monitor import MarketMonitor, monitor_position_task, monitor_markets_task
from .order_monitor import OrderMonitor, monitor_order_task, monitor_orders_task
from ..types import TradeAllocation
from ..sys_configs.global_event_reg import vlogger


# ==================== 全局实例 ====================

# 创建全局数据库实例
_db = PositionDatabase()

# 创建全局交易记录器实例
_recorder = TradeRecorder(_db)

# 创建全局市场监控器实例
_market_monitor = MarketMonitor(_db, _recorder)

# 创建全局订单监控器实例
_order_monitor = OrderMonitor(_db)


# ==================== 便捷函数 ====================

def record_trade(
    allocation: TradeAllocation,
    order_id: str = None,
    token_id: str = None,
    task_metadata: dict = None
) -> int:
    """
    记录交易分配

    参数:
        allocation: TradeAllocation对象
        order_id: 订单ID（可选）
        token_id: Token ID（可选）
        task_metadata: 任务元信息（可选），包含analysis、market、marks、source_analysis_task_id等

    返回:
        int: 创建的持仓ID
    """
    return _recorder.record_trade_allocation(allocation, order_id, token_id, task_metadata)


def get_position(position_id: int) -> Position:
    """
    获取持仓信息
    
    参数:
        position_id: 持仓ID
        
    返回:
        Position: 持仓对象
    """
    return _db.get_position(position_id)


def get_positions_by_market(market_id: str) -> list:
    """
    获取指定市场的所有持仓
    
    参数:
        market_id: 市场ID
        
    返回:
        list: Position对象列表
    """
    return _db.get_positions_by_market(market_id)


def get_open_positions() -> list:
    """
    获取所有未平仓的持仓
    
    返回:
        list: Position对象列表
    """
    return _db.get_open_positions()


def get_position_summary() -> dict:
    """
    获取持仓汇总信息
    
    返回:
        dict: 持仓汇总数据
    """
    return _recorder.get_position_summary()


def update_position_price(position_id: int, current_price: float) -> bool:
    """
    更新持仓价格
    
    参数:
        position_id: 持仓ID
        current_price: 当前价格
        
    返回:
        bool: 是否更新成功
    """
    return _recorder.update_position_price(position_id, current_price)


def settle_position(
    position_id: int,
    settlement_result: str,
    settlement_payout: float
) -> bool:
    """
    结算持仓
    
    参数:
        position_id: 持仓ID
        settlement_result: 结算结果（YES/NO）
        settlement_payout: 结算收益
        
    返回:
        bool: 是否结算成功
    """
    return _recorder.settle_position(position_id, settlement_result, settlement_payout)


def monitor_position(position_id: int) -> dict:
    """
    监控单个持仓
    
    参数:
        position_id: 持仓ID
        
    返回:
        dict: 监控结果
    """
    return _market_monitor.monitor_position(position_id)


def monitor_all_positions() -> dict:
    """
    监控所有未平仓持仓
    
    返回:
        dict: 监控结果汇总
    """
    return _market_monitor.monitor_all_open_positions()


def create_order_record(
    order_id: str,
    position_id: int,
    market_id: str,
    token_id: str,
    side: str,
    price: float,
    size: float,
    metadata: dict = None
) -> int:
    """
    创建订单记录
    
    参数:
        order_id: 订单ID
        position_id: 持仓ID
        market_id: 市场ID
        token_id: Token ID
        side: 交易方向（BUY/SELL）
        price: 订单价格
        size: 订单数量
        metadata: 额外元数据
        
    返回:
        int: 订单记录ID
    """
    order = Order(
        order_id=order_id,
        position_id=position_id,
        market_id=market_id,
        token_id=token_id,
        side=side,
        price=price,
        size=size,
        status=OrderStatus.PENDING,
        metadata=metadata or {}
    )
    return _db.create_order(order)


def monitor_order(order_id: str) -> dict:
    """
    监控单个订单
    
    参数:
        order_id: 订单ID
        
    返回:
        dict: 监控结果
    """
    return _order_monitor.monitor_order(order_id)


def monitor_all_orders() -> dict:
    """
    监控所有待成交订单

    返回:
        dict: 监控结果汇总
    """
    return _order_monitor.monitor_all_pending_orders()


def process_monitor_results(monitor_results: list) -> dict:
    """
    处理批量监控结果，更新订单状态、任务状态和purse

    参数:
        monitor_results: 监控结果列表

    返回:
        dict: 处理结果汇总
    """
    return _order_monitor.process_monitor_results(monitor_results)


def get_order(order_id: str) -> Order:
    """
    获取订单信息
    
    参数:
        order_id: 订单ID
        
    返回:
        Order: 订单对象
    """
    return _db.get_order_by_id(order_id)


def get_pending_orders() -> list:
    """
    获取所有待成交订单
    
    返回:
        list: Order对象列表
    """
    return _db.get_pending_orders()


# ==================== 模块导出 ====================

__all__ = [
    # 数据模型
    "Position",
    "Trade",
    "Order",
    "PositionStatus",
    "OrderStatus",
    
    # 核心类
    "PositionDatabase",
    "TradeRecorder",
    "MarketMonitor",
    "OrderMonitor",
    
    # 便捷函数 - 交易记录
    "record_trade",
    "get_position",
    "get_positions_by_market",
    "get_open_positions",
    "get_position_summary",
    "update_position_price",
    "settle_position",
    
    # 便捷函数 - 市场监控
    "monitor_position",
    "monitor_all_positions",
    
    # 便捷函数 - 订单监控
    "create_order_record",
    "monitor_order",
    "monitor_all_orders",
    "process_monitor_results",
    "get_order",
    "get_pending_orders",
    
    # Huey任务
    "monitor_position_task",
    "monitor_markets_task",
    "monitor_order_task",
    "monitor_orders_task",
]


# 模块初始化日志
vlogger.info(
    "POSITION_LISTENER.INIT",
    msg="Position Listener模块初始化完成",
    extra={
        "features": [
            "交易记录",
            "市场监控",
            "订单监控"
        ]
    }
)

