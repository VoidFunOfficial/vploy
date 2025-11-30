"""
告警机制

实现告警严重性分级、去重、节流等功能。
支持邮件、短信、电话等多种告警通道。
"""

import time
from enum import Enum
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass, field
from threading import Lock
from collections import defaultdict
import json
from datetime import datetime

# 导入邮件发送辅助函数
from .email_helper import email_send

# 导入统一配置管理器
try:
    from ..sys_configs import get_email_config, save_email_config
    USE_UNIFIED_CONFIG = True
except ImportError:
    USE_UNIFIED_CONFIG = False


class AlertLevel(str, Enum):
    """
    告警严重性等级
    
    - P0: 立即处理（邮件即时推送 + 可选短信/电话）
    - P1: 高优先级（邮件即时推送 + 创建待办）
    - P2: 中优先级（邮件聚合推送，5-15 分钟批量）
    - P3: 低优先级（仅在仪表盘标记，不发送邮件）
    """
    
    P0 = "P0"  # 立即处理
    P1 = "P1"  # 高优先级
    P2 = "P2"  # 中优先级
    P3 = "P3"  # 低优先级
    
    @property
    def priority(self) -> int:
        """获取优先级数值（数值越大优先级越高）"""
        priority_map = {
            AlertLevel.P3: 1,
            AlertLevel.P2: 2,
            AlertLevel.P1: 3,
            AlertLevel.P0: 4,
        }
        return priority_map[self]
    
    @property
    def should_send_email(self) -> bool:
        """是否应该发送邮件"""
        return self in (AlertLevel.P0, AlertLevel.P1, AlertLevel.P2)
    
    @property
    def should_send_sms(self) -> bool:
        """是否应该发送短信"""
        return self == AlertLevel.P0
    
    @property
    def batch_interval_seconds(self) -> int:
        """批量发送间隔（秒）"""
        if self == AlertLevel.P2:
            return 300  # 5 分钟
        return 0  # P0/P1 立即发送


@dataclass
class AlertRule:
    """
    告警规则
    
    属性:
        event_code: 事件码或错误码
        level: 告警等级
        dedup_window_seconds: 去重窗口（秒）
        throttle_max_per_minute: 每分钟最大告警数
        merge_by_fields: 合并告警的字段列表
        enabled: 是否启用
    """
    event_code: str
    level: AlertLevel
    dedup_window_seconds: int = 60
    throttle_max_per_minute: int = 2
    merge_by_fields: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class AlertRecord:
    """
    告警记录
    
    属性:
        event_code: 事件码或错误码
        level: 告警等级
        message: 告警消息
        extra: 额外信息
        timestamp: 时间戳
        count: 重复次数
    """
    event_code: str
    level: AlertLevel
    message: str
    extra: Dict[str, Any]
    timestamp: float
    count: int = 1


