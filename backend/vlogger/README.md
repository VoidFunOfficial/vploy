# VLogger - 结构化日志模块

基于 loguru 实现的企业级结构化日志系统，专为高频交易和金融系统设计。

## 特性

- ✅ **6 级日志等级**：INFO, TRADE, WARN, ERROR, DEBUG, AUDIT
- ✅ **事件类型管理**：域.子域.动作命名规范，稳定的事件码体系
- ✅ **错误码体系**：统一的错误码前缀规范（E-AUTH-*, E-ORDER-* 等）
- ✅ **告警机制**：4 级严重性分级（P0-P3），去重、节流、智能合并
- ✅ **敏感信息脱敏**：自动识别并脱敏邮箱、手机、密钥、钱包地址等
- ✅ **全链路追踪**：trace_id 贯穿整个流程，支持跨服务传递
- ✅ **采样控制**：分级采样策略，高频路径低侵扰
- ✅ **结构化 JSON**：统一的 JSON Schema，易于检索和分析
- ✅ **灵活配置**：支持 JSON/YAML 配置文件，预定义环境模板

## 安装依赖

```bash
pip install loguru
```

## 快速开始

### 基础使用

```python
from vlogger import get_logger

# 创建日志记录器
logger = get_logger("strategy")

# 记录不同等级的日志
logger.info("SYS.STARTUP", msg="策略模块启动")
logger.trade("EXEC.ORDER.SUBMIT", msg="提交订单", extra={
    "order_id": "ORD-001",
    "symbol": "BTC-USD",
    "price": 45000.0
})
logger.warn("SYS.LATENCY_HIGH", msg="延迟过高", extra={"latency_ms": 150})
logger.error("EXEC.ORDER.REJECTED", msg="订单被拒绝", error_code="E-ORDER-003")
```

### 使用 TraceContext 进行全链路追踪

```python
from vlogger import get_logger, TraceContext

logger = get_logger("strategy")

# 使用 TraceContext 确保整个流程使用相同的 trace_id
with TraceContext() as trace_id:
    logger.info("STRATEGY.SIGNAL.GENERATED", msg="生成交易信号")
    logger.info("ROUTER.ROUTE.SELECTED", msg="选择交易路由")
    logger.trade("EXEC.ORDER.SUBMIT", msg="提交订单")
    logger.trade("EXEC.ORDER.FILLED", msg="订单成交")
```

## 日志等级

### 6 个日志等级

| 等级 | 用途 | 采样 | 留存 | 告警 |
|------|------|------|------|------|
| **INFO** | 正常状态与关键业务里程碑 | 可采样（默认 20%） | 30 天 | 否 |
| **TRADE** | 交易证据级流水 | **永不采样** | 180 天 | 否 |
| **WARN** | 可能影响收益或稳定性的异常 | 100% | 30 天 | 是（P2） |
| **ERROR** | 功能性失败 | 100% | 30 天 | 是（P1） |
| **DEBUG** | 调试细粒度信息 | 可采样（默认 0%） | 7 天 | 否 |
| **AUDIT** | 敏感操作审计 | **永不采样** | 180 天 | 否 |

### 使用示例

```python
logger.info("SYS.STARTUP", msg="系统启动")
logger.trade("EXEC.ORDER.FILLED", msg="订单成交", extra={"order_id": "001"})
logger.warn("SYS.LATENCY_HIGH", msg="延迟过高", error_code="E-SYS-008")
logger.error("EXEC.ORDER.REJECTED", msg="订单被拒绝", error_code="E-ORDER-002")
logger.debug("STRATEGY.SIGNAL.DETAIL", msg="信号详情", extra={"features": [...]})
logger.audit("AUDIT.AUTH.LOGIN", msg="用户登录", extra={"user_id": "12345"})
```

## 事件类型

### 命名规范

采用 **域.子域.动作** 格式（全大写），每个事件分配稳定的事件码（EVT-xxxx）。

### 预定义事件类型

| 事件码 | 事件名称 | 描述 |
|--------|----------|------|
| EVT-1001 | SYS.STARTUP | 系统启动 |
| EVT-1002 | SYS.SHUTDOWN | 系统关闭 |
| EVT-2001 | INGEST.MARKET.DISCOVERED | 发现新市场 |
| EVT-3001 | STRATEGY.SIGNAL.GENERATED | 生成交易信号 |
| EVT-5001 | EXEC.ORDER.SUBMIT | 提交订单 |
| EVT-5004 | EXEC.ORDER.FILLED | 订单成交 |
| EVT-6001 | RECON.STARTED | 对账开始 |
| EVT-7001 | AUDIT.AUTH.LOGIN | 用户登录 |

