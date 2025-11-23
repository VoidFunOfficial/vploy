"""
健康检查系统

基于 asyncio 实现的定时健康检查系统，支持：
- 每60秒自动执行一次健康检查
- 测试所有已配置的API端点网络延迟
- 使用 VLogger 记录检查结果
- 单例模式确保全局唯一实例
"""

from .health_check import (
    HealthChecker,
    EndpointType,
    HealthStatus,
    EndpointConfig,
    HealthCheckResult,
)

__all__ = [
    "HealthChecker",
    "EndpointType",
    "HealthStatus",
    "EndpointConfig",
    "HealthCheckResult",
]

