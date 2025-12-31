# Token 自动刷新系统

## 概述

基于 Huey 和动态调度器的自动 Token 刷新系统，提供定期刷新和手动触发两种机制，确保 `auth_token` 和 `access_token` 始终保持有效状态。

## 功能特性

### 1. 定期自动刷新（由动态调度器管理）

- **access_token**: 每天凌晨 0 点自动刷新
- **auth_token**: 每 7 天凌晨 1 点自动刷新

### 2. 手动触发刷新

- 监控 `backend/sys_configs/token_refresher.py` 中的手动过期事件
- 当检测到手动过期时，立即触发两个 token 的刷新
- 监控间隔：10 秒

### 3. 前端管理

- 可在前端任务管理界面查看任务状态
- 支持启用/禁用任务
- 查看任务执行历史和下次运行时间
- 手动触发任务执行

### 4. 自动保存

- 刷新成功后自动保存到数据库
- 更新 token 的过期时间
- 记录刷新日志

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              动态调度器 (Dynamic Scheduler)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  定时任务数据库 (scheduled_tasks 表)                     │
│  ┌──────────────────────────────────────────────┐      │
│  │  • refresh_access_token (每天 0:00)          │      │
│  │  • refresh_auth_token (每 7 天 1:00)         │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  任务执行器 (Task Executors)                            │
│  ┌──────────────────────────────────────────────┐      │
│  │  • _execute_refresh_access_token()           │      │
│  │  • _execute_refresh_auth_token()             │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         Token 刷新任务 (token_refresh_tasks.py)         │
├─────────────────────────────────────────────────────────┤
│  • refresh_access_token_scheduled()                     │
│  • refresh_auth_token_scheduled()                       │
│  • refresh_both_tokens_immediate()                      │
│  • TokenExpirationMonitor (手动触发监控)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│       Token 刷新函数 (utils/auto_token_refresher.py)    │
├─────────────────────────────────────────────────────────┤
│  • refresh_access_token()                               │
│  • refresh_auth_token()                                 │
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

## 前端管理

### 查看任务列表

访问前端任务管理页面，可以看到所有定时任务，包括：

- `refresh_access_token`: Access Token 自动刷新
- `refresh_auth_token`: Auth Token 自动刷新

### 任务信息

每个任务显示以下信息：

- **任务名称**: 任务的唯一标识
- **描述**: 任务的详细说明
- **调度表达式**: Cron 表达式（如 `0 0 * * *`）
- **启用状态**: 是否启用
- **下次运行时间**: 下一次执行的时间
- **上次运行时间**: 上一次执行的时间
- **运行次数**: 总共执行的次数

### 操作

- **启用/禁用**: 切换任务的启用状态
- **立即执行**: 手动触发任务执行
- **查看详情**: 查看任务的详细信息和执行历史

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
    trigger_immediate_refresh,
    start_token_monitor,
    stop_token_monitor
)

# 手动触发立即刷新
trigger_immediate_refresh()

# 启动监控器
start_token_monitor()

# 停止监控器
stop_token_monitor()
```

### 手动标记 Token 过期

```python
from backend.sys_configs.token_refresher import get_token_refresher, TokenType

refresher = get_token_refresher()

# 手动标记 access_token 为过期
refresher.set_expired_immediate(TokenType.ACCESS_TOKEN.value)

# 监控器会在 10 秒内检测到过期事件并触发立即刷新
```

## API 接口

### 获取任务列表

```http
GET /api/scheduled-tasks
```

### 获取任务详情

```http
GET /api/scheduled-tasks/{task_id}
```

### 更新任务

```http
PUT /api/scheduled-tasks/{task_id}
Content-Type: application/json

{
  "enabled": true
}
```

### 立即执行任务

```http
POST /api/scheduled-tasks/{task_id}/execute
```

## 测试

运行测试脚本：

```bash
python test/test_token_refresh_tasks.py
```

查看日志：

```bash
tail -f logs/vlogger.log | grep TOKEN
```

## 注意事项

1. **依赖关系**: 确保 `utils.auto_token_refresher` 模块可用
2. **数据库**: 系统使用 `backend/sys_configs/system_config.db` 存储 token
3. **线程安全**: 所有操作都是线程安全的
4. **守护线程**: 监控线程是守护线程，主程序退出时会自动停止
5. **Worker 运行**: 需要运行 Huey worker 和动态调度器才能执行任务

## 启动服务

```bash
# 启动 Huey Worker
python run_task_worker.py
```

Worker 启动后会自动：
- 初始化任务管理器
- 启动动态调度器
- 启动 Token 过期监控器
- 加载所有定时任务

