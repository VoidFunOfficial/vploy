# Token 自动刷新系统

## 概述

基于 Huey 的自动 Token 刷新系统，提供定期刷新和手动触发两种机制，确保 `auth_token` 和 `access_token` 始终保持有效状态。

## 功能特性

### 1. 定期自动刷新

- **access_token**: 每 1 天自动刷新一次
- **auth_token**: 每 7 天自动刷新一次

### 2. 手动触发刷新

- 监控 `backend/sys_configs/token_refresher.py` 中的手动过期事件
- 当检测到手动过期时，立即触发两个 token 的刷新
- 监控间隔：10 秒

### 3. 自动保存

- 刷新成功后自动保存到数据库
- 更新 token 的过期时间
- 记录刷新日志

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   Huey Task System                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │   定期刷新任务 (Periodic Tasks)              │      │
│  ├──────────────────────────────────────────────┤      │
│  │  • refresh_access_token_scheduled (1天)      │      │
│  │  • refresh_auth_token_scheduled (7天)        │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │   手动触发监控 (Manual Trigger Monitor)      │      │
│  ├──────────────────────────────────────────────┤      │
│  │  • TokenExpirationMonitor                    │      │
│  │  • 监控数据库中的过期事件                     │      │
│  │  • 检测到过期后触发立即刷新                   │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │   立即刷新任务 (Immediate Refresh)           │      │
│  ├──────────────────────────────────────────────┤      │
│  │  • refresh_both_tokens_immediate()           │      │
│  │  • 同时刷新 auth_token 和 access_token       │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Token Refresher (数据库)                   │
├─────────────────────────────────────────────────────────┤
│  • 保存 token 值                                        │
│  • 记录过期时间                                         │
│  • 跟踪刷新状态                                         │
└─────────────────────────────────────────────────────────┘
```

## 使用方法

### 自动启动（推荐）

系统会在任务管理器初始化时自动启动：

```python
from backend.task_manager import init_task_manager

# 初始化任务管理器（包含 Token 刷新系统）
init_task_manager()
```

### 手动控制

```python
from backend.task_manager import (
    start_token_monitor,
    stop_token_monitor,
    trigger_immediate_refresh
)

# 启动监控器
start_token_monitor()

# 手动触发立即刷新
trigger_immediate_refresh()

# 停止监控器
stop_token_monitor()
```

### 手动标记 Token 过期

```python
from backend.sys_configs.token_refresher import get_token_refresher, TokenType

refresher = get_token_refresher()

# 手动标记 access_token 为过期
refresher.set_expired_immediate(TokenType.ACCESS_TOKEN.value)

# 手动标记 auth_token 为过期
refresher.set_expired_immediate(TokenType.AUTH_TOKEN.value)

# 监控器会在 10 秒内检测到过期事件并触发立即刷新
```

## 工作流程

### 定期刷新流程

1. Huey 定期任务触发（每 1 天或 7 天）
2. 调用 `utils.auto_token_refresher` 中的刷新函数
3. 获取新的 token
4. 保存到数据库并更新过期时间
5. 记录刷新日志

### 手动触发流程

1. 用户调用 `set_expired_immediate()` 标记 token 过期
2. TokenExpirationMonitor 每 10 秒检查一次数据库
3. 检测到过期事件（过期时间在最近 1 分钟内）
4. 触发 `refresh_both_tokens_immediate()` 任务
5. 同时刷新两个 token
6. 保存到数据库并记录日志

## 日志记录

系统会记录以下日志事件：

- `TOKEN.REFRESH.ACCESS.START`: 开始刷新 access_token
- `TOKEN.REFRESH.ACCESS.SUCCESS`: access_token 刷新成功
- `TOKEN.REFRESH.ACCESS.FAILED`: access_token 刷新失败
- `TOKEN.REFRESH.AUTH.START`: 开始刷新 auth_token
- `TOKEN.REFRESH.AUTH.SUCCESS`: auth_token 刷新成功
- `TOKEN.REFRESH.AUTH.FAILED`: auth_token 刷新失败
- `TOKEN.MONITOR.MANUAL_EXPIRE_DETECTED`: 检测到手动过期事件
- `TOKEN.REFRESH.IMMEDIATE.START`: 开始立即刷新
- `TOKEN.REFRESH.IMMEDIATE.COMPLETE`: 立即刷新完成

## 错误处理

系统包含完善的错误处理机制：

- `E-TOKEN-002`: Token 刷新成功但保存到数据库失败
- `E-TOKEN-003`: Token 刷新失败
- `E-TOKEN-004`: 刷新过程中发生异常
- `E-TOKEN-005`: 监控循环发生错误
- `E-TOKEN-006`: 检查手动过期事件时发生错误
- `E-TOKEN-007`: 立即刷新失败
- `E-TOKEN-008`: 立即刷新时发生异常
- `E-TOKEN-009`: 系统初始化失败

所有错误都会通过 VLogger 记录，并根据配置发送邮件告警。

## 配置说明

### Token 有效期配置

在 `backend/sys_configs/token_refresher.py` 中配置：

```python
DEFAULT_TOKEN_CONFIGS = {
    TokenType.ACCESS_TOKEN: TokenConfig(
        token_type=TokenType.ACCESS_TOKEN,
        validity_days=1,  # 1 天有效期
        description="访问 Token"
    ),
    TokenType.AUTH_TOKEN: TokenConfig(
        token_type=TokenType.AUTH_TOKEN,
        validity_days=7,  # 7 天有效期
        description="认证 Token"
    ),
}
```

### 监控间隔配置

在 `backend/task_manager/token_refresh_tasks.py` 中修改：

```python
# 监控循环中的睡眠时间（秒）
time.sleep(10)  # 默认 10 秒
```

## 注意事项

1. **依赖关系**: 确保 `utils.auto_token_refresher` 模块可用
2. **数据库**: 系统使用 `backend/sys_configs/system_config.db` 存储 token
3. **线程安全**: 所有操作都是线程安全的
4. **守护线程**: 监控线程是守护线程，主程序退出时会自动停止
5. **Huey Worker**: 需要运行 Huey worker 才能执行定期任务

## 启动 Huey Worker

```bash
# 启动 worker
python run_task_worker.py
```

## 测试

查看日志确认系统正常运行：

```bash
# 查看日志
tail -f logs/vlogger.log | grep TOKEN
```

