"""
过滤器数据库模块

提供数据库初始化、黑名单配置管理和已处理事件记录功能。
现在使用统一配置数据库（backend/sys_configs）。
"""

# 导入统一配置管理器
from backend.sys_configs import (
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
    init_config_database,
)

# 保留旧的接口以保持向后兼容
from .db_manager import (
    DatabaseManager,
    get_db_manager,
)

# 为了向后兼容，提供 init_database 函数
def init_database(db_path: str = "backend/filter/database/filter.db") -> bool:
    """
    初始化数据库（向后兼容接口）

    使用统一配置数据库。

    参数:
        db_path: 数据库文件路径（保留参数以保持兼容性，但实际使用统一配置数据库）

    返回:
        bool: 初始化是否成功
    """
    return init_config_database()


__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    "get_blacklist",
    "add_blacklist_item",
    "remove_blacklist_item",
    "update_blacklist_item",
    "is_market_processed",
    "mark_market_as_processed",
    "clear_processed_markets",
]

