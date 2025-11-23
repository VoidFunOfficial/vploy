"""
Trace ID 管理

提供全链路追踪 ID 的生成、传递和管理功能。
支持跨服务、跨进程的 trace_id 传递。
"""

import uuid
import contextvars
from typing import Optional
from datetime import datetime


# 使用 contextvars 实现线程安全的上下文变量
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'trace_id', default=None
)


def generate_trace_id(prefix: str = "TRC") -> str:
    """
    生成新的 trace_id
    
    格式: {prefix}-{timestamp}-{uuid}
    例如: TRC-20250109123456-a1b2c3d4e5f6
    
    参数:
        prefix: trace_id 前缀，默认为 "TRC"
        
    返回:
        str: 生成的 trace_id
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:12]
    return f"{prefix}-{timestamp}-{unique_id}"


def set_trace_id(trace_id: str) -> str:
    """
    设置当前上下文的 trace_id
    
    参数:
        trace_id: 要设置的 trace_id
        
    返回:
        str: 设置的 trace_id
    """
    _trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> Optional[str]:
    """
    获取当前上下文的 trace_id
    
    返回:
        str: 当前的 trace_id，如果未设置则返回 None
    """
    return _trace_id_var.get()


def get_or_create_trace_id(prefix: str = "TRC") -> str:
    """
    获取当前上下文的 trace_id，如果不存在则创建新的
    
    参数:
        prefix: trace_id 前缀，默认为 "TRC"
        
    返回:
        str: trace_id
    """
    trace_id = get_trace_id()
    if trace_id is None:
        trace_id = generate_trace_id(prefix)
        set_trace_id(trace_id)
    return trace_id


def clear_trace_id():
    """清除当前上下文的 trace_id"""
    _trace_id_var.set(None)


class TraceContext:
    """
    Trace 上下文管理器
    
    用于在代码块中设置和管理 trace_id。
    支持嵌套使用，内层会继承外层的 trace_id。
    
    使用示例:
        >>> with TraceContext() as trace_id:
        ...     # 在这个代码块中，所有日志都会使用相同的 trace_id
        ...     logger.info("EXEC.ORDER.SUBMIT", msg="提交订单")
        ...     process_order()
        
        >>> # 使用已有的 trace_id
        >>> with TraceContext(trace_id="existing-trace-id"):
        ...     logger.info("EXEC.ORDER.FILLED", msg="订单成交")
    """
    
    def __init__(self, trace_id: Optional[str] = None, prefix: str = "TRC"):
        """
        初始化 Trace 上下文
        
        参数:
            trace_id: 指定的 trace_id，如果为 None 则自动生成
            prefix: trace_id 前缀，仅在自动生成时使用
        """
        self.trace_id = trace_id
        self.prefix = prefix
        self._previous_trace_id: Optional[str] = None
    
    def __enter__(self) -> str:
        """进入上下文时设置 trace_id"""
        # 保存之前的 trace_id
        self._previous_trace_id = get_trace_id()
        
        # 如果没有指定 trace_id，则生成新的或继承父级的
        if self.trace_id is None:
            if self._previous_trace_id is not None:
                # 继承父级的 trace_id
                self.trace_id = self._previous_trace_id
            else:
                # 生成新的 trace_id
                self.trace_id = generate_trace_id(self.prefix)
        
        # 设置当前的 trace_id
        set_trace_id(self.trace_id)
        return self.trace_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时恢复之前的 trace_id"""
        # 恢复之前的 trace_id
        if self._previous_trace_id is not None:
            set_trace_id(self._previous_trace_id)
        else:
            clear_trace_id()


class TraceIdGenerator:
    """
    Trace ID 生成器
    
    支持自定义前缀和格式的 trace_id 生成。
    """
    
    def __init__(self, prefix: str = "TRC", include_timestamp: bool = True):
        """
        初始化生成器
        
        参数:
            prefix: trace_id 前缀
            include_timestamp: 是否包含时间戳
        """
        self.prefix = prefix
        self.include_timestamp = include_timestamp
    
    def generate(self) -> str:
        """
        生成 trace_id
        
        返回:
            str: 生成的 trace_id
        """
        if self.include_timestamp:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex[:12]
            return f"{self.prefix}-{timestamp}-{unique_id}"
        else:
            unique_id = uuid.uuid4().hex
            return f"{self.prefix}-{unique_id}"
    
    def __call__(self) -> str:
        """使生成器可调用"""
        return self.generate()


def extract_trace_id_from_headers(headers: dict, header_name: str = "X-Trace-ID") -> Optional[str]:
    """
    从 HTTP 请求头中提取 trace_id
    
    参数:
        headers: HTTP 请求头字典
        header_name: trace_id 所在的请求头名称
        
    返回:
        str: 提取的 trace_id，如果不存在则返回 None
    """
    # 支持大小写不敏感的查找
    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value
    return None


def inject_trace_id_to_headers(
    headers: dict,
    trace_id: Optional[str] = None,
    header_name: str = "X-Trace-ID"
) -> dict:
    """
    将 trace_id 注入到 HTTP 请求头中
    
    参数:
        headers: HTTP 请求头字典
        trace_id: 要注入的 trace_id，如果为 None 则使用当前上下文的 trace_id
        header_name: trace_id 所在的请求头名称
        
    返回:
        dict: 注入 trace_id 后的请求头字典
    """
    if trace_id is None:
        trace_id = get_or_create_trace_id()
    
    headers = headers.copy()
    headers[header_name] = trace_id
    return headers


def create_child_trace_id(parent_trace_id: str, child_suffix: Optional[str] = None) -> str:
    """
    创建子 trace_id
    
    用于在分布式系统中创建具有父子关系的 trace_id。
    格式: {parent_trace_id}.{child_suffix}
    
    参数:
        parent_trace_id: 父 trace_id
        child_suffix: 子 trace_id 后缀，如果为 None 则自动生成
        
    返回:
        str: 子 trace_id
    """
    if child_suffix is None:
        child_suffix = uuid.uuid4().hex[:8]
    return f"{parent_trace_id}.{child_suffix}"


def parse_trace_id(trace_id: str) -> dict:
    """
    解析 trace_id
    
    参数:
        trace_id: 要解析的 trace_id
        
    返回:
        dict: 包含 prefix, timestamp, unique_id 等信息的字典
    """
    parts = trace_id.split("-")
    result = {"raw": trace_id}
    
    if len(parts) >= 1:
        result["prefix"] = parts[0]
    if len(parts) >= 2:
        result["timestamp"] = parts[1]
    if len(parts) >= 3:
        result["unique_id"] = parts[2]
    
    # 检查是否是子 trace_id
    if "." in trace_id:
        parent_child = trace_id.rsplit(".", 1)
        result["parent_trace_id"] = parent_child[0]
        result["child_suffix"] = parent_child[1]
    
    return result

