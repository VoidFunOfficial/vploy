"""
VLogger 配置管理

提供 VLogger 日志配置和邮件配置的读取/写入接口。
使用 sys_settings 表存储配置,采用分层命名空间 (logging.*, mail.*)
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .sys_settings import get_setting, set_setting


def get_vlogger_config(db_path: str = "backend/sys_configs/system_config.db") -> Dict[str, Any]:
    """
    获取 VLogger 日志配置

    从 sys_settings 表读取 logging.* 命名空间的配置项

    参数:
        db_path: 数据库文件路径

    返回:
        Dict[str, Any]: 配置字典 (不带 logging. 前缀的键)
    """
    from .config_manager import get_config_manager
    config_manager = get_config_manager(db_path)

    # 查询所有 logging.* 配置项
    query = """
        SELECT key, value, value_type FROM sys_settings
        WHERE key LIKE 'logging.%'
    """
    rows = config_manager.execute_query(query)

    config = {}
    for row in rows:
        full_key = row['key']
        value_str = row['value']
        value_type = row['value_type']

        # 移除 logging. 前缀
        key = full_key.replace('logging.', '', 1)

        # 反序列化值
        if value_type == 'bool':
            config[key] = value_str in ('1', 'true', 'True', 'TRUE')
        elif value_type == 'int':
            config[key] = int(value_str)
        elif value_type == 'float':
            config[key] = float(value_str)
        elif value_type == 'json':
            config[key] = json.loads(value_str)
        else:
            config[key] = value_str

    return config


def save_vlogger_config(config: Dict[str, Any], db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    保存 VLogger 日志配置

    将配置保存到 sys_settings 表的 logging.* 命名空间

    参数:
        config: 配置字典 (不带 logging. 前缀的键)
        db_path: 数据库文件路径

    返回:
        bool: 保存是否成功
    """
    try:
        for key, value in config.items():
            # 添加 logging. 前缀
            full_key = f"logging.{key}"

            # 使用 sys_settings 的 set_setting 函数
            success = set_setting(full_key, value, db_path=db_path)
            if not success:
                print(f"[VLoggerConfig] 保存配置项失败: {key}")
                return False

        return True
    except Exception as e:
        print(f"[VLoggerConfig] 保存配置失败: {str(e)}")
        return False


def get_email_config(db_path: str = "backend/sys_configs/system_config.db") -> Dict[str, Any]:
    """
    获取邮件配置

    从 sys_settings 表读取 mail.* 命名空间的配置项

    参数:
        db_path: 数据库文件路径

    返回:
        Dict[str, Any]: 邮件配置字典 (不带 mail. 前缀的键)
    """
    from .config_manager import get_config_manager
    config_manager = get_config_manager(db_path)

    # 查询所有 mail.* 配置项
    query = """
        SELECT key, value, value_type FROM sys_settings
        WHERE key LIKE 'mail.%'
    """
    rows = config_manager.execute_query(query)

    config = {}
    for row in rows:
        full_key = row['key']
        value_str = row['value']
        value_type = row['value_type']

        # 移除 mail. 前缀
        key = full_key.replace('mail.', '', 1)

        # 反序列化值
        if value_type == 'bool':
            config[key] = value_str in ('1', 'true', 'True', 'TRUE')
        elif value_type == 'int':
            config[key] = int(value_str)
        elif value_type == 'float':
            config[key] = float(value_str)
        elif value_type == 'json':
            config[key] = json.loads(value_str)
        else:
            config[key] = value_str

    return config


def save_email_config(config: Dict[str, Any], db_path: str = "backend/sys_configs/system_config.db") -> bool:
    """
    保存邮件配置

    将配置保存到 sys_settings 表的 mail.* 命名空间

    参数:
        config: 邮件配置字典 (不带 mail. 前缀的键)
        db_path: 数据库文件路径

    返回:
        bool: 保存是否成功
    """
    try:
        for key, value in config.items():
            # 添加 mail. 前缀
            full_key = f"mail.{key}"

            # 使用 sys_settings 的 set_setting 函数
            success = set_setting(full_key, value, db_path=db_path)
            if not success:
                print(f"[EmailConfig] 保存配置项失败: {key}")
                return False

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

