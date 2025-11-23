# VLogger 机制详解

## 一、核心概念

### 1. 日志等级 (LogLevel)
位置：`backend/vlogger/levels.py`

VLogger 定义了 6 个日志等级：

| 等级 | 用途 | 优先级 | 是否触发告警 | 默认采样率 |
|------|------|--------|-------------|-----------|
| **DEBUG** | 调试细粒度信息 | 10 | ❌ | 0% (默认关闭) |
| **INFO** | 正常状态与关键业务里程碑 | 20 | ❌ | 20% |
| **WARN** | 可能影响收益或稳定性的异常 | 30 | ✅ | 100% |
| **ERROR** | 功能性失败 | 40 | ✅ | 100% |
| **TRADE** | 交易证据级流水（永不采样） | 50 | ❌ | 100% |
| **AUDIT** | 敏感操作审计（不走告警通道） | 45 | ❌ | 100% |

**关键属性：**
- `should_alert`: 只有 **WARN** 和 **ERROR** 会触发告警
- `can_sample`: TRADE 和 AUDIT 永不采样，必须 100% 记录
- `retention_days`: TRADE 和 AUDIT 保留 180 天，其他 7-30 天

---

## 二、事件码系统 (EventCode)
位置：`backend/vlogger/events.py`

### 事件码命名规范
- **格式**: `EVT-xxxx` (如 EVT-5001)
- **事件名称**: `域.子域.动作` (全大写，如 `EXEC.ORDER.SUBMIT`)

### 预定义事件分类

| 事件码范围 | 分类 | 示例 |
|-----------|------|------|
| EVT-1xxx | 系统事件 | EVT-1001 (SYS.STARTUP) |
| EVT-2xxx | 数据采集事件 | EVT-2001 (INGEST.MARKET.DISCOVERED) |
| EVT-3xxx | 策略事件 | EVT-3001 (STRATEGY.SIGNAL.GENERATED) |
| EVT-4xxx | 路由事件 | EVT-4001 (ROUTER.ROUTE.SELECTED) |
| EVT-5xxx | 订单执行事件 | EVT-5001 (EXEC.ORDER.SUBMIT) |
| EVT-6xxx | 对账事件 | EVT-6001 (RECON.STARTED) |
| EVT-7xxx | 审计事件 | EVT-7001 (AUDIT.AUTH.LOGIN) |
| EVT-8xxx | 过滤器事件 | EVT-8001 (FILTER.INIT) |

### 使用方式
```python
from vlogger import register_event, get_event

# 注册自定义事件
register_event(
    code="EVT-9001",
    name="CUSTOM.ACTION.START",
    description="自定义动作开始",
    metadata={"category": "custom"}
)

# 使用事件（可以用事件码或事件名称）
logger.info("EVT-9001", msg="开始执行自定义动作")
logger.info("CUSTOM.ACTION.START", msg="开始执行自定义动作")
```

---

## 三、错误码系统 (ErrorCode)
位置：`backend/vlogger/errors.py`

### 错误码命名规范
- **格式**: `E-<模块>-<序号>` (如 E-AUTH-001)

### 预定义错误码分类

| 前缀 | 分类 | 示例 |
|------|------|------|
| E-AUTH-* | 认证/授权错误 | E-AUTH-001 (认证失败) |
| E-ORDER-* | 订单错误 | E-ORDER-001 (订单提交失败) |
| E-RATE-* | 速率限制错误 | E-RATE-001 (超过速率限制) |
| E-DATA-* | 数据验证/解析错误 | E-DATA-001 (数据格式错误) |
| E-RECON-* | 对账错误 | E-RECON-001 (对账不平) |
| E-SYS-* | 系统级错误 | E-SYS-001 (系统内部错误) |
| E-FILTER-* | 过滤器错误 | E-FILTER-001 (过滤器初始化失败) |

### 使用方式
```python
from vlogger import register_error

# 注册自定义错误码
register_error(
    code="E-FILTER-008",
    name="过滤器调用失败",
    description="调用过滤器服务失败",
    severity="error"
)

# 使用错误码
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="E-FILTER-008",  # 这里传入错误码
    extra={"service": "filter_service"}
)
```

