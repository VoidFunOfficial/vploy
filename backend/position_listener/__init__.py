"""
仓位监听模块

提供Polymarket仓位的实时监听和价格更新功能。
使用gamma_markets.py中的Market和Event数据结构。
"""

from .position_monitor import (
    monitor_all_positions,
    update_position_data,
    get_market_data,
    get_market_current_price,
    check_market_status,
    check_threshold_trigger,
    get_position_market_info,
    batch_get_markets
)

from .database import (
    get_db,
    PositionListenerDatabase
)

__all__ = [
    # 监听功能
    'monitor_all_positions',
    'update_position_data',
    'get_market_data',
    'get_market_current_price',
    'check_market_status',
    'check_threshold_trigger',
    'get_position_market_info',
    'batch_get_markets',

    # 数据库操作
    'get_db',
    'PositionListenerDatabase'
]

