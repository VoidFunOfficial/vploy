"""
VLogger 配置管理

提供 VLogger 日志配置和邮件配置的读取/写入接口。
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .config_manager import get_config_manager


def get_vlogger_config(db_path: str = "backend/sys_configs/system_config.db") -> Dict[str, Any]:
    """
    获取 VLogger 日志配置
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        Dict[str, Any]: 配置字典
    """
    config_manager = get_config_manager(db_path)
    
    query = """
        SELECT config_key, config_value, config_type FROM vlogger_config
    """
    rows = config_manager.execute_query(query)
    
    config = {}
    for row in rows:
        key = row['config_key']
        value = row['config_value']
        config_type = row['config_type']
        
        # 根据类型转换值
        if config_type == 'boolean':
            config[key] = value.lower() == 'true'
        elif config_type == 'integer':
            config[key] = int(value)
        elif config_type == 'float':
            config[key] = float(value)
        elif config_type == 'json':
            config[key] = json.loads(value)
        else:
            config[key] = value
    
    return config


def save_vlogger_config(config: Dict[str, Any], db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    保存 VLogger 日志配置
    
    参数:
        config: 配置字典
        db_path: 数据库文件路径
        
    返回:
        bool: 保存是否成功
    """
    config_manager = get_config_manager(db_path)
    
    try:
        for key, value in config.items():
            # 确定配置类型
            if isinstance(value, bool):
                config_type = 'boolean'
                config_value = 'true' if value else 'false'
            elif isinstance(value, int):
                config_type = 'integer'
                config_value = str(value)
            elif isinstance(value, float):
                config_type = 'float'
                config_value = str(value)
            elif isinstance(value, (dict, list)):
                config_type = 'json'
                config_value = json.dumps(value, ensure_ascii=False)
            else:
                config_type = 'string'
                config_value = str(value)
            
            # 更新或插入配置
            query = """
                INSERT INTO vlogger_config (config_key, config_value, config_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_value = excluded.config_value,
                    config_type = excluded.config_type,
                    updated_at = CURRENT_TIMESTAMP
            """
            config_manager.execute_update(query, (key, config_value, config_type))
        
        return True
    except Exception as e:
        print(f"[VLoggerConfig] 保存配置失败: {str(e)}")
        return False


def get_email_config(db_path: str = "backend/sys_configs/system_config.db") -> Dict[str, Any]:
    """
    获取邮件配置
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        Dict[str, Any]: 邮件配置字典
    """
    config_manager = get_config_manager(db_path)
    
    query = """
        SELECT config_key, config_value, config_type FROM email_config
    """
    rows = config_manager.execute_query(query)
    
    config = {}
    for row in rows:
        key = row['config_key']
        value = row['config_value']
        config_type = row['config_type']
        
        # 根据类型转换值
        if config_type == 'boolean':
            config[key] = value.lower() == 'true'
        elif config_type == 'integer':
            config[key] = int(value)
        elif config_type == 'float':
            config[key] = float(value)
        elif config_type == 'json':
            config[key] = json.loads(value)
        else:
            config[key] = value
    
    return config


def save_email_config(config: Dict[str, Any], db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    保存邮件配置
    
    参数:
        config: 邮件配置字典
        db_path: 数据库文件路径
        
    返回:
        bool: 保存是否成功
    """
    config_manager = get_config_manager(db_path)
    
    try:
        for key, value in config.items():
            # 确定配置类型
            if isinstance(value, bool):
                config_type = 'boolean'
                config_value = 'true' if value else 'false'
            elif isinstance(value, int):
                config_type = 'integer'
                config_value = str(value)
            elif isinstance(value, float):
                config_type = 'float'
                config_value = str(value)
            elif isinstance(value, (dict, list)):
                config_type = 'json'
                config_value = json.dumps(value, ensure_ascii=False)
            else:
                config_type = 'string'
                config_value = str(value)
            
            # 更新或插入配置
            query = """
                INSERT INTO email_config (config_key, config_value, config_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_value = excluded.config_value,
                    config_type = excluded.config_type,
                    updated_at = CURRENT_TIMESTAMP
            """
            config_manager.execute_update(query, (key, config_value, config_type))
        
        return True
    except Exception as e:
        print(f"[EmailConfig] 保存配置失败: {str(e)}")
        return False


def get_vlogger_config_value(key: str, default: Any = None, db_path: str = "backend/sys_configs/system_config.db") -> Any:
    """
    获取单个 VLogger 配置项的值
    
    参数:
        key: 配置键
        default: 默认值
        db_path: 数据库文件路径
        
    返回:
        Any: 配置值
    """
    config = get_vlogger_config(db_path)
    return config.get(key, default)


def set_vlogger_config_value(key: str, value: Any, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    设置单个 VLogger 配置项的值
    
    参数:
        key: 配置键
        value: 配置值
        db_path: 数据库文件路径
        
    返回:
        bool: 设置是否成功
    """
    return save_vlogger_config({key: value}, db_path)


def get_email_config_value(key: str, default: Any = None, db_path: str = "backend/sys_configs/system_config.db") -> Any:
    """
    获取单个邮件配置项的值
    
    参数:
        key: 配置键
        default: 默认值
        db_path: 数据库文件路径
        
    返回:
        Any: 配置值
    """
    config = get_email_config(db_path)
    return config.get(key, default)


def set_email_config_value(key: str, value: Any, db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    设置单个邮件配置项的值
    
    参数:
        key: 配置键
        value: 配置值
        db_path: 数据库文件路径
        
    返回:
        bool: 设置是否成功
    """
    return save_email_config({key: value}, db_path)

