"""
仓位监听模块

提供Polymarket仓位的实时监听和价格更新功能。
使用gamma_markets.py中的Market和Event数据结构。
支持 WebSocket 实时监听订单状态和市场价格变化。
"""

from .position_monitor import (
    monitor_all_positions,
    update_position_data,
    get_market_data,
    get_market_current_price,
    check_market_status,
    check_threshold_trigger,
    get_position_market_info,
    batch_get_markets,
    start_websocket_listeners,
    stop_websocket_listeners,
    add_position_with_order_tracking,
    start_wss_listeners_huey,
    stop_wss_listeners_huey,
    get_wss_status
)

from .database import (
    get_db,
    PositionListenerDatabase
)

from .order_listener import (
    get_order_listener,
    OrderListener
)

from .market_listener import (
    get_market_listener,
    MarketListener
)

from .wss_manager import (
    get_wss_manager,
    WebSocketListenerManager
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

    # WebSocket 监听
    'start_websocket_listeners',
    'stop_websocket_listeners',
    'add_position_with_order_tracking',
    'get_order_listener',
    'get_market_listener',
    'OrderListener',
    'MarketListener',

    # WebSocket 管理器 (Huey)
    'start_wss_listeners_huey',
    'stop_wss_listeners_huey',
    'get_wss_status',
    'get_wss_manager',
    'WebSocketListenerManager',

    # 数据库操作
    'get_db',
    'PositionListenerDatabase'
]

