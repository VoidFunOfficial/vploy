# TokenRefresher - Token 刷新管理器

## 概述

TokenRefresher 是一个自动化的 token 过期检查和告警系统，专为管理多种类型的 API token 和认证凭证而设计。

## 核心功能

### 1. 多 Token 类型管理
- **coze_token**: Coze API Token，30天有效期
- **auth_token**: 认证 Token，7天有效期
- **access_token**: 访问 Token，1天有效期
- 支持添加自定义 token 类型

### 2. 自动过期检查
- 默认每 10 分钟检查一次所有 token 的过期状态
- 检查间隔可通过配置动态调整
- 使用后台守护线程，不阻塞主程序

### 3. 智能告警机制
- 集成 VLogger 日志系统
- 检测到 token 过期时自动发送 P1 级别告警
- 通过邮件即时推送告警信息（163邮箱）
- 支持手动标记 token 为过期并立即告警

### 4. 数据持久化
- 使用 SQLite 数据库存储 token 配置和状态
- 集成 SysConfig 统一配置管理系统
- 记录 token 值、过期时间、最后检查时间等信息

### 5. 可扩展设计
- 支持动态添加新的 token 类型
- 每个 token 类型可单独配置有效期
- 灵活的配置管理接口

## 快速开始

### 基础使用

```python
from backend.sys_configs import get_token_refresher, TokenType

# 获取 TokenRefresher 实例（单例模式）
refresher = get_token_refresher(
    check_interval_minutes=10,  # 每 10 分钟检查一次
    auto_start=True  # 自动启动后台检查线程
)

# 更新 token（自动计算过期时间）
refresher.update_token(
    token_type=TokenType.COZE_TOKEN.value,
    token_value="your_coze_token_here"
)

refresher.update_token(
    token_type=TokenType.AUTH_TOKEN.value,
    token_value="your_auth_token_here"
)

refresher.update_token(
    token_type=TokenType.ACCESS_TOKEN.value,
    token_value="your_access_token_here"
)
```

### 自定义过期时间

```python
from datetime import datetime, timedelta

# 手动指定过期时间
custom_expiry = datetime.now() + timedelta(days=15)
refresher.update_token(
    token_type=TokenType.COZE_TOKEN.value,
    token_value="your_token",
    expires_at=custom_expiry
)
```

### 添加自定义 Token 类型

```python
# 添加新的 token 类型
refresher.add_token_type(
    token_type="api_key",
    validity_days=90,  # 90天有效期
    description="第三方 API 密钥"
)

# 更新新类型的 token
refresher.update_token(
    token_type="api_key",
    token_value="sk-1234567890abcdef"
)
```

## API 参考

### TokenRefresher 类

#### 初始化

```python
TokenRefresher(
    db_path: str = "backend/sys_configs/system_config.db",
    check_interval_minutes: int = 10,
    auto_start: bool = True
)
```

**参数:**
- `db_path`: 数据库文件路径
- `check_interval_minutes`: 检查间隔（分钟）
- `auto_start`: 是否自动启动后台检查线程

#### 主要方法

##### update_token()
更新 token 信息

```python
refresher.update_token(
    token_type: str,
    token_value: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> bool
```

**参数:**
- `token_type`: Token 类型
- `token_value`: Token 值（可选）
- `expires_at`: 过期时间（可选，不提供则自动计算）

**返回:** 更新是否成功

##### get_token_status()
获取单个 token 的状态

```python
status = refresher.get_token_status(token_type: str) -> Optional[Dict[str, Any]]
```

**返回字典包含:**
- `token_type`: Token 类型
- `token_value`: Token 值
- `expires_at`: 过期时间
- `is_expired`: 是否已过期
- `last_checked_at`: 最后检查时间

##### get_all_token_status()
获取所有 token 的状态

```python
all_status = refresher.get_all_token_status() -> Dict[str, Dict[str, Any]]
```

##### check_all_tokens()
手动检查所有 token 的过期状态

```python
result = refresher.check_all_tokens() -> Dict[str, bool]
```

**返回:** `{token_type: is_expired}` 字典

##### set_expired_immediate()
立即将 token 标记为过期并发送告警

```python
refresher.set_expired_immediate(token_type: str) -> bool
```

##### add_token_type()
添加新的 token 类型配置

```python
refresher.add_token_type(
    token_type: str,
    validity_days: int,
    description: str = ""
) -> bool
```

##### set_check_interval()
设置检查间隔

```python
refresher.set_check_interval(minutes: int) -> bool
```

##### start() / stop()
启动/停止后台检查线程