---

## 四、告警机制 (Alert System)
位置：`backend/vlogger/alerts.py`

### 4.1 告警等级 (AlertLevel)

| 等级 | 处理方式 | 是否发邮件 | 是否发短信 | 批量间隔 |
|------|---------|-----------|-----------|---------|
| **P0** | 立即处理 | ✅ | ✅ | 立即 |
| **P1** | 高优先级 | ✅ | ❌ | 立即 |
| **P2** | 中优先级 | ✅ | ❌ | 5分钟批量 |
| **P3** | 低优先级 | ❌ | ❌ | 仅仪表盘 |

### 4.2 告警规则 (AlertRule)

**规则结构：**
```python
@dataclass
class AlertRule:
    event_code: str                    # 事件码或错误码
    level: AlertLevel                  # 告警等级
    dedup_window_seconds: int = 60     # 去重窗口（秒）
    throttle_max_per_minute: int = 2   # 每分钟最大告警数
    merge_by_fields: List[str] = []    # 合并告警的字段
    enabled: bool = True               # 是否启用
```

### 4.3 默认告警规则

系统在初始化时自动注册以下默认规则：

```python
# 1. WARN 级别 → P2 告警（中优先级，邮件聚合）
AlertRule(
    event_code="WARN",
    level=AlertLevel.P2,
    dedup_window_seconds=60,
    throttle_max_per_minute=2
)

# 2. ERROR 级别 → P1 告警（高优先级，邮件即时）
AlertRule(
    event_code="ERROR",
    level=AlertLevel.P1,
    dedup_window_seconds=60,
    throttle_max_per_minute=2
)

# 3. 特定错误码 → P0 告警（紧急，邮件+短信）
critical_errors = [
    "E-SYS-001",   # 系统内部错误
    "E-SYS-004",   # 数据库错误
    "E-SYS-009",   # 资源耗尽
    "E-RECON-001", # 对账不平
]
```

### 4.4 告警触发流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 用户调用 logger.error() 或 logger.warn()                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. VLogger._log() 检查 level.should_alert                    │
│    - WARN/ERROR: should_alert = True                        │
│    - 其他等级: should_alert = False (不触发告警)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 确定 alert_code                                           │
│    alert_code = error_code or event                         │
│    - 如果有 error_code，用 error_code                        │
│    - 否则用 event                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. AlertManager.send_alert(alert_code, msg, extra)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. AlertManager.should_alert() 判断是否发送                  │
│    a) 查找告警规则 (按 alert_code 精确匹配)                  │
│    b) 如果没有规则 → 不发送告警                              │
│    c) 检查去重窗口 (dedup_window_seconds)                    │
│    d) 检查节流限制 (throttle_max_per_minute)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 调用告警处理器                                            │
│    - 如果 level.should_send_email → 调用邮件处理器           │
│    - 如果 level.should_send_sms → 调用短信处理器             │
│    - 总是调用仪表盘处理器                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、关键问题解析

### 问题 1: 为什么 `logger.error(..., error_code="E-FILTER-008")` 没有触发邮件？

**原因分析：**

1. **告警规则匹配机制**：
   - 系统使用 `alert_code` 来查找告警规则
   - `alert_code = error_code or event`
   - 如果你传了 `error_code="E-FILTER-008"`，则 `alert_code = "E-FILTER-008"`

2. **默认规则只有这些**：
   ```python
   "WARN"         → P2
   "ERROR"        → P1
   "E-SYS-001"    → P0
   "E-SYS-004"    → P0
   "E-SYS-009"    → P0
   "E-RECON-001"  → P0
   ```

3. **你的 error_code 没有对应规则**：
   - `"E-FILTER-008"` 不在默认规则中
   - 系统找不到规则 → `should_alert()` 返回 `(False, None)`
   - 不发送告警

### 解决方案

**方案 1: 不传 error_code，让系统使用默认 ERROR 规则**
```python
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    # 不传 error_code，alert_code 会是 "FILTER.CALL.FAILED"
    # 但这个也没有规则...
)
```

