"""
VLogger - 结构化日志模块

基于 loguru 实现的企业级结构化日志系统，支持：
- 6 级日志等级（INFO, TRADE, WARN, ERROR, DEBUG, AUDIT）
- 事件类型和事件码管理
- 错误码体系
- 告警机制（分级、去重、节流）
- 敏感信息脱敏
- trace_id 全链路追踪
- 结构化 JSON 输出

使用示例:
    >>> from vlogger import get_logger, LogLevel
    >>> logger = get_logger("strategy")
    >>> logger.info("STRATEGY.SIGNAL.GENERATED", msg="生成交易信号", extra={"symbol": "BTC-USD"})
    >>> logger.trade("EXEC.ORDER.SUBMIT", msg="提交订单", extra={"order_id": "12345"})
"""

from .logger import VLogger, get_logger
from .config import LogConfig
from .levels import LogLevel
from .events import EventRegistry, EventCode, register_event, get_event
from .errors import ErrorRegistry, ErrorCode, register_error, get_error
from .alerts import (
    AlertManager, AlertLevel, AlertRule, register_alert_rule, register_alert_handler,
    EmailConfig, EmailSender, setup_email_alerts, send_test_alert
)
from .sanitizer import Sanitizer, sanitize, add_sensitive_field
from .trace import TraceContext, generate_trace_id
from .email_helper import email_send, email_send_with_db_config

__version__ = "1.0.0"
__all__ = [
    "VLogger",
    "get_logger",
    "LogConfig",
    "LogLevel",
    "EventRegistry",
    "EventCode",
    "register_event",
    "get_event",
    "ErrorRegistry",
    "ErrorCode",
    "register_error",
    "get_error",
    "AlertManager",
    "AlertLevel",
    "AlertRule",
    "register_alert_rule",
    "register_alert_handler",
    "EmailConfig",
    "EmailSender",
    "setup_email_alerts",
    "send_test_alert",
    "Sanitizer",
    "sanitize",
    "add_sensitive_field",
    "TraceContext",
    "generate_trace_id",
    "email_send",
    "email_send_with_db_config",
]

