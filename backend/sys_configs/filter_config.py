"""
Filter 配置管理

提供 Filter 黑名单配置和已处理事件管理的接口。
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

from .config_manager import get_config_manager


# ==================== 黑名单管理函数 ====================

def get_blacklist(blacklist_type: Optional[str] = None, db_path: str = "backend/sys_configs/system_config.db") -> Dict[str, List[str]]:
    """
    获取黑名单配置（仅返回激活的配置）

    参数:
        blacklist_type: 黑名单类型（'category' / 'tag' / 'description_keyword'），None 表示获取所有类型
        db_path: 数据库文件路径

    返回:
        dict: 黑名单配置字典，格式为 {blacklist_type: [value1, value2, ...]}
    """
    config_manager = get_config_manager(db_path)

    if blacklist_type:
        query = """
            SELECT value FROM filter_blacklist
            WHERE blacklist_type = ? AND is_active = 1
        """
        rows = config_manager.execute_query(query, (blacklist_type,))
        return {blacklist_type: [row['value'] for row in rows]}
    else:
        query = """
            SELECT blacklist_type, value FROM filter_blacklist
            WHERE is_active = 1
            ORDER BY blacklist_type, value
        """
        rows = config_manager.execute_query(query)

        result: Dict[str, List[str]] = {}
        for row in rows:
            bl_type = row['blacklist_type']
            if bl_type not in result:
                result[bl_type] = []
            result[bl_type].append(row['value'])

        return result


def add_blacklist_item(blacklist_type: str, value: str, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    添加黑名单配置项

    参数:
        blacklist_type: 黑名单类型
        value: 黑名单值
        db_path: 数据库文件路径

    返回:
        bool: 添加是否成功
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            INSERT INTO filter_blacklist (blacklist_type, value, is_active, created_at, updated_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        config_manager.execute_update(query, (blacklist_type, value))
        print(f"[FilterConfig] 添加黑名单配置项: {blacklist_type} = {value}")
        return True
    except sqlite3.IntegrityError:
        # 配置项已存在
        print(f"[FilterConfig] 黑名单配置项已存在: {blacklist_type} = {value}")
        return False
    except Exception as e:
        print(f"[FilterConfig] 添加黑名单配置项失败: {str(e)}")
        return False


def remove_blacklist_item(blacklist_type: str, value: str, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    删除黑名单配置项

    参数:
        blacklist_type: 黑名单类型
        value: 黑名单值
        db_path: 数据库文件路径

    返回:
        bool: 删除是否成功
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            DELETE FROM filter_blacklist
            WHERE blacklist_type = ? AND value = ?
        """
        rowcount = config_manager.execute_update(query, (blacklist_type, value))

        if rowcount > 0:
            print(f"[FilterConfig] 删除黑名单配置项: {blacklist_type} = {value}")
            return True
        else:
            print(f"[FilterConfig] 黑名单配置项不存在: {blacklist_type} = {value}")
            return False
    except Exception as e:
        print(f"[FilterConfig] 删除黑名单配置项失败: {str(e)}")
        return False


def update_blacklist_item(item_id: int, is_active: bool, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    更新黑名单配置项的激活状态

    参数:
        item_id: 配置项 ID
        is_active: 是否激活
        db_path: 数据库文件路径

    返回:
        bool: 更新是否成功
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            UPDATE filter_blacklist
            SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        rowcount = config_manager.execute_update(query, (1 if is_active else 0, item_id))

        if rowcount > 0:
            print(f"[FilterConfig] 更新黑名单配置项: ID={item_id}, is_active={is_active}")
            return True
        else:
            print(f"[FilterConfig] 黑名单配置项不存在: ID={item_id}")
            return False
    except Exception as e:
        print(f"[FilterConfig] 更新黑名单配置项失败: {str(e)}")
        return False


# ==================== 已处理事件管理函数 ====================

def is_market_processed(market_id: str, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    检查市场是否已处理

    参数:
        market_id: 市场 ID
        db_path: 数据库文件路径

    返回:
        bool: 是否已处理
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            SELECT COUNT(*) as count FROM processed_markets
            WHERE market_id = ?
        """
        rows = config_manager.execute_query(query, (market_id,))
        return rows[0]['count'] > 0
    except Exception as e:
        print(f"[FilterConfig] 检查市场处理状态失败: {str(e)}")
        return False


def mark_market_as_processed(market_id: str, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    标记市场为已处理

    参数:
        market_id: 市场 ID
        db_path: 数据库文件路径

    返回:
        bool: 标记是否成功
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            INSERT OR IGNORE INTO processed_markets (market_id, processed_at, created_at)
            VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        config_manager.execute_update(query, (market_id,))
        return True
    except Exception as e:
        print(f"[FilterConfig] 标记市场失败: {str(e)}")
        return False


def clear_processed_markets(before_date: Optional[datetime] = None, db_path: str = "backend/sys_configs/system_config.db") -> int:
    """
    清理已处理市场记录

    参数:
        before_date: 清理此日期之前的记录，None 表示清理所有记录
        db_path: 数据库文件路径

    返回:
        int: 清理的记录数量
    """
    config_manager = get_config_manager(db_path)

    try:
        if before_date:
            query = """
                DELETE FROM processed_markets
                WHERE processed_at < ?
            """
            rowcount = config_manager.execute_update(query, (before_date.isoformat(),))
        else:
            query = "DELETE FROM processed_markets"
            rowcount = config_manager.execute_update(query)

        print(f"[FilterConfig] 清理已处理市场记录: {rowcount} 条")
        return rowcount
    except Exception as e:
        print(f"[FilterConfig] 清理已处理市场记录失败: {str(e)}")
        return 0


def get_all_blacklist_items(db_path: str = "backend/sys_configs/system_config.db") -> List[Dict]:
    """
    获取所有黑名单配置项（包括未激活的）

    参数:
        db_path: 数据库文件路径

    返回:
        List[Dict]: 黑名单配置项列表
    """
    config_manager = get_config_manager(db_path)

    try:
        query = """
            SELECT id, blacklist_type, value, is_active, created_at, updated_at
            FROM filter_blacklist
            ORDER BY blacklist_type, value
        """
        rows = config_manager.execute_query(query)

        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'blacklist_type': row['blacklist_type'],
                'value': row['value'],
                'is_active': bool(row['is_active']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            })

        return result
    except Exception as e:
        print(f"[FilterConfig] 获取所有黑名单配置项失败: {str(e)}")
        return []