**方案 2: 传 error_code="ERROR"，使用默认 ERROR 规则** ✅ **推荐**
```python
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="ERROR",  # 使用默认 ERROR 规则 → P1 告警
    extra={"real_error": "E-FILTER-008"}
)
```

**方案 3: 为 E-FILTER-008 注册专门的告警规则**
```python
from vlogger import register_alert_rule, AlertRule, AlertLevel

# 注册规则
register_alert_rule(AlertRule(
    event_code="E-FILTER-008",
    level=AlertLevel.P1,  # 高优先级
    dedup_window_seconds=60,
    throttle_max_per_minute=2
))

# 然后使用
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="E-FILTER-008",  # 现在有规则了
)
```

**方案 4: 为所有 E-FILTER-* 错误注册规则**
```python
# 批量注册过滤器错误规则
filter_errors = [
    "E-FILTER-001", "E-FILTER-002", "E-FILTER-003",
    "E-FILTER-004", "E-FILTER-005", "E-FILTER-006",
    "E-FILTER-007", "E-FILTER-008",
]

for error_code in filter_errors:
    register_alert_rule(AlertRule(
        event_code=error_code,
        level=AlertLevel.P1,
        dedup_window_seconds=60,
        throttle_max_per_minute=2
    ))
```

---

## 六、最佳实践

### 1. 日志记录最佳实践

```python
# ✅ 推荐：使用预定义事件码
logger.info("EVT-8001", msg="过滤器初始化完成")

# ✅ 推荐：ERROR 日志使用 error_code="ERROR" 触发默认告警
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="ERROR",  # 触发 P1 告警
    extra={"service": "filter", "reason": "timeout"}
)

# ✅ 推荐：特定错误码需要先注册规则
register_alert_rule(AlertRule(
    event_code="E-FILTER-CRITICAL",
    level=AlertLevel.P0  # 紧急告警
))
logger.error(
    event="FILTER.CRITICAL.ERROR",
    msg="过滤器严重错误",
    error_code="E-FILTER-CRITICAL"
)

# ❌ 不推荐：使用未注册规则的 error_code（不会触发告警）
logger.error(
    event="SOMETHING",
    msg="错误",
    error_code="E-UNKNOWN-999"  # 没有规则，不会告警
)
```

### 2. 告警规则设计原则

1. **使用默认规则**：大部分场景用 "ERROR" 和 "WARN" 就够了
2. **关键错误升级**：对账不平、系统崩溃等升级到 P0
3. **避免告警风暴**：合理设置 `dedup_window_seconds` 和 `throttle_max_per_minute`
4. **分级响应**：
   - P0: 立即处理（5分钟内）
   - P1: 1小时内处理
   - P2: 当天处理
   - P3: 仅记录

### 3. 配置管理

```python
from vlogger import LogConfig, get_logger

# 开发环境：关闭告警
dev_config = LogConfig(
    service_name="my_service",
    enable_alerts=False,  # 开发环境不告警
    enable_sanitization=False
)

# 生产环境：启用告警
prod_config = LogConfig(
    service_name="my_service",
    enable_alerts=True,  # 生产环境启用告警
    enable_sanitization=True
)

logger = get_logger(config=prod_config)
```

---

## 七、完整示例

```python
from vlogger import (
    get_logger,
    register_error,
    register_alert_rule,
    AlertRule,
    AlertLevel
)

# 1. 注册错误码
register_error(
    code="E-FILTER-008",
    name="过滤器调用失败",
    description="调用过滤器服务失败",
    severity="error"
)

# 2. 注册告警规则（可选，如果想要特定告警级别）
register_alert_rule(AlertRule(
    event_code="E-FILTER-008",
    level=AlertLevel.P1,  # 高优先级
    dedup_window_seconds=60,
    throttle_max_per_minute=2
))

# 3. 获取 logger
logger = get_logger("filter")

# 4. 记录日志（会触发 P1 告警，发送邮件）
logger.error(
    event="FILTER.CALL.FAILED",
    msg="调用失败",
    error_code="E-FILTER-008",  # 现在有规则了
    extra={"service": "filter_service", "reason": "连接超时"}
)
```

