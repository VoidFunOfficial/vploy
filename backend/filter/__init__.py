"""
事件过滤器模块

提供多步骤的事件（Event）和市场（Market）数据过滤功能，包括：
- Tag 黑名单过滤
- 标题关键词黑名单过滤
- 描述关键词黑名单过滤
- 数据库去重检查
- AI 处理预留接口

同时提供黑名单配置管理和已处理事件记录功能。
"""

from .event_filter import (
    EventFilter,
    filter_events,  # 保持向后兼容
)

from .market_filter import (
    MarketFilter,
    filter_markets,
)

from .database import (
    DatabaseManager,
    get_db_manager,
    init_database,
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
)

__all__ = [
    # 过滤器类和函数
    "EventFilter",
    "MarketFilter",
    "filter_events",  # 默认使用 event_filter 的 filter_events
    "filter_markets",
    # 数据库管理
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    # 黑名单管理
    "get_blacklist",
    "add_blacklist_item",
    "remove_blacklist_item",
    "update_blacklist_item",
    # 已处理事件管理
    "is_market_processed",
    "mark_market_as_processed",
    "clear_processed_markets",
]

