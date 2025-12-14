# Task Manager - 任务管理器

基于 Huey 和 SQLite 实现的企业级异步任务和定时任务管理系统。

## 特性

- ✅ **异步任务队列**：基于 Huey 的高性能任务队列
- ✅ **多阶段任务处理**：支持 5 个任务阶段（mark, analysis, decision, trade, listen）
- ✅ **智能任务路由**：根据 stage 和 status 自动路由到对应的处理函数
- ✅ **定时任务调度**：支持 cron 表达式和间隔时间的定时任务
- ✅ **数据持久化**：使用 SQLite 存储任务数据和状态
- ✅ **日志集成**：集成 VLogger 日志系统进行全链路追踪
- ✅ **便携扩展**：易于添加新的任务处理函数和定时任务

## 安装依赖

```bash
pip install huey
```

## 快速开始

### 1. 初始化任务管理器

```python
from backend.task_manager import init_task_manager

# 在应用启动时初始化
init_task_manager()
```

### 2. 提交异步任务

```python
from backend.task_manager import submit_task, AsyncTask, TaskStage, TaskStatus

# 创建任务
task = AsyncTask(
    stage=TaskStage.MARK,
    status=TaskStatus.WAITING,
    metadata={
        "event_id": "123",
        "market_id": "456",
        "description": "需要标记的事件"
    }
)

# 提交任务到队列
task_id = submit_task(task)
print(f"任务已提交，ID: {task_id}")
```

### 3. 查询任务状态

```python
from backend.task_manager import TaskDatabase, TaskStage, TaskStatus

db = TaskDatabase()

# 获取单个任务
task = db.get_async_task(task_id)
print(f"任务状态: {task.status.value}")
print(f"任务结果: {task.result}")

# 查询特定阶段和状态的任务
tasks = db.query_async_tasks(
    stage=TaskStage.MARK,
    status=TaskStatus.WAITING,
    limit=10
)
```

### 4. 添加定时任务

```python
from backend.task_manager import add_scheduled_task

# 添加间隔时间的定时任务（每小时执行一次）
task_id = add_scheduled_task(
    name="hourly_sync",
    task_type="interval",
    schedule="3600",  # 秒数
    enabled=True,
    metadata={"description": "每小时同步数据"}
)

# 添加 cron 表达式的定时任务（每天早上 9 点执行）
task_id = add_scheduled_task(
    name="daily_report",
    task_type="cron",
    schedule="0 9 * * *",
    enabled=True,
    metadata={"description": "每日报告"}
)
```

### 5. 启动 Huey 消费者

在命令行运行以下命令启动任务消费者：

```bash
# Windows PowerShell
huey_consumer backend.task_manager.tasks.huey

# Linux/Mac
huey_consumer backend.task_manager.tasks.huey
```

## 任务阶段和状态

### 任务阶段（TaskStage）

任务按以下顺序流转：

- `ANALYSIS`: 分析阶段 - AI 分析和数据处理（第一阶段）
- `DECISION`: 决策阶段 - 自动决策和策略选择（第二阶段）
- `MARK`: 标记阶段 - 事件标记处理（第三阶段）
- `TRADE`: 交易阶段 - 执行交易操作（第四阶段）
- `LISTEN`: 监听阶段 - 监听市场变化和事件（第五阶段）

### 完整工作流程

```
event_sniffing → ANALYSIS(WAITING) → [用户批准] → ANALYSIS(PROCESSING)
→ [自动拆分] → DECISION(WAITING) → [用户批准] → DECISION(PROCESSING)
→ MARK(WAITING) → [用户批准] → MARK(PROCESSING)
→ TRADE(WAITING) → [用户批准] → TRADE(PROCESSING)
→ LISTEN(WAITING) → LISTEN(PROCESSING)
```

### 任务状态（TaskStatus）

- `WAITING`: 等待中 - 任务已创建，等待用户批准
- `PROCESSING`: 处理中 - 任务正在执行
- `FINISHED`: 已完成 - 任务成功完成
- `FAILED`: 失败 - 任务执行失败

## 任务路由机制

系统会根据任务的 `stage` 和 `status` 组合，自动路由到对应的处理函数。

### 已注册的处理函数

| Stage | Status | 处理函数 | 说明 | 完成后转换 |
|-------|--------|---------|------|-----------|
| ANALYSIS | WAITING | `handle_analysis_waiting` | 等待用户批准开始分析 | 保持WAITING |
| ANALYSIS | PROCESSING | `handle_analysis_processing` | 执行分析处理，自动拆分为decision任务 | 自动拆分 |
| DECISION | WAITING | `handle_decision_waiting` | 等待用户批准开始决策 | 保持WAITING |
| DECISION | PROCESSING | `handle_decision_processing` | 执行决策处理 | MARK+WAITING |
| MARK | WAITING | `handle_mark_waiting` | 等待用户批准开始标记 | 保持WAITING |
| MARK | PROCESSING | `handle_mark_processing` | 执行标记处理 | TRADE+WAITING |
| TRADE | WAITING | `handle_trade_waiting` | 等待用户批准开始交易 | 保持WAITING |
| TRADE | PROCESSING | `handle_trade_processing` | 执行交易处理 | LISTEN+WAITING |
| LISTEN | WAITING | `handle_listen_waiting` | 等待开始监听 | 保持WAITING |
| LISTEN | PROCESSING | `handle_listen_processing` | 执行监听处理 | FINISHED |

