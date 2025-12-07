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

from .auth_config import (
    AuthConfig,
    get_auth_config,
)

from .position_listen_config import (
    add_position_listen,
    get_position_listen_list,
    update_position_listen,
    remove_position_listen,
    deactivate_position_listen,
    clear_position_listen_list,
)

from .token_refresher import (
    TokenRefresher,
    TokenType,
    TokenConfig,
    get_token_refresher,
)

from .sys_settings import (
    get_setting,
    get_all_settings,
    set_setting,
    delete_setting,
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
    # 认证配置
    "AuthConfig",
    "get_auth_config",
    # 持仓监听配置
    "add_position_listen",
    "get_position_listen_list",
    "update_position_listen",
    "remove_position_listen",
    "deactivate_position_listen",
    "clear_position_listen_list",
    # Token 刷新管理
    "TokenRefresher",
    "TokenType",
    "TokenConfig",
    "get_token_refresher",
    # 系统设置
    "get_setting",
    "get_all_settings",
    "set_setting",
    "delete_setting",
]

