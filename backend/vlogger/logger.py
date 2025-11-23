"""
VLogger 核心日志模块

基于 loguru 实现的结构化日志记录器。
"""

import json
import random
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger as loguru_logger

from .config import LogConfig
from .levels import LogLevel
from .events import get_event, _event_registry
from .errors import get_error, _error_registry
from .alerts import _alert_manager
from .sanitizer import _default_sanitizer
from .trace import get_or_create_trace_id


class VLogger:
    """
    结构化日志记录器
    
    提供统一的日志记录接口，支持：
    - 6 级日志等级
    - 事件类型和错误码
    - 结构化 JSON 输出
    - 敏感信息脱敏
    - 告警机制
    - trace_id 追踪
    - 采样控制
    """
    
    def __init__(self, config: Optional[LogConfig] = None):
        """
        初始化日志记录器
        
        参数:
            config: 日志配置，如果为 None 则使用默认配置
        """
        self.config = config or LogConfig()
        self._setup_loguru()
    
    def _setup_loguru(self):
        """配置 loguru"""
        # 移除默认的处理器
        loguru_logger.remove()
        
        # 添加控制台处理器
        if self.config.enable_console:
            if self.config.enable_json:
                loguru_logger.add(
                    sink=lambda msg: print(msg, end=""),
                    format="{message}",
                    level=self.config.min_level,
                )
            else:
                loguru_logger.add(
                    sink=lambda msg: print(msg, end=""),
                    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                           "<level>{level: <8}</level> | "
                           "<cyan>{extra[service]}</cyan> | "
                           "{message}",
                    level=self.config.min_level,
                )
        
        # 添加文件处理器
        if self.config.enable_file:
            log_file = self.config.get_log_file_path()
            if self.config.enable_json:
                loguru_logger.add(
                    sink=log_file,
                    format="{message}",
                    rotation=self.config.rotation,
                    retention=self.config.retention,
                    compression=self.config.compression,
                    level=self.config.min_level,
                )
            else:
                loguru_logger.add(
                    sink=log_file,
                    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                           "{extra[service]} | {message}",
                    rotation=self.config.rotation,
                    retention=self.config.retention,
                    compression=self.config.compression,
                    level=self.config.min_level,
                )
    
    def _should_sample(self, level: LogLevel) -> bool:
        """
        判断是否应该采样（记录）该日志
        
        参数:
            level: 日志等级
            
        返回:
            bool: True 表示应该记录
        """
        # TRADE 和 AUDIT 永不采样
        if not level.can_sample:
            return True
        
        # 获取采样率
        sample_rate = self.config.get_sample_rate(level.value)
        
        # 随机采样
        return random.random() < sample_rate
    
    def _build_log_entry(
        self,
        level: LogLevel,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建结构化日志条目
        
        参数:
            level: 日志等级
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            error_code: 错误码
            trace_id: 追踪 ID
            
        返回:
            dict: 结构化日志条目
        """
        # 获取或创建 trace_id
        if trace_id is None:
            trace_id = get_or_create_trace_id()
        
        # 获取事件码
        event_obj = get_event(event)
        event_code = event_obj.code if event_obj else event
        
        # 构建基础日志条目
        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level.value,
            "event": event,
            "event_code": event_code,
            "trace_id": trace_id,
            "service": self.config.service_name,
            "msg": msg,
        }
        
        # 添加错误码
        if error_code:
            log_entry["error_code"] = error_code
            error_obj = get_error(error_code)
            if error_obj:
                log_entry["error_name"] = error_obj.name
        
        # 添加额外字段
        if extra:
            # 脱敏处理
            if self.config.enable_sanitization:
                extra = _default_sanitizer.sanitize_dict(extra, deep=True)
            log_entry["extra"] = extra
        
        # 添加全局额外字段
        if self.config.extra_fields:
            log_entry.update(self.config.extra_fields)
        
        return log_entry
    
    def _log(
        self,
        level: LogLevel,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """
        内部日志记录方法
        
        参数:
            level: 日志等级
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            error_code: 错误码
            trace_id: 追踪 ID
        """
        # 采样检查
        if not self._should_sample(level):
            return
        
        # 构建日志条目
        log_entry = self._build_log_entry(level, event, msg, extra, error_code, trace_id)
        
        # 格式化输出
        if self.config.enable_json:
            log_message = json.dumps(log_entry, ensure_ascii=False)
        else:
            log_message = msg
        
        # 使用 loguru 记录日志
        loguru_level = level.to_loguru_level()
        loguru_logger.bind(service=self.config.service_name).log(
            loguru_level,
            log_message
        )
        
        # 触发告警
        if self.config.enable_alerts and level.should_alert:
            alert_code = error_code or event
            _alert_manager.send_alert(alert_code, msg, extra)
    
    def info(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 INFO 级别日志
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            trace_id: 追踪 ID
        """
        self._log(LogLevel.INFO, event, msg, extra, trace_id=trace_id)
    
    def trade(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 TRADE 级别日志（交易证据级流水）
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            trace_id: 追踪 ID
        """
        self._log(LogLevel.TRADE, event, msg, extra, trace_id=trace_id)
    
    def warn(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 WARN 级别日志
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            error_code: 错误码
            trace_id: 追踪 ID
        """
        self._log(LogLevel.WARN, event, msg, extra, error_code, trace_id)
    
    def error(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 ERROR 级别日志
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            error_code: 错误码
            trace_id: 追踪 ID
        """
        self._log(LogLevel.ERROR, event, msg, extra, error_code, trace_id)
    
    def debug(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 DEBUG 级别日志
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            trace_id: 追踪 ID
        """
        self._log(LogLevel.DEBUG, event, msg, extra, trace_id=trace_id)
    
    def audit(
        self,
        event: str,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ):
        """
        记录 AUDIT 级别日志（敏感操作审计）
        
        参数:
            event: 事件名称
            msg: 日志消息
            extra: 额外字段
            trace_id: 追踪 ID
        """
        self._log(LogLevel.AUDIT, event, msg, extra, trace_id=trace_id)


# 全局日志记录器实例
_default_logger: Optional[VLogger] = None


def get_logger(service_name: Optional[str] = None, config: Optional[LogConfig] = None, use_db_config: bool = True) -> VLogger:
    """
    获取日志记录器实例

    参数:
        service_name: 服务名称
        config: 日志配置
        use_db_config: 是否尝试从数据库加载配置（默认为 True）

    返回:
        VLogger: 日志记录器实例
    """
    global _default_logger

    # 如果没有提供配置，尝试从数据库加载
    if config is None and use_db_config:
        try:
            config = LogConfig.from_database()
            if service_name is not None:
                config.service_name = service_name
        except Exception:
            # 如果从数据库加载失败，使用默认配置
            if service_name is not None:
                config = LogConfig(service_name=service_name)
    elif config is None and service_name is not None:
        config = LogConfig(service_name=service_name)

    if _default_logger is None:
        _default_logger = VLogger(config)

    return _default_logger

