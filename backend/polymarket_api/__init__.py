"""
Polymarket API Python 客户端

该包提供了访问 Polymarket API 的 Python 接口，包括：
1. Gamma Markets API - 市场数据查询（无需身份验证）
2. Orderbook API - 订单簿和价格查询（无需身份验证）
3. CLOB API - 订单管理和交易（需要身份验证）
4. WebSocket API - 实时市场数据和用户订单流（部分需要身份验证）

主要功能：

Gamma Markets API（无需身份验证）:
- 获取市场数据和选项价格信息
- 获取事件信息及其关联市场
- 获取活跃市场和新增市场
- 通过标签过滤市场
- 通过 slug 查询市场和事件
- 搜索市场、事件和用户资料

Orderbook API（无需身份验证）:
- 订单簿查询（单个和批量）
- 价格和价差查询
- 市场数据查询

CLOB API（需要身份验证）:
- 订单创建、提交、取消
- 交易记录查询
- 账户余额和授权查询
- 服务器时间同步

WebSocket API:
- 市场频道（无需身份验证）：订单簿、价格变化、最新成交价
- 用户频道（需要身份验证）：用户订单、交易记录
- 自动重连和心跳保活
- 消息回调处理

使用 VLogger 记录关键操作和错误

数据结构：
- Market: 市场数据结构
- Event: 事件数据结构
- Tag: 标签数据结构

使用示例：

    # Gamma Markets API（无需身份验证）
    from polymarket_api import GammaMarketsAPI, Market, Event, Tag

    with GammaMarketsAPI() as api:
        markets = api.get_active_markets(limit=10)
        event_data = api.get_event_with_all_markets("event_id")
        crypto_markets = api.get_markets_by_tag("crypto")
        results = api.search("bitcoin")

    # Orderbook API（无需身份验证）
    from polymarket_api import PolymarketOrderbookClient

    with PolymarketOrderbookClient() as client:
        # 查询订单簿
        orderbook = client.get_orderbook(token_id)

        # 查询价格
        buy_price = client.get_price(token_id, "BUY")
        mid_price = client.get_midpoint(token_id)
        spread = client.get_spread(token_id)

        # 查询市场数据
        markets = client.get_markets()

    # CLOB API（需要身份验证）
    from polymarket_api.clob_api import (
        get_client,
        place_limit_buy_order,
        get_collateral_balance,
        get_trades
    )

    client = get_client()  # 需要配置私钥
    balance = get_collateral_balance()
    trades = get_trades(limit=50)
    response = place_limit_buy_order(token_id, price=0.55, size=100)

    # WebSocket API
    from polymarket_api import PolymarketWSClient

    # 市场频道（无需身份验证）
    client = PolymarketWSClient()
    client.on_message(lambda msg: print(msg))
    await client.connect()
    await client.subscribe_market("market_id")

    # 用户频道（需要身份验证）
    client = PolymarketWSClient(
        api_key="your_key",
        api_secret="your_secret",
        api_passphrase="your_passphrase"
    )
    await client.connect()
    await client.subscribe_user()
"""

# 导入全局 VLogger 实例
from backend.sys_configs.global_event_reg import vlogger

# Gamma Markets API
from .gamma_markets import (
    GammaMarketsAPI,
    get_active_markets,
    get_new_events,
    search,
    base_filter,
    event_summary_readable,
    event_summary_readableforai,
)

# 数据类型从 backend.types 导入
from ..types import Market, Event, Tag

# Orderbook API
from .orderbook_api import (
    PolymarketOrderbookClient,
)

# WebSocket API
from .wss_client import (
    PolymarketWSClient,
    ChannelType,
    MessageType,
    WSConfig,
)

# CLOB API 作为子模块导入（需要身份验证的订单管理功能）
from .clob_api import (
    # 客户端管理
    get_client,
    get_address,

    # 订单创建
    create_limit_order,
    create_market_order,
    post_order,

    # 订单取消
    cancel_order,
    cancel_orders,
    cancel_all_orders,
    cancel_market_orders,

    # 订单查询
    get_order,
    get_orders,
    is_order_scoring,

    # 交易记录（需要身份验证）
    get_trades,
    get_last_trade_price,

    # 账户余额
    get_balance_allowance,
    get_collateral_balance,
    get_conditional_balance,

    # 其他
    get_server_time,

    # 便捷函数
    place_limit_buy_order,
    place_limit_sell_order,
    place_market_buy_order,
    place_market_sell_order,

    # 常量
    BUY,
    SELL,
    AssetType,
    OrderType,
)

# Easy Trade API - 高级交易功能
from .easy_trade import (
    # 冰山订单
    iceberg_order,
    IcebergOrder,
    IcebergOrderStatus,
    IcebergOrderManager,
    OrderSlice,
    SliceStatus,
)

__version__ = "1.0.0"
__all__ = [
    # Gamma Markets API
    "GammaMarketsAPI",
    "Market",
    "Event",
    "Tag",
    "get_active_markets",
    "get_new_events",
    "search",
    "base_filter",
    "event_summary_readable",
    "event_summary_readableforai",

    # Orderbook API
    "PolymarketOrderbookClient",

    # WebSocket API
    "PolymarketWSClient",
    "ChannelType",
    "MessageType",
    "WSConfig",

    # CLOB API (作为子模块 - 需要身份验证的订单管理功能)
    "clob_api",
    # 客户端管理
    "get_client",
    "get_address",

    # 订单创建
    "create_limit_order",
    "create_market_order",
    "post_order",

    # 订单取消
    "cancel_order",
    "cancel_orders",
    "cancel_all_orders",
    "cancel_market_orders",

    # 订单查询
    "get_order",
    "get_orders",
    "is_order_scoring",

    # 交易记录（需要身份验证）
    "get_trades",
    "get_last_trade_price",

    # 账户余额
    "get_balance_allowance",
    "get_collateral_balance",
    "get_conditional_balance",

    # 其他
    "get_server_time",

    # 便捷函数
    "place_limit_buy_order",
    "place_limit_sell_order",
    "place_market_buy_order",
    "place_market_sell_order",

    # 常量
    "BUY",
    "SELL",
    "AssetType",
    "OrderType",

    # Easy Trade API - 高级交易功能
    "iceberg_order",
    "IcebergOrder",
    "IcebergOrderStatus",
    "IcebergOrderManager",
    "OrderSlice",
    "SliceStatus",
]