```python
refresher.start()
refresher.stop()
```

##### is_running()
检查后台线程是否正在运行

```python
is_running = refresher.is_running() -> bool
```

## 告警机制

### 告警触发条件
1. 定期检查发现 token 已过期
2. 手动调用 `set_expired_immediate()` 标记 token 为过期

### 告警级别
- **P1 级别**: 邮件即时推送
- 使用 VLogger 的 ERROR 级别日志
- 错误码: `E-TOKEN-001`

### 告警内容
- Token 类型和描述
- 过期时间
- 是否为手动标记过期

### 邮件配置
告警邮件通过 VLogger 的邮件系统发送，配置方式：

```python
from backend.vlogger import setup_email_alerts, EmailConfig

# 使用默认配置（163邮箱）
setup_email_alerts()

# 或自定义配置
config = EmailConfig(
    smtp_server="smtp.163.com",
    smtp_port=465,
    username="your_email@163.com",
    password="your_password",
    to_emails=["admin@example.com"]
)
setup_email_alerts(config)
```

## 数据库结构

### token_configs 表
存储 token 类型配置

| 字段 | 类型 | 说明 |
|------|------|------|
| token_type | TEXT | Token 类型（主键） |
| validity_days | INTEGER | 有效期（天） |
| description | TEXT | 描述信息 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### token_status 表
存储 token 状态信息

| 字段 | 类型 | 说明 |
|------|------|------|
| token_type | TEXT | Token 类型（主键） |
| token_value | TEXT | Token 值 |
| expires_at | TIMESTAMP | 过期时间 |
| is_expired | INTEGER | 是否已过期 |
| last_checked_at | TIMESTAMP | 最后检查时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### token_refresher_config 表
存储 TokenRefresher 配置

| 字段 | 类型 | 说明 |
|------|------|------|
| config_key | TEXT | 配置键（主键） |
| config_value | TEXT | 配置值 |
| config_type | TEXT | 配置类型 |
| description | TEXT | 描述信息 |
| updated_at | TIMESTAMP | 更新时间 |

## 使用场景

### 场景 1: 初始化所有 Token
```python
from backend.sys_configs import get_token_refresher, TokenType

refresher = get_token_refresher()

# 更新所有默认 token
refresher.update_token(TokenType.COZE_TOKEN.value, "coze_token_value")
refresher.update_token(TokenType.AUTH_TOKEN.value, "auth_token_value")
refresher.update_token(TokenType.ACCESS_TOKEN.value, "access_token_value")
```

### 场景 2: 定期检查状态
```python
# 后台线程会自动每 10 分钟检查一次
# 也可以手动触发检查
result = refresher.check_all_tokens()
for token_type, is_expired in result.items():
    if is_expired:
        print(f"⚠️  {token_type} 已过期！")
```

### 场景 3: Token 更新后重置过期时间
```python
# 当你手动更新了某个 token，重置其过期时间
refresher.update_token(
    token_type=TokenType.COZE_TOKEN.value,
    token_value="new_token_value"
    # expires_at 不提供，会自动计算为 30 天后
)
```

### 场景 4: 紧急标记 Token 失效
```python
# 当发现 token 泄露或需要立即失效时
refresher.set_expired_immediate(TokenType.ACCESS_TOKEN.value)
# 这会立即发送邮件告警
```

## 注意事项

1. **单例模式**: 使用 `get_token_refresher()` 获取实例，确保全局只有一个实例
2. **线程安全**: 所有操作都是线程安全的
3. **后台线程**: 后台检查线程是守护线程，主程序退出时会自动停止
4. **邮件告警**: 确保已正确配置 VLogger 的邮件系统
5. **数据库路径**: 默认使用 `backend/sys_configs/system_config.db`

## 完整示例

参考 `token_refresher_example.py` 文件查看完整的使用示例。

## 集成到现有系统

### 在 Coze API 中使用

```python
# backend/ai_analysis/coze_api.py
from backend.sys_configs import get_token_refresher, TokenType

# 初始化时更新 token
refresher = get_token_refresher()
refresher.update_token(
    token_type=TokenType.COZE_TOKEN.value,
    token_value=coze_api_token
)

# 定期检查 token 状态
status = refresher.get_token_status(TokenType.COZE_TOKEN.value)
if status and status['is_expired']:
    # Token 已过期，需要更新
    print("⚠️  Coze API Token 已过期，请更新！")
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| E-TOKEN-001 | Token 已过期 |
| E-SYS-004 | 数据库操作错误 |
| E-SYS-001 | 系统内部错误 |