class AlertManager:
    """
    告警管理器
    
    提供告警规则管理、去重、节流、合并等功能。
    线程安全的单例模式。
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化告警管理器"""
        if self._initialized:
            return
        
        self._rules: Dict[str, AlertRule] = {}
        self._dedup_cache: Dict[str, AlertRecord] = {}
        self._throttle_counters: Dict[str, List[float]] = defaultdict(list)
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = Lock()
        self._initialized = True
        
        # 注册默认规则
        self._register_default_rules()
    
    def _register_default_rules(self):
        """注册默认的告警规则"""
        # WARN 级别日志默认映射到 P2
        self.register_rule(AlertRule(
            event_code="WARN",
            level=AlertLevel.P2,
            dedup_window_seconds=60,
            throttle_max_per_minute=2
        ))
        
        # ERROR 级别日志默认映射到 P1
        self.register_rule(AlertRule(
            event_code="ERROR",
            level=AlertLevel.P1,
            dedup_window_seconds=60,
            throttle_max_per_minute=2
        ))
        
        # 特定错误码升级到 P0
        critical_errors = [
            "E-SYS-001",  # 系统内部错误
            "E-SYS-004",  # 数据库错误
            "E-SYS-009",  # 资源耗尽
            "E-RECON-001",  # 对账不平
        ]
        for error_code in critical_errors:
            self.register_rule(AlertRule(
                event_code=error_code,
                level=AlertLevel.P0,
                dedup_window_seconds=300,  # 5 分钟去重窗口
                throttle_max_per_minute=1
            ))
    
    def register_rule(self, rule: AlertRule, overwrite: bool = True):
        """
        注册告警规则
        
        参数:
            rule: 告警规则
            overwrite: 是否覆盖已存在的规则
        """
        with self._lock:
            if not overwrite and rule.event_code in self._rules:
                raise ValueError(f"告警规则 {rule.event_code} 已存在")
            self._rules[rule.event_code] = rule
    
    def get_rule(self, event_code: str) -> Optional[AlertRule]:
        """
        获取告警规则
        
        参数:
            event_code: 事件码或错误码
            
        返回:
            AlertRule: 告警规则，如果不存在则返回 None
        """
        return self._rules.get(event_code)
    
    def register_handler(self, channel: str, handler: Callable):
        """
        注册告警处理器
        
        参数:
            channel: 告警通道（email, sms, phone, dashboard 等）
            handler: 处理函数，接收 AlertRecord 对象
        """
        self._handlers[channel].append(handler)
    
    def _get_dedup_key(self, event_code: str, extra: Dict[str, Any]) -> str:
        """
        生成去重键
        
        参数:
            event_code: 事件码
            extra: 额外信息
            
        返回:
            str: 去重键
        """
        # 简单实现：使用事件码作为去重键
        # 可以根据需要扩展，例如包含特定字段
        return event_code
    
    def _should_throttle(self, event_code: str, max_per_minute: int) -> bool:
        """
        检查是否应该节流
        
        参数:
            event_code: 事件码
            max_per_minute: 每分钟最大告警数
            
        返回:
            bool: 如果应该节流返回 True
        """
        now = time.time()
        one_minute_ago = now - 60
        
        # 清理过期的计数
        self._throttle_counters[event_code] = [
            ts for ts in self._throttle_counters[event_code]
            if ts > one_minute_ago
        ]
        
        # 检查是否超过限制
        if len(self._throttle_counters[event_code]) >= max_per_minute:
            return True
        
        # 记录本次告警
        self._throttle_counters[event_code].append(now)
        return False
    
    def should_alert(
        self,
        event_code: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[AlertLevel]]:
        """
        判断是否应该发送告警
        
        参数:
            event_code: 事件码或错误码
            message: 告警消息
            extra: 额外信息
            
        返回:
            tuple: (是否应该告警, 告警等级)
        """
        extra = extra or {}
        
        # 获取告警规则
        rule = self.get_rule(event_code)
        if not rule or not rule.enabled:
            return False, None
        
        # 生成去重键
        dedup_key = self._get_dedup_key(event_code, extra)
        
        with self._lock:
            # 检查去重窗口
            now = time.time()
            if dedup_key in self._dedup_cache:
                cached = self._dedup_cache[dedup_key]
                if now - cached.timestamp < rule.dedup_window_seconds:
                    # 在去重窗口内，增加计数但不发送告警
                    cached.count += 1
                    return False, rule.level
            
            # 检查节流
            if self._should_throttle(event_code, rule.throttle_max_per_minute):
                return False, rule.level
            
            # 创建新的告警记录
            record = AlertRecord(
                event_code=event_code,
                level=rule.level,
                message=message,
                extra=extra,
                timestamp=now
            )
            self._dedup_cache[dedup_key] = record
            
            return True, rule.level
    
    def send_alert(
        self,
        event_code: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        发送告警
        
        参数:
            event_code: 事件码或错误码
            message: 告警消息
            extra: 额外信息
        """
        should_send, level = self.should_alert(event_code, message, extra)
        
        if not should_send or level is None:
            return
        
        # 获取去重键对应的记录（包含累计次数）
        dedup_key = self._get_dedup_key(event_code, extra or {})
        record = self._dedup_cache.get(dedup_key)
        
        if not record:
            return
        
        # 根据告警等级调用相应的处理器
        if level.should_send_email:
            for handler in self._handlers.get("email", []):
                handler(record)
        
        if level.should_send_sms:
            for handler in self._handlers.get("sms", []):
                handler(record)
        
        # 总是发送到仪表盘
        for handler in self._handlers.get("dashboard", []):
            handler(record)
    
    def cleanup_expired(self):
        """清理过期的去重缓存"""
        now = time.time()
        with self._lock:
            expired_keys = [
                key for key, record in self._dedup_cache.items()
                if now - record.timestamp > 3600  # 1 小时后清理
            ]
            for key in expired_keys:
                del self._dedup_cache[key]


# 全局告警管理器实例
_alert_manager = AlertManager()


def register_alert_rule(rule: AlertRule, overwrite: bool = True):
    """
    注册告警规则的便捷函数
    
    参数:
        rule: 告警规则
        overwrite: 是否覆盖已存在的规则
    """
    _alert_manager.register_rule(rule, overwrite)


def register_alert_handler(channel: str, handler: Callable):
    """
    注册告警处理器的便捷函数

    参数:
        channel: 告警通道
        handler: 处理函数
    """
    _alert_manager.register_handler(channel, handler)


@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_server: str = "smtp.163.com"
    smtp_port: int = 465
    username: str = "imzfat@163.com"
    password: str = "VUnyu33GQ3guVmct"
    from_name: str = "VLogger 告警系统"
    to_emails: List[str] = field(default_factory=lambda: ["imzfat@163.com"])
    use_ssl: bool = True

    @classmethod
    def from_database(cls, db_path: str = "backend/sys_configs/system_config.db") -> "EmailConfig":
        """
        从统一配置数据库加载配置

        参数:
            db_path: 数据库文件路径

        返回:
            EmailConfig: 邮件配置对象
        """
        if not USE_UNIFIED_CONFIG:
            # 如果统一配置不可用，返回默认配置
            return cls()

        try:
            config_dict = get_email_config(db_path)
            return cls(**config_dict)
        except Exception as e:
            print(f"[EmailConfig] 从数据库加载配置失败: {str(e)}，使用默认配置")
            return cls()

    def save_to_database(self, db_path: str = "backend/sys_configs/system_config.db") -> bool:
        """
        保存配置到统一配置数据库

        参数:
            db_path: 数据库文件路径

        返回:
            bool: 保存是否成功
        """
        if not USE_UNIFIED_CONFIG:
            print("[EmailConfig] 统一配置管理器不可用")
            return False

        config_dict = {
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'username': self.username,
            'password': self.password,
            'from_name': self.from_name,
            'to_emails': self.to_emails,
            'use_ssl': self.use_ssl,
        }
        return save_email_config(config_dict, db_path)


class EmailSender:
    """邮件发送器"""

    def __init__(self, config: EmailConfig = None):
        """
        初始化邮件发送器

        参数:
            config: 邮件配置，如果为 None 则使用默认配置
        """
        self.config = config or EmailConfig()

    def send_alert_email(self, alert_level: AlertLevel, event_code: str,
                        message: str, extra: Dict[str, Any] = None) -> bool:
        """
        发送告警邮件

        参数:
            alert_level: 告警级别
            event_code: 事件码
            message: 告警消息
            extra: 额外信息

        返回:
            bool: 发送是否成功
        """
        try:
            # 构建邮件内容
            subject = self._build_subject(alert_level, event_code)
            body = self._build_body(alert_level, event_code, message, extra)

            # 使用通用邮件发送函数
            return email_send(
                smtp_server=self.config.smtp_server,
                smtp_port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                from_name=self.config.from_name,
                to_emails=self.config.to_emails,
                subject=subject,
                body_text=body['text'],
                body_html=body['html'],
                use_ssl=self.config.use_ssl
            )

        except Exception as e:
            print(f"发送告警邮件失败: {e}")
            return False

    def _build_subject(self, alert_level: AlertLevel, event_code: str) -> str:
        """构建邮件主题"""
        level_names = {
            AlertLevel.P0: "🚨 紧急告警",
            AlertLevel.P1: "⚠️ 高优先级告警",
            AlertLevel.P2: "📢 中优先级告警",
            AlertLevel.P3: "ℹ️ 低优先级告警"
        }

        level_name = level_names.get(alert_level, "告警")
        return f"[{level_name}] {event_code} - VLogger 系统告警"

    def _build_body(self, alert_level: AlertLevel, event_code: str,
                   message: str, extra: Dict[str, Any] = None) -> Dict[str, str]:
        """构建邮件正文（HTML 和纯文本格式）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extra = extra or {}

        # 纯文本格式
        text_body = f"""
VLogger 系统告警通知

告警级别: {alert_level.value}
事件码: {event_code}
告警消息: {message}
发生时间: {timestamp}

额外信息:
{json.dumps(extra, ensure_ascii=False, indent=2) if extra else '无'}

---
此邮件由 VLogger 告警系统自动发送
        """.strip()

        # HTML 格式
        level_colors = {
            AlertLevel.P0: "#dc3545",  # 红色
            AlertLevel.P1: "#fd7e14",  # 橙色
            AlertLevel.P2: "#ffc107",  # 黄色
            AlertLevel.P3: "#17a2b8"   # 蓝色
        }

        level_color = level_colors.get(alert_level, "#6c757d")

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: {level_color}; color: white; padding: 15px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .info-table {{ border-collapse: collapse; width: 100%; }}
        .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .info-table th {{ background-color: #f2f2f2; }}
        .extra-info {{ background-color: #f8f9fa; padding: 10px; border-radius: 3px; margin-top: 10px; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🚨 VLogger 系统告警通知</h2>
    </div>

    <div class="content">
        <table class="info-table">
            <tr>
                <th>告警级别</th>
                <td style="color: {level_color}; font-weight: bold;">{alert_level.value}</td>
            </tr>
            <tr>
                <th>事件码</th>
                <td>{event_code}</td>
            </tr>
            <tr>
                <th>告警消息</th>
                <td>{message}</td>
            </tr>
            <tr>
                <th>发生时间</th>
                <td>{timestamp}</td>
            </tr>
        </table>

        {f'<div class="extra-info"><strong>额外信息:</strong><br><pre>{json.dumps(extra, ensure_ascii=False, indent=2)}</pre></div>' if extra else ''}
    </div>

    <div class="footer">
        <hr>
        <p>此邮件由 VLogger 告警系统自动发送，请勿回复。</p>
    </div>
</body>
</html>
        """.strip()

        return {
            'text': text_body,
            'html': html_body
        }


# 全局邮件发送器实例
_email_sender = None


def setup_email_alerts(config: EmailConfig = None):
    """
    设置邮件告警功能

    参数:
        config: 邮件配置，如果为 None 则尝试从数据库加载，否则使用默认配置
    """
    global _email_sender

    # 如果没有提供配置，尝试从数据库加载
    if config is None and USE_UNIFIED_CONFIG:
        try:
            config = EmailConfig.from_database()
            print("[EmailConfig] 从统一配置数据库加载邮件配置")
        except Exception as e:
            print(f"[EmailConfig] 从数据库加载配置失败: {str(e)}，使用默认配置")
            config = EmailConfig()

    _email_sender = EmailSender(config)

    # 注册邮件处理器
    def email_handler(record: AlertRecord):
        """邮件告警处理器"""
        if record.level.should_send_email and _email_sender:
            return _email_sender.send_alert_email(record.level, record.event_code, record.message, record.extra)
        return True

    register_alert_handler("email", email_handler)


def send_test_alert(alert_level: AlertLevel = AlertLevel.P2):
    """
    发送测试告警邮件

    参数:
        alert_level: 告警级别
    """
    if not _email_sender:
        setup_email_alerts()

    test_message = f"这是一个 {alert_level.value} 级别的测试告警"
    test_extra = {
        "test_field": "测试数据",
        "timestamp": datetime.now().isoformat(),
        "system": "VLogger"
    }

    success = _email_sender.send_alert_email(
        alert_level=alert_level,
        event_code="EVT-TEST-EMAIL",
        message=test_message,
        extra=test_extra
    )

    if success:
        print(f"✓ 测试告警邮件发送成功 ({alert_level.value})")
    else:
        print(f"✗ 测试告警邮件发送失败 ({alert_level.value})")

    return success


# 自动设置默认邮件告警
setup_email_alerts()

