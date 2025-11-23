"""
错误码管理

提供统一的错误码注册、查询和管理功能。
错误码前缀体系：
- E-AUTH-*: 认证/授权相关错误
- E-ORDER-*: 订单相关错误
- E-RATE-*: 速率限制相关错误
- E-DATA-*: 数据验证/解析错误
- E-RECON-*: 对账相关错误
- E-SYS-*: 系统级错误
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from threading import Lock


@dataclass
class ErrorCode:
    """
    错误码定义
    
    属性:
        code: 错误码，如 E-AUTH-001
        name: 错误名称
        description: 错误描述
        severity: 严重程度（info, warning, error, critical）
        metadata: 额外的元数据
    """
    code: str
    name: str
    description: str
    severity: str = "error"
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "metadata": self.metadata or {},
        }


class ErrorRegistry:
    """
    错误码注册表
    
    提供错误码的注册、查询和管理功能。
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
        """初始化错误码注册表"""
        if self._initialized:
            return
        
        self._errors: Dict[str, ErrorCode] = {}
        self._lock = Lock()
        self._initialized = True
        
        # 注册预定义的错误码
        self._register_default_errors()
    
    def _register_default_errors(self):
        """注册默认的错误码"""
        default_errors = [
            # 认证/授权错误 (E-AUTH-*)
            ErrorCode("E-AUTH-001", "AUTH_FAILED", "认证失败", "error"),
            ErrorCode("E-AUTH-002", "AUTH_EXPIRED", "认证过期", "warning"),
            ErrorCode("E-AUTH-003", "AUTH_INVALID_TOKEN", "无效的令牌", "error"),
            ErrorCode("E-AUTH-004", "AUTH_PERMISSION_DENIED", "权限不足", "error"),
            ErrorCode("E-AUTH-005", "AUTH_KEY_INVALID", "API 密钥无效", "error"),
            
            # 订单错误 (E-ORDER-*)
            ErrorCode("E-ORDER-001", "ORDER_SUBMIT_FAILED", "订单提交失败", "error"),
            ErrorCode("E-ORDER-002", "ORDER_REJECTED", "订单被拒绝", "warning"),
            ErrorCode("E-ORDER-003", "ORDER_INSUFFICIENT_FUNDS", "资金不足", "error"),
            ErrorCode("E-ORDER-004", "ORDER_INSUFFICIENT_AUTH", "授权额度不足", "error"),
            ErrorCode("E-ORDER-005", "ORDER_INVALID_PARAMS", "订单参数无效", "error"),
            ErrorCode("E-ORDER-006", "ORDER_FOK_FAILED", "FOK 订单未成交", "warning"),
            ErrorCode("E-ORDER-007", "ORDER_CANCEL_FAILED", "订单取消失败", "error"),
            ErrorCode("E-ORDER-008", "ORDER_NOT_FOUND", "订单不存在", "warning"),
            ErrorCode("E-ORDER-009", "ORDER_DUPLICATE", "重复订单", "warning"),
            
            # 速率限制错误 (E-RATE-*)
            ErrorCode("E-RATE-429", "RATE_LIMIT_EXCEEDED", "速率限制超出", "warning"),
            ErrorCode("E-RATE-001", "RATE_LIMIT_ORDER", "订单速率限制", "warning"),
            ErrorCode("E-RATE-002", "RATE_LIMIT_API", "API 速率限制", "warning"),
            ErrorCode("E-RATE-003", "RATE_LIMIT_WS", "WebSocket 速率限制", "warning"),
            
            # 数据错误 (E-DATA-*)
            ErrorCode("E-DATA-001", "DATA_VALIDATION_FAILED", "数据验证失败", "error"),
            ErrorCode("E-DATA-002", "DATA_PARSE_FAILED", "数据解析失败", "error"),
            ErrorCode("E-DATA-003", "DATA_MISSING_FIELD", "缺少必需字段", "error"),
            ErrorCode("E-DATA-004", "DATA_INVALID_FORMAT", "数据格式无效", "error"),
            ErrorCode("E-DATA-005", "DATA_OUT_OF_RANGE", "数据超出范围", "error"),
            ErrorCode("E-DATA-006", "DATA_CHECKSUM_FAILED", "数据校验和失败", "error"),
            
            # 对账错误 (E-RECON-*)
            ErrorCode("E-RECON-001", "RECON_MISMATCH", "对账不平", "error"),
            ErrorCode("E-RECON-002", "RECON_POSITION_MISMATCH", "仓位不匹配", "error"),
            ErrorCode("E-RECON-003", "RECON_BALANCE_MISMATCH", "余额不匹配", "error"),
            ErrorCode("E-RECON-004", "RECON_TRADE_MISSING", "交易记录缺失", "error"),
            ErrorCode("E-RECON-005", "RECON_TIMEOUT", "对账超时", "warning"),
            
            # 系统错误 (E-SYS-*)
            ErrorCode("E-SYS-001", "SYS_INTERNAL_ERROR", "系统内部错误", "critical"),
            ErrorCode("E-SYS-002", "SYS_NETWORK_ERROR", "网络错误", "error"),
            ErrorCode("E-SYS-003", "SYS_TIMEOUT", "系统超时", "warning"),
            ErrorCode("E-SYS-004", "SYS_DB_ERROR", "数据库错误", "critical"),
            ErrorCode("E-SYS-005", "SYS_CONFIG_ERROR", "配置错误", "error"),
            ErrorCode("E-SYS-006", "SYS_WS_DISCONNECTED", "WebSocket 断开", "warning"),
            ErrorCode("E-SYS-007", "SYS_WS_RECONNECT_FAILED", "WebSocket 重连失败", "error"),
            ErrorCode("E-SYS-008", "SYS_LATENCY_HIGH", "延迟过高", "warning"),
            ErrorCode("E-SYS-009", "SYS_RESOURCE_EXHAUSTED", "资源耗尽", "critical"),

            # 过滤器错误 (E-FILTER-*)
            ErrorCode("E-FILTER-001", "FILTER_DB_QUERY_ERROR", "数据库查询错误", "error"),
            ErrorCode("E-FILTER-002", "FILTER_DB_UPDATE_ERROR", "数据库更新错误", "error"),
            ErrorCode("E-FILTER-003", "FILTER_DB_INIT_ERROR", "数据库初始化错误", "critical"),
            ErrorCode("E-FILTER-004", "FILTER_DB_INSERT_ERROR", "数据库插入错误", "error"),
            ErrorCode("E-FILTER-005", "FILTER_BLACKLIST_ADD_ERROR", "添加黑名单配置项失败", "error"),
            ErrorCode("E-FILTER-006", "FILTER_BLACKLIST_REMOVE_ERROR", "删除黑名单配置项失败", "error"),
            ErrorCode("E-FILTER-007", "FILTER_BLACKLIST_UPDATE_ERROR", "更新黑名单配置项失败", "error"),
            ErrorCode("E-FILTER-008", "FILTER_PROCESSED_CHECK_ERROR", "检查市场处理状态失败", "error"),
            ErrorCode("E-FILTER-009", "FILTER_PROCESSED_MARK_ERROR", "标记市场失败", "error"),
            ErrorCode("E-FILTER-010", "FILTER_PROCESSED_CLEAR_ERROR", "清理已处理市场记录失败", "error"),
        ]
        
        for error in default_errors:
            self._errors[error.code] = error
    
    def register(
        self,
        code: str,
        name: str,
        description: str,
        severity: str = "error",
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> ErrorCode:
        """
        注册新的错误码
        
        参数:
            code: 错误码，如 E-AUTH-001
            name: 错误名称
            description: 错误描述
            severity: 严重程度（info, warning, error, critical）
            metadata: 额外的元数据
            overwrite: 是否覆盖已存在的错误码
            
        返回:
            ErrorCode: 注册的错误码对象
            
        异常:
            ValueError: 如果错误码已存在且 overwrite=False
        """
        with self._lock:
            if not overwrite and code in self._errors:
                raise ValueError(f"错误码 {code} 已存在")
            
            if severity not in ("info", "warning", "error", "critical"):
                raise ValueError(f"无效的严重程度: {severity}")
            
            error = ErrorCode(code, name, description, severity, metadata)
            self._errors[code] = error
            
            return error
    
    def get(self, code: str) -> Optional[ErrorCode]:
        """
        根据错误码获取错误信息
        
        参数:
            code: 错误码
            
        返回:
            ErrorCode: 错误码对象，如果不存在则返回 None
        """
        return self._errors.get(code)
    
    def exists(self, code: str) -> bool:
        """
        检查错误码是否存在
        
        参数:
            code: 错误码
            
        返回:
            bool: 如果存在返回 True
        """
        return code in self._errors
    
    def list_all(self) -> Dict[str, ErrorCode]:
        """
        列出所有已注册的错误码
        
        返回:
            dict: 错误码到 ErrorCode 对象的映射
        """
        return self._errors.copy()
    
    def list_by_prefix(self, prefix: str) -> Dict[str, ErrorCode]:
        """
        根据错误码前缀列出错误
        
        参数:
            prefix: 错误码前缀，如 "E-AUTH"
            
        返回:
            dict: 匹配的错误码到 ErrorCode 对象的映射
        """
        return {
            code: error
            for code, error in self._errors.items()
            if code.startswith(prefix)
        }
    
    def list_by_severity(self, severity: str) -> Dict[str, ErrorCode]:
        """
        根据严重程度列出错误
        
        参数:
            severity: 严重程度（info, warning, error, critical）
            
        返回:
            dict: 匹配的错误码到 ErrorCode 对象的映射
        """
        return {
            code: error
            for code, error in self._errors.items()
            if error.severity == severity
        }
    
    def unregister(self, code: str) -> bool:
        """
        注销错误码
        
        参数:
            code: 错误码
            
        返回:
            bool: 如果成功注销返回 True
        """
        with self._lock:
            return self._errors.pop(code, None) is not None


# 全局错误码注册表实例
_error_registry = ErrorRegistry()


def register_error(
    code: str,
    name: str,
    description: str,
    severity: str = "error",
    metadata: Optional[Dict[str, Any]] = None,
    overwrite: bool = False
) -> ErrorCode:
    """
    注册错误码的便捷函数
    
    参数:
        code: 错误码
        name: 错误名称
        description: 错误描述
        severity: 严重程度
        metadata: 额外的元数据
        overwrite: 是否覆盖已存在的错误码
        
    返回:
        ErrorCode: 注册的错误码对象
    """
    return _error_registry.register(code, name, description, severity, metadata, overwrite)


def get_error(code: str) -> Optional[ErrorCode]:
    """
    获取错误码的便捷函数
    
    参数:
        code: 错误码
        
    返回:
        ErrorCode: 错误码对象，如果不存在则返回 None
    """
    return _error_registry.get(code)

