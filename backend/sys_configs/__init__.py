"""
系统配置管理模块

提供统一的配置管理功能，使用 SQLite 数据库存储所有配置项。
支持 VLogger 日志配置、邮件配置、Filter 黑名单配置等。
"""

from .config_manager import (
    ConfigManager,
    get_config_manager,
    init_config_database,
)

from .vlogger_config import (
    get_vlogger_config,
    save_vlogger_config,
    get_email_config,
    save_email_config,
)

from .filter_config import (
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
)

__all__ = [
    # 配置管理器
    "ConfigManager",
    "get_config_manager",
    "init_config_database",
    # VLogger 配置
    "get_vlogger_config",
    "save_vlogger_config",
    "get_email_config",
    "save_email_config",
    # Filter 配置
    "get_blacklist",
    "add_blacklist_item",
    "remove_blacklist_item",
    "update_blacklist_item",
    "is_market_processed",
    "mark_market_as_processed",
    "clear_processed_markets",
]