### 注册自定义事件

```python
from vlogger import register_event

register_event(
    code="EVT-9001",
    name="CUSTOM.ML.PREDICTION",
    description="机器学习模型预测",
    metadata={"model": "lstm", "version": "1.0"}
)

logger.info("CUSTOM.ML.PREDICTION", msg="模型预测完成")
```

## 错误码

### 错误码前缀体系

| 前缀 | 类别 | 示例 |
|------|------|------|
| E-AUTH-* | 认证/授权错误 | E-AUTH-001: 认证失败 |
| E-ORDER-* | 订单错误 | E-ORDER-003: 资金不足 |
| E-RATE-* | 速率限制错误 | E-RATE-429: 速率限制超出 |
| E-DATA-* | 数据错误 | E-DATA-001: 数据验证失败 |
| E-RECON-* | 对账错误 | E-RECON-001: 对账不平 |
| E-SYS-* | 系统错误 | E-SYS-001: 系统内部错误 |

### 注册自定义错误码

```python
from vlogger import register_error

register_error(
    code="E-ML-001",
    name="ML_MODEL_LOAD_FAILED",
    description="机器学习模型加载失败",
    severity="error"
)

logger.error("CUSTOM.ML.ERROR", msg="模型加载失败", error_code="E-ML-001")
```

## 告警机制

### 告警严重性分级

| 等级 | 处理方式 | 默认映射 |
|------|----------|----------|
| **P0** | 邮件即时推送 + 可选短信/电话 | 特定错误码（对账不平、系统崩溃等） |
| **P1** | 邮件即时推送 + 创建待办 | ERROR 级别日志 |
| **P2** | 邮件聚合推送（5-15 分钟批量） | WARN 级别日志 |
| **P3** | 仅在仪表盘标记，不发送邮件 | - |

### 去噪与抖动控制

- **去重窗口**：同一事件在 60 秒窗口内只发送一次告警
- **节流限制**：单个告警规则每分钟最多发送 2 封邮件
- **智能合并**：相同根因的告警合并为一封邮件

### 邮件告警功能

VLogger 内置了完整的邮件告警功能，支持 163 邮箱发送告警邮件。

#### 快速开始

```python
from vlogger import setup_email_alerts, send_test_alert, AlertLevel

# 使用默认配置设置邮件告警（163 邮箱）
setup_email_alerts()

# 发送测试邮件
send_test_alert(AlertLevel.P1)
```

#### 自定义邮件配置

```python
from vlogger import EmailConfig, setup_email_alerts

# 自定义邮件配置
config = EmailConfig(
    smtp_server="smtp.163.com",
    smtp_port=465,
    username="your_email@163.com",
    password="your_password",
    from_name="VLogger 告警系统",
    to_emails=["admin@company.com", "ops@company.com"],
    use_ssl=True
)

# 应用配置
setup_email_alerts(config)
```

#### 邮件告警触发

当日志记录触发告警规则时，系统会自动发送邮件：

```python
from vlogger import get_logger, register_alert_rule, AlertRule, AlertLevel

# 注册告警规则
register_alert_rule(AlertRule(
    event_code="E-ORDER-001",
    level=AlertLevel.P1,  # 高优先级，会发送邮件
    dedup_window_seconds=60,
    throttle_max_per_minute=2
))

logger = get_logger("order_mgr")

# 这条错误日志会触发邮件告警
logger.error("ORDER.SUBMIT.FAILED",
            msg="订单提交失败",
            error_code="E-ORDER-001",
            extra={"order_id": "12345", "reason": "资金不足"})
```

#### 邮件内容格式

邮件包含以下信息：
- **告警级别**：P0/P1/P2/P3 带颜色标识
- **事件码**：便于快速定位问题
- **告警消息**：详细描述
- **发生时间**：精确到秒
- **额外信息**：JSON 格式的上下文数据
- **HTML 格式**：美观的表格布局

### 自定义告警处理器

