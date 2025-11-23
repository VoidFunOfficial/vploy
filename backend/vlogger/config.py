"""
日志配置

提供日志系统的配置管理功能。
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

# 导入统一配置管理器
try:
    from ..sys_configs import get_vlogger_config, save_vlogger_config
    USE_UNIFIED_CONFIG = True
except ImportError:
    USE_UNIFIED_CONFIG = False


@dataclass
class LogConfig:
    """
    日志配置
    
    属性:
        service_name: 服务名称（ingestor, strategy, router, order_mgr, recon, frontend, core）
        log_dir: 日志文件目录
        log_file_prefix: 日志文件前缀
        rotation: 日志轮转策略（如 "500 MB", "1 day"）
        retention: 日志保留策略（如 "30 days"）
        compression: 压缩格式（如 "zip", "gz"）
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        enable_json: 是否使用 JSON 格式
        min_level: 最小日志等级
        sample_rates: 各等级的采样率配置
        enable_sanitization: 是否启用敏感信息脱敏
        enable_alerts: 是否启用告警
        extra_fields: 额外的全局字段
    """
    
    service_name: str = "core"
    log_dir: str = "./logs"
    log_file_prefix: str = "vlogger"
    rotation: str = "500 MB"
    retention: str = "30 days"
    compression: str = "zip"
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = True
    min_level: str = "INFO"
    sample_rates: Dict[str, float] = field(default_factory=dict)
    enable_sanitization: bool = True
    enable_alerts: bool = True
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保日志目录存在
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
    
    def get_log_file_path(self, level: str = "") -> str:
        """
        获取日志文件路径
        
        参数:
            level: 日志等级（可选，用于分级存储）
            
        返回:
            str: 日志文件路径
        """
        if level:
            filename = f"{self.log_file_prefix}_{level.lower()}.log"
        else:
            filename = f"{self.log_file_prefix}.log"
        
        return str(Path(self.log_dir) / filename)
    
    def get_sample_rate(self, level: str) -> float:
        """
        获取指定等级的采样率
        
        参数:
            level: 日志等级
            
        返回:
            float: 采样率（0.0-1.0）
        """
        return self.sample_rates.get(level, 1.0)
    
    def set_sample_rate(self, level: str, rate: float):
        """
        设置指定等级的采样率
        
        参数:
            level: 日志等级
            rate: 采样率（0.0-1.0）
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"采样率必须在 0.0-1.0 之间，当前值: {rate}")
        self.sample_rates[level] = rate
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "service_name": self.service_name,
            "log_dir": self.log_dir,
            "log_file_prefix": self.log_file_prefix,
            "rotation": self.rotation,
            "retention": self.retention,
            "compression": self.compression,
            "enable_console": self.enable_console,
            "enable_file": self.enable_file,
            "enable_json": self.enable_json,
            "min_level": self.min_level,
            "sample_rates": self.sample_rates,
            "enable_sanitization": self.enable_sanitization,
            "enable_alerts": self.enable_alerts,
            "extra_fields": self.extra_fields,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogConfig":
        """
        从字典创建配置

        参数:
            data: 配置字典

        返回:
            LogConfig: 配置对象
        """
        return cls(**data)

    @classmethod
    def from_database(cls, db_path: str = "backend/sys_configs/system_config.db") -> "LogConfig":
        """
        从统一配置数据库加载配置

        参数:
            db_path: 数据库文件路径

        返回:
            LogConfig: 配置对象
        """
        if not USE_UNIFIED_CONFIG:
            raise ImportError("统一配置管理器不可用，请检查 backend.sys_configs 模块")

        config_dict = get_vlogger_config(db_path)
        return cls.from_dict(config_dict)

    def save_to_database(self, db_path: str = "backend/sys_configs/system_config.db") -> bool:
        """
        保存配置到统一配置数据库

        参数:
            db_path: 数据库文件路径

        返回:
            bool: 保存是否成功
        """
        if not USE_UNIFIED_CONFIG:
            raise ImportError("统一配置管理器不可用，请检查 backend.sys_configs 模块")

        return save_vlogger_config(self.to_dict(), db_path)
    
    @classmethod
    def from_file(cls, file_path: str) -> "LogConfig":
        """
        从配置文件加载配置
        
        参数:
            file_path: 配置文件路径（支持 JSON 或 YAML）
            
        返回:
            LogConfig: 配置对象
        """
        import json
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix == '.json':
                data = json.load(f)
            elif path.suffix in ('.yaml', '.yml'):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("需要安装 PyYAML 才能加载 YAML 配置文件")
            else:
                raise ValueError(f"不支持的配置文件格式: {path.suffix}")
        
        return cls.from_dict(data)
    
    def save_to_file(self, file_path: str):
        """
        保存配置到文件
        
        参数:
            file_path: 配置文件路径
        """
        import json
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix == '.json':
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            elif path.suffix in ('.yaml', '.yml'):
                try:
                    import yaml
                    yaml.safe_dump(self.to_dict(), f, allow_unicode=True)
                except ImportError:
                    raise ImportError("需要安装 PyYAML 才能保存 YAML 配置文件")
            else:
                raise ValueError(f"不支持的配置文件格式: {path.suffix}")


# 预定义的配置模板
def get_development_config() -> LogConfig:
    """
    获取开发环境配置
    
    返回:
        LogConfig: 开发环境配置
    """
    return LogConfig(
        service_name="dev",
        log_dir="./logs/dev",
        enable_console=True,
        enable_file=True,
        enable_json=False,  # 开发环境使用可读格式
        min_level="DEBUG",
        sample_rates={
            "DEBUG": 1.0,  # 开发环境不采样
            "INFO": 1.0,
        },
        enable_sanitization=False,  # 开发环境不脱敏
        enable_alerts=False,  # 开发环境不告警
    )


def get_production_config() -> LogConfig:
    """
    获取生产环境配置
    
    返回:
        LogConfig: 生产环境配置
    """
    return LogConfig(
        service_name="prod",
        log_dir="./logs/prod",
        enable_console=False,
        enable_file=True,
        enable_json=True,  # 生产环境使用 JSON 格式
        min_level="INFO",
        sample_rates={
            "DEBUG": 0.0,  # 生产环境关闭 DEBUG
            "INFO": 0.2,   # INFO 采样 20%
            "WARN": 1.0,
            "ERROR": 1.0,
            "TRADE": 1.0,
            "AUDIT": 1.0,
        },
        enable_sanitization=True,  # 生产环境启用脱敏
        enable_alerts=True,  # 生产环境启用告警
        rotation="500 MB",
        retention="30 days",
        compression="zip",
    )


def get_test_config() -> LogConfig:
    """
    获取测试环境配置
    
    返回:
        LogConfig: 测试环境配置
    """
    return LogConfig(
        service_name="test",
        log_dir="./logs/test",
        enable_console=True,
        enable_file=True,
        enable_json=True,
        min_level="DEBUG",
        sample_rates={
            "DEBUG": 1.0,
            "INFO": 1.0,
        },
        enable_sanitization=True,
        enable_alerts=False,
    )

