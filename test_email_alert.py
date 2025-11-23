"""
测试邮件告警功能
"""

from backend.vlogger import get_logger, register_error

# 注册测试错误码
register_error(
    code="E-FILTER-002138",
    name="过滤器调用失败",
    description="调用过滤器服务失败",
    severity="error"
)

# 获取 logger
logger = get_logger("filter")

# 测试 ERROR 级别日志（应该触发 P1 告警，发送邮件）
print("发送 ERROR 级别日志，应该触发邮件告警...")
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="WARN",
    extra={"service": "filter_service", "reason": "连接超时"}
)

print("日志已发送，请检查邮箱是否收到告警邮件")