### 自定义处理函数

可以使用 `@register_handler` 装饰器注册新的处理函数：

```python
from backend.task_manager import register_handler, AsyncTask, TaskStage, TaskStatus

@register_handler(TaskStage.MARK, TaskStatus.WAITING)
def my_custom_handler(task: AsyncTask) -> dict:
    """自定义处理函数"""
    # 实现你的业务逻辑
    result = {
        "processed": True,
        "data": "处理结果"
    }
    return result
```

## 预定义定时任务

系统预定义了两个定时任务：

### 1. 健康检查邮件（health_check_email）

- **执行时间**: 每天早上 9:00
- **功能**: 发送系统健康检查报告邮件
- **实现位置**: `backend/task_manager/scheduler.py`

### 2. 收益报告邮件（profit_email）

- **执行时间**: 每天下午 18:00
- **功能**: 发送每日收益报告邮件
- **实现位置**: `backend/task_manager/scheduler.py`

## 定时任务管理

### 查看所有定时任务

```python
from backend.task_manager import list_scheduled_tasks

# 查看所有任务
all_tasks = list_scheduled_tasks()

# 只查看启用的任务
enabled_tasks = list_scheduled_tasks(enabled_only=True)

for task in enabled_tasks:
    print(f"{task['name']}: {task['schedule']}")
```

### 更新定时任务

```python
from backend.task_manager import update_scheduled_task

# 修改任务执行时间
update_scheduled_task(
    name="health_check_email",
    schedule="0 10 * * *",  # 改为每天 10 点
    enabled=True
)

# 禁用任务
update_scheduled_task(
    name="profit_email",
    enabled=False
)
```

### 获取任务信息

```python
from backend.task_manager import get_scheduled_task_info

task_info = get_scheduled_task_info("health_check_email")
print(task_info)
```

## 数据库结构

### 异步任务表（async_tasks）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| stage | TEXT | 任务阶段 |
| status | TEXT | 任务状态 |
| metadata | TEXT | 任务元数据（JSON） |
| result | TEXT | 任务结果（JSON） |
| error_msg | TEXT | 错误信息 |
| create_time | TEXT | 创建时间 |
| update_time | TEXT | 更新时间 |

### 定时任务表（scheduled_tasks）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| name | TEXT | 任务名称（唯一） |
| task_type | TEXT | 任务类型（interval/cron） |
| schedule | TEXT | 调度配置 |
| enabled | INTEGER | 是否启用 |
| last_run | TEXT | 上次运行时间 |
| next_run | TEXT | 下次运行时间 |
| metadata | TEXT | 任务元数据（JSON） |
| create_time | TEXT | 创建时间 |
| update_time | TEXT | 更新时间 |

## 配置

可以通过 `TaskManagerConfig` 自定义配置：

```python
from backend.task_manager import TaskManagerConfig, set_config

config = TaskManagerConfig(
    db_path="./custom/path/tasks.db",
    huey_db_path="./custom/path/huey.db",
    workers=8,  # 工作进程数
    scheduler_interval=30  # 调度器检查间隔（秒）
)

set_config(config)
```

## 日志集成

所有任务操作都会通过 VLogger 记录日志，支持全链路追踪：

```python
# 日志会自动记录以下信息：
# - 任务提交: TASK.SUBMIT
# - 任务开始: TASK.PROCESS.START
# - 任务执行: TASK.PROCESS.EXECUTE
# - 任务成功: TASK.PROCESS.SUCCESS
# - 任务失败: TASK.PROCESS.FAILED
# - 定时任务: SCHEDULER.*
```

## 注意事项

1. **Huey 消费者**: 必须启动 Huey 消费者进程才能处理异步任务
2. **数据库路径**: 确保数据库文件路径有写入权限
3. **任务处理函数**: 所有处理函数都是占位符，需要根据实际业务实现具体逻辑
4. **定时任务**: 预定义的定时任务需要实现具体的邮件发送逻辑
5. **错误处理**: 任务失败时会自动更新状态为 FAILED 并记录错误信息

## 扩展开发

### 添加新的任务阶段

1. 在 `models.py` 中的 `TaskStage` 枚举添加新阶段
2. 在 `tasks.py` 中使用 `@register_handler` 注册处理函数

### 添加新的定时任务

1. 在 `scheduler.py` 中使用 `@huey.periodic_task()` 装饰器定义任务
2. 在 `init_default_scheduled_tasks()` 中添加任务初始化代码

## 示例：完整工作流

```python
from backend.task_manager import (
    init_task_manager,
    submit_task,
    AsyncTask,
    TaskStage,
    TaskStatus,
    TaskDatabase
)

# 1. 初始化
init_task_manager()

# 2. 创建并提交任务
task = AsyncTask(
    stage=TaskStage.ANALYSIS,
    status=TaskStatus.WAITING,
    metadata={"event_id": "evt_123", "data": "分析数据"}
)
task_id = submit_task(task)

# 3. 查询任务状态
db = TaskDatabase()
task = db.get_async_task(task_id)
print(f"任务状态: {task.status.value}")

# 4. 任务会自动被 Huey 消费者处理
# 5. 处理完成后可以查看结果
task = db.get_async_task(task_id)
print(f"任务结果: {task.result}")
```

