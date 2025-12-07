"""
系统设置管理模块

提供通用的系统设置存储和管理功能，支持多种数据类型。
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

from .config_manager import get_config_manager


def get_setting(key: str, default: Any = None, db_path: str = "backend/sys_configs/system_config.db") -> Any:
    """
    获取单个系统设置项的值
    
    参数:
        key: 设置键
        default: 默认值（当设置不存在时返回）
        db_path: 数据库文件路径
        
    返回:
        Any: 设置值（根据value_type自动反序列化）
    """
    config_manager = get_config_manager(db_path)
    
    try:
        query = "SELECT value, value_type FROM sys_settings WHERE key = ?"
        rows = config_manager.execute_query(query, (key,))
        
        if not rows:
            return default
        
        row = rows[0]
        value_str = row['value']
        value_type = row['value_type']
        
        # 根据类型反序列化
        return _deserialize_value(value_str, value_type)
        
    except Exception as e:
        print(f"[SysSettings] 获取设置失败: {str(e)}")
        return default


def get_all_settings(db_path: str = "backend/sys_configs/system_config.db") -> List[Dict[str, Any]]:
    """
    获取所有系统设置项
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        List[Dict]: 设置项列表，每项包含 key, value, value_type, description, created_at, updated_at
    """
    config_manager = get_config_manager(db_path)
    
    try:
        query = """
            SELECT key, value, value_type, description, created_at, updated_at
            FROM sys_settings
            ORDER BY key
        """
        rows = config_manager.execute_query(query)
        
        settings = []
        for row in rows:
            settings.append({
                'key': row['key'],
                'value': _deserialize_value(row['value'], row['value_type']),
                'value_type': row['value_type'],
                'description': row['description'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return settings
        
    except Exception as e:
        print(f"[SysSettings] 获取所有设置失败: {str(e)}")
        return []


def set_setting(
    key: str,
    value: Any,
    value_type: Optional[str] = None,
    description: Optional[str] = None,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    设置系统设置项（新增或更新）
    
    参数:
        key: 设置键
        value: 设置值
        value_type: 值类型（string/int/float/bool/json），如果为None则自动推断
        description: 设置描述
        db_path: 数据库文件路径
        
    返回:
        bool: 是否成功
    """
    config_manager = get_config_manager(db_path)
    
    try:
        # 自动推断类型
        if value_type is None:
            value_type = _infer_type(value)
        
        # 序列化值
        value_str = _serialize_value(value, value_type)
        
        # 插入或更新
        query = """
            INSERT INTO sys_settings (key, value, value_type, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                value_type = excluded.value_type,
                description = COALESCE(excluded.description, description),
                updated_at = CURRENT_TIMESTAMP
        """
        config_manager.execute_update(query, (key, value_str, value_type, description))
        
        print(f"[SysSettings] 设置保存成功: {key} = {value} ({value_type})")
        return True
        
    except Exception as e:
        print(f"[SysSettings] 设置保存失败: {str(e)}")
        return False


def delete_setting(key: str, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    删除系统设置项
    
    参数:
        key: 设置键
        db_path: 数据库文件路径
        
    返回:
        bool: 是否成功
    """
    config_manager = get_config_manager(db_path)
    
    try:
        query = "DELETE FROM sys_settings WHERE key = ?"
        rowcount = config_manager.execute_update(query, (key,))
        
        if rowcount > 0:
            print(f"[SysSettings] 设置删除成功: {key}")
            return True
        else:
            print(f"[SysSettings] 设置不存在: {key}")
            return False
        
    except Exception as e:
        print(f"[SysSettings] 设置删除失败: {str(e)}")
        return False


def _infer_type(value: Any) -> str:
    """
    推断值的类型
    
    参数:
        value: 值
        
    返回:
        str: 类型字符串
    """
    if isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, (dict, list)):
        return 'json'
    else:
        return 'string'


def _serialize_value(value: Any, value_type: str) -> str:
    """
    序列化值为字符串
    
    参数:
        value: 值
        value_type: 值类型
        
    返回:
        str: 序列化后的字符串
    """
    if value_type == 'json':
        return json.dumps(value, ensure_ascii=False)
    elif value_type == 'bool':
        return '1' if value else '0'
    else:
        return str(value)


def _deserialize_value(value_str: str, value_type: str) -> Any:
    """
    反序列化字符串为值
    
    参数:
        value_str: 字符串值
        value_type: 值类型
        
    返回:
        Any: 反序列化后的值
    """
    try:
        if value_type == 'bool':
            return value_str in ('1', 'true', 'True', 'TRUE')
        elif value_type == 'int':
            return int(value_str)
        elif value_type == 'float':
            return float(value_str)
        elif value_type == 'json':
            return json.loads(value_str)
        else:
            return value_str
    except Exception as e:
        print(f"[SysSettings] 反序列化失败: {str(e)}, 返回原始字符串")
        return value_str