```python
from vlogger import register_alert_handler, register_alert_rule, AlertRule, AlertLevel

# 定义自定义告警处理器
def custom_handler(alert_level, event_code, message, extra=None):
    print(f"[自定义告警] {alert_level.value} - {message}")
    # 可以集成其他告警系统（钉钉、企业微信等）
    return True

# 注册告警处理器
register_alert_handler("custom", custom_handler)

# 注册自定义告警规则
register_alert_rule(AlertRule(
    event_code="E-RECON-001",
    level=AlertLevel.P0,  # 对账不平升级到 P0
    dedup_window_seconds=300,
    throttle_max_per_minute=1
))
```

## 敏感信息脱敏

### 自动脱敏

系统会自动识别并脱敏以下敏感信息：

- **邮箱地址**：`user@example.com` → `u***@example.com`
- **手机号码**：`13812345678` → `138****5678`
- **钱包地址**：`0x1234...abcd`
- **密钥/令牌**：完全掩码
- **密码**：完全掩码

### 使用示例

```python
from vlogger import get_logger
from vlogger.config import get_production_config

# 使用生产环境配置（启用脱敏）
config = get_production_config()
logger = get_logger(config=config)

# 记录包含敏感信息的日志（会自动脱敏）
logger.audit("AUDIT.AUTH.LOGIN", msg="用户登录", extra={
    "email": "user@example.com",  # 会被脱敏
    "api_key": "sk_live_1234567890abcdef",  # 会被脱敏
})
```

## 全链路追踪

### 使用 TraceContext

```python
from vlogger import get_logger, TraceContext

logger = get_logger("strategy")

# 自动生成 trace_id
with TraceContext() as trace_id:
    logger.info("STRATEGY.SIGNAL.GENERATED", msg="生成交易信号")
    process_order()  # 内部的日志会继承相同的 trace_id

# 使用已有的 trace_id
with TraceContext(trace_id="existing-trace-id"):
    logger.info("EXEC.ORDER.FILLED", msg="订单成交")
```

### 跨服务传递 trace_id

```python
from vlogger.trace import inject_trace_id_to_headers, extract_trace_id_from_headers

# 发送 HTTP 请求时注入 trace_id
headers = {"Content-Type": "application/json"}
headers = inject_trace_id_to_headers(headers)

# 接收 HTTP 请求时提取 trace_id
trace_id = extract_trace_id_from_headers(request.headers)
```

## 配置管理

### 预定义配置模板

```python
from vlogger.config import get_development_config, get_production_config, get_test_config

# 开发环境配置
dev_config = get_development_config()

# 生产环境配置
prod_config = get_production_config()

# 测试环境配置
test_config = get_test_config()

logger = get_logger(config=prod_config)
```

### 自定义配置

```python
from vlogger import LogConfig, get_logger

config = LogConfig(
    service_name="my_service",
    log_dir="./logs",
    enable_json=True,
    min_level="INFO",
    enable_sanitization=True,
    enable_alerts=True
)

# 设置采样率
config.set_sample_rate("INFO", 0.2)  # INFO 日志采样 20%
config.set_sample_rate("DEBUG", 0.0)  # DEBUG 日志完全关闭

logger = get_logger(config=config)
```

### 从配置文件加载

```python
from vlogger import LogConfig

# 保存配置到文件
config = LogConfig(service_name="example")
config.save_to_file("./config.json")

# 从文件加载配置
config = LogConfig.from_file("./config.json")
```

## 结构化日志 JSON Schema

每条日志包含以下字段：

```json
{
  "ts": "2025-01-09T12:34:56.789Z",
  "level": "TRADE",
  "event": "EXEC.ORDER.SUBMIT",
  "event_code": "EVT-5001",
  "trace_id": "TRC-20250109123456-a1b2c3d4e5f6",
  "service": "order_mgr",
  "msg": "提交订单",
  "extra": {
    "order_id": "ORD-001",
    "symbol": "BTC-USD",
    "price": 45000.0
  }
}
```

## 完整示例

查看 `examples.py` 文件获取更多详细示例。

运行示例：

```bash
cd backend/vlogger
python examples.py
```

## 最佳实践

1. **使用 TRADE 级别记录所有交易证据**：订单、成交、对账等
2. **使用 TraceContext 进行全链路追踪**：确保一次完整流程使用相同的 trace_id
3. **合理设置采样率**：高频路径（如市场数据更新）使用低采样率
4. **敏感信息脱敏**：生产环境务必启用脱敏功能
5. **自定义告警规则**：根据业务需求调整告警等级和去重策略

## 许可证

MIT License

