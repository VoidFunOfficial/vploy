"""
日志等级定义

定义了 6 个日志等级及其优先级、采样策略等属性。
"""

from enum import Enum
from typing import Dict, Any


class LogLevel(str, Enum):
    """
    日志等级枚举
    
    6 个日志等级：
    - INFO: 正常状态与关键业务里程碑
    - TRADE: 交易证据级流水（永不采样、长期留存）
    - WARN: 可能影响收益或稳定性的异常
    - ERROR: 功能性失败
    - DEBUG: 调试细粒度信息，默认禁用
    - AUDIT: 敏感操作审计，不走告警通道
    """
    
    INFO = "INFO"
    TRADE = "TRADE"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    AUDIT = "AUDIT"
    
    @property
    def priority(self) -> int:
        """
        获取日志等级的优先级（数值越大优先级越高）
        
        返回:
            int: 优先级数值
        """
        priority_map = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARN: 30,
            LogLevel.ERROR: 40,
            LogLevel.TRADE: 50,  # TRADE 优先级最高，确保不被过滤
            LogLevel.AUDIT: 45,
        }
        return priority_map[self]
    
    @property
    def can_sample(self) -> bool:
        """
        判断该日志等级是否可以采样
        
        返回:
            bool: True 表示可以采样，False 表示必须 100% 记录
        """
        # TRADE 和 AUDIT 永不采样
        return self not in (LogLevel.TRADE, LogLevel.AUDIT)
    
    @property
    def default_sample_rate(self) -> float:
        """
        获取默认采样率
        
        返回:
            float: 采样率（0.0-1.0），1.0 表示 100% 记录
        """
        sample_rates = {
            LogLevel.DEBUG: 0.0,   # 默认关闭
            LogLevel.INFO: 0.2,    # 20% 采样
            LogLevel.WARN: 1.0,    # 100% 记录
            LogLevel.ERROR: 1.0,   # 100% 记录
            LogLevel.TRADE: 1.0,   # 100% 记录（永不采样）
            LogLevel.AUDIT: 1.0,   # 100% 记录（永不采样）
        }
        return sample_rates[self]
    
    @property
    def retention_days(self) -> int:
        """
        获取日志留存天数
        
        返回:
            int: 留存天数
        """
        retention_map = {
            LogLevel.DEBUG: 7,      # 7 天
            LogLevel.INFO: 30,      # 30 天
            LogLevel.WARN: 30,      # 30 天
            LogLevel.ERROR: 30,     # 30 天
            LogLevel.TRADE: 180,    # 180 天（合规要求）
            LogLevel.AUDIT: 180,    # 180 天（合规要求）
        }
        return retention_map[self]
    
    @property
    def should_alert(self) -> bool:
        """
        判断该日志等级是否应该触发告警
        
        返回:
            bool: True 表示应该触发告警
        """
        # WARN 和 ERROR 触发告警，AUDIT 不触发告警
        return self in (LogLevel.WARN, LogLevel.ERROR)
    
    def to_loguru_level(self) -> str:
        """
        转换为 loguru 的日志等级
        
        返回:
            str: loguru 日志等级名称
        """
        # 将自定义等级映射到 loguru 的标准等级
        level_map = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARN: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.TRADE: "SUCCESS",  # 使用 SUCCESS 等级表示 TRADE
            LogLevel.AUDIT: "INFO",     # AUDIT 使用 INFO 等级
        }
        return level_map[self]
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取日志等级的完整元数据
        
        返回:
            dict: 包含优先级、采样率、留存天数等信息的字典
        """
        return {
            "level": self.value,
            "priority": self.priority,
            "can_sample": self.can_sample,
            "default_sample_rate": self.default_sample_rate,
            "retention_days": self.retention_days,
            "should_alert": self.should_alert,
            "loguru_level": self.to_loguru_level(),
        }


def get_level_by_name(name: str) -> LogLevel:
    """
    根据名称获取日志等级
    
    参数:
        name: 日志等级名称（不区分大小写）
        
    返回:
        LogLevel: 日志等级枚举
        
    异常:
        ValueError: 如果日志等级名称无效
    """
    try:
        return LogLevel[name.upper()]
    except KeyError:
        raise ValueError(f"无效的日志等级: {name}，有效值为: {[l.value for l in LogLevel]}")


def get_all_levels() -> Dict[str, Dict[str, Any]]:
    """
    获取所有日志等级的元数据
    
    返回:
        dict: 所有日志等级的元数据字典
    """
    return {level.value: level.get_metadata() for level in LogLevel}

