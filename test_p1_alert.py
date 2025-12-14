"""
测试 P1 级别错误码的邮件告警功能
"""

from backend.vlogger import get_logger, register_error, register_alert_rule, AlertRule, AlertLevel
from backend.sys_configs.global_event_reg import vlogger

# 测试1: 使用已注册的错误码（应该有告警规则）
print("=" * 60)
print("测试1: 使用已注册的 P1 错误码 E-FILTER-005")
print("=" * 60)

logger = get_logger("test_filter")
logger.error(
    event="FILTER.AI.ERROR",
    msg="AI 过滤调用失败 - 测试告警",
    error_code="E-FILTER-005",
    extra={"service": "ai_filter", "reason": "连接超时"}
)

print("\n等待 3 秒...\n")
import time
time.sleep(3)

# 测试2: 使用通用 ERROR 级别（应该触发默认 P1 规则）
print("=" * 60)
print("测试2: 使用通用 ERROR 级别（无 error_code）")
print("=" * 60)

logger.error(
    event="TEST.ERROR.EVENT",
    msg="这是一个测试错误 - 应该触发默认 P1 告警",
    extra={"test_id": "12345"}
)

print("\n等待 3 秒...\n")
time.sleep(3)

# 测试3: 检查告警规则是否存在
print("=" * 60)
print("测试3: 检查告警规则注册情况")
print("=" * 60)

from backend.vlogger.alerts import _alert_manager

# 检查 E-FILTER-005 的告警规则
rule_filter = _alert_manager.get_rule("E-FILTER-005")
print(f"E-FILTER-005 告警规则: {rule_filter}")

# 检查 ERROR 的默认告警规则
rule_error = _alert_manager.get_rule("ERROR")
print(f"ERROR 默认告警规则: {rule_error}")

# 检查邮件处理器是否注册
print(f"\n已注册的告警处理器: {list(_alert_manager._handlers.keys())}")
print(f"邮件处理器数量: {len(_alert_manager._handlers.get('email', []))}")

print("\n" + "=" * 60)
print("测试完成，请检查邮箱是否收到告警邮件")
print("=" * 60)

