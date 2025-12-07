# MARK 和 ANALYSIS 处理函数文档

## 概述

本文档描述了任务管理系统中 MARK 和 ANALYSIS 阶段的处理函数实现。

## 工作流程

```
Event ID → MARK (PROCESSING) → ANALYSIS (WAITING) → [用户批准] → ANALYSIS (PROCESSING) → 完成
```

**关键点**:
- MARK 成功后，任务会自动转换为 ANALYSIS+WAITING 状态
- ANALYSIS+WAITING 状态需要用户手动批准才会开始处理
- 使用 `approve_analysis(task_id)` 函数批准任务

### 1. MARK 阶段 (PROCESSING)

**处理函数**: `handle_mark_processing`

**功能**:
1. 从 `metadata` 中获取 `event_id`
2. 通过 Polymarket API 获取 Event 对象
3. 调用 `auto_mark.py` 的 `mark()` 函数进行标记
4. 将标记结果写入 `result` 字段和 `metadata`
5. 返回 `next_stage` 和 `next_status`，指示任务转换为 ANALYSIS+WAITING

**输入** (task.metadata):
```json
{
  "event_id": "事件ID",
  "description": "任务描述（可选）"
}
```

**输出** (task.result):
```json
{
  "mark": "标记结果",
  "event_id": "事件ID",
  "event_title": "事件标题"
}
```

**任务转换**:
- 任务的 `stage` 转换为 `ANALYSIS`
- 任务的 `status` 转换为 `WAITING`
- 任务的 `metadata` 更新，添加 `mark` 和 `event_title` 字段

### 2. ANALYSIS 阶段 (WAITING)

**处理函数**: `handle_analysis_waiting`

**功能**:
- 返回 waiting 状态，保持 WAITING 状态不变
- 等待用户调用 `approve_analysis(task_id)` 批准任务

**输入** (task.metadata):
```json
{
  "event_id": "事件ID",
  "mark": "标记结果",
  "event_title": "事件标题"
}
```

**输出** (task.result):
```json
{
  "event_id": "事件ID",
  "mark": "标记结果",
  "event_title": "事件标题"
}
```

**批准函数**: `approve_analysis(task_id: int) -> bool`

**功能**:
- 检查任务是否为 ANALYSIS+WAITING 状态
- 将任务转换为 PROCESSING 状态
- 提交到 Huey 队列进行处理

**使用示例**:
```python
from backend.task_manager import approve_analysis

# 批准分析任务
success = approve_analysis(task_id)
if success:
    print("分析任务已批准")
else:
    print("批准失败")
```

### 3. ANALYSIS 阶段 (PROCESSING)

**处理函数**: `handle_analysis_processing`

**功能**:
1. 从 `metadata` 中获取 `event_id`
2. 通过 Polymarket API 获取 Event 对象
3. 生成 `event_summary_readableforai` 摘要
4. 从 `token_refresher` 获取 `access_token` 和 `auth_token`
5. 构建 cookie_string
6. 创建 `AnalysisTaskManager` 并提交深度分析任务
7. 等待分析完成（最多2小时）
8. 将分析结果写入 `metadata`

**输入** (task.metadata):
```json
{
  "event_id": "事件ID",
  "mark": "标记结果",
  "source_task_id": "来源MARK任务ID"
}
```

**输出** (task.metadata - 更新后):
```json
{
  "event_id": "事件ID",
  "mark": "标记结果",
  "source_task_id": "来源MARK任务ID",
  "analysis_result": {
    "market_id_1": {
      "p": 0.6,
      "a": 0.3,
      "reasons_p": ["正面理由1", "正面理由2"],
      "reasons_n": ["负面理由1"]
    },
    "market_id_2": {
      "p": 0.7,
      "a": 0.2,
      "reasons_p": ["正面理由1"],
      "reasons_n": ["负面理由1", "负面理由2"]
    }
  },
  "analysis_task_id": "深度分析任务ID",
  "market_ids": ["market_id_1", "market_id_2"]
}
```

**输出** (task.result):
```json
{
  "event_id": "事件ID",
  "analysis_result": {
    "market_id_1": {...},
    "market_id_2": {...}
  },
  "market_ids": ["market_id_1", "market_id_2"]
}
```

## 使用示例

### 示例 1: 提交 MARK 任务

```python
from backend.task_manager import submit_task, AsyncTask, TaskStage, TaskStatus

# 创建 MARK 任务
task = AsyncTask(
    stage=TaskStage.MARK,
    status=TaskStatus.PROCESSING,
    metadata={
        "event_id": "your_event_id_here",
        "description": "标记处理任务"
    }
)

# 提交任务
task_id = submit_task(task)
print(f"已提交 MARK 任务，ID: {task_id}")
```

### 示例 2: 查询任务结果

```python
from backend.task_manager import TaskDatabase

db = TaskDatabase()

# 查询 MARK 任务
mark_task = db.get_async_task(mark_task_id)
print(f"MARK 任务状态: {mark_task.status.value}")
print(f"MARK 结果: {mark_task.result}")

# 获取 ANALYSIS 任务 ID
analysis_task_id = mark_task.result.get("analysis_task_id")

# 查询 ANALYSIS 任务
if analysis_task_id:
    analysis_task = db.get_async_task(analysis_task_id)
    print(f"ANALYSIS 任务状态: {analysis_task.status.value}")
    print(f"分析结果: {analysis_task.metadata.get('analysis_result')}")
```

### 示例 3: 完整工作流

```python
from backend.task_manager import submit_task, approve_analysis, AsyncTask, TaskStage, TaskStatus, TaskDatabase
import time

# 1. 提交 MARK 任务
mark_task = AsyncTask(
    stage=TaskStage.MARK,
    status=TaskStatus.PROCESSING,
    metadata={"event_id": "your_event_id"}
)
task_id = submit_task(mark_task)

# 2. 等待 MARK 任务完成并转换为 ANALYSIS+WAITING
time.sleep(5)

# 3. 查询任务状态
db = TaskDatabase()
task = db.get_async_task(task_id)
print(f"任务阶段: {task.stage.value}")  # ANALYSIS
print(f"任务状态: {task.status.value}")  # WAITING
print(f"标记结果: {task.metadata.get('mark')}")

# 4. 用户批准分析任务
success = approve_analysis(task_id)
if success:
    print("分析任务已批准")

    # 5. 等待 ANALYSIS 任务完成（可能需要较长时间）
    time.sleep(600)  # 等待10分钟

    # 6. 查询分析结果
    task = db.get_async_task(task_id)
    print(f"分析结果: {task.metadata.get('analysis_result')}")
else:
    print("批准失败")
```

## 依赖配置

### 1. Token 配置

在使用 ANALYSIS 处理函数之前，需要配置 `access_token` 和 `auth_token`:

```python
from backend.sys_configs import get_token_refresher, TokenType

refresher = get_token_refresher()

# 配置 access_token
refresher.update_token(
    token_type=TokenType.ACCESS_TOKEN.value,
    token_value="your_access_token_here"
)

# 配置 auth_token
refresher.update_token(
    token_type=TokenType.AUTH_TOKEN.value,
    token_value="your_auth_token_here"
)
```

### 2. Huey 消费者

确保 Huey 消费者正在运行：

```bash
huey_consumer backend.task_manager.tasks.huey
```

## 错误处理

### MARK 阶段错误码

- `E-MARK-001`: metadata 中缺少 event_id
- `E-MARK-002`: 未找到指定的 event_id
- `E-MARK-003`: 标记处理异常

### ANALYSIS 阶段错误码

- `E-ANALYSIS-001`: metadata 中缺少 event_id
- `E-ANALYSIS-002`: 未找到指定的 event_id
- `E-ANALYSIS-003`: 未配置 access_token 或 auth_token
- `E-ANALYSIS-004`: access_token 或 auth_token 已过期
- `E-ANALYSIS-005`: 分析任务超时或失败
- `E-ANALYSIS-006`: 分析失败
- `E-ANALYSIS-007`: 分析处理异常

## 日志事件

### MARK 阶段

- `TASK.MARK.PROCESSING`: 开始处理 MARK 任务
- `TASK.MARK.ERROR`: MARK 处理错误
- `TASK.MARK.SUCCESS`: 标记处理完成
- `TASK.MARK.ANALYSIS_SUBMITTED`: 已提交 ANALYSIS 任务
- `TASK.MARK.EXCEPTION`: MARK 处理异常

### ANALYSIS 阶段

- `TASK.ANALYSIS.WAITING`: ANALYSIS 任务等待处理
- `TASK.ANALYSIS.PROCESSING`: 开始处理 ANALYSIS 任务
- `TASK.ANALYSIS.ERROR`: ANALYSIS 处理错误
- `TASK.ANALYSIS.SUMMARY_GENERATED`: 生成事件摘要
- `TASK.ANALYSIS.SUBMITTED`: 已提交深度分析任务
- `TASK.ANALYSIS.SUCCESS`: 分析处理完成
- `TASK.ANALYSIS.EXCEPTION`: ANALYSIS 处理异常

## 注意事项

1. **异步执行**: 所有任务都是异步执行的，需要通过轮询或回调机制获取结果
2. **超时设置**: ANALYSIS 任务最多等待 2 小时（7200 秒）
3. **Token 有效期**: 确保 access_token 和 auth_token 在有效期内
4. **资源消耗**: 深度分析任务可能消耗较多资源，建议控制并发数量
5. **错误重试**: 当前实现不包含自动重试机制，失败的任务需要手动重新提交

## 测试

参考 `test_handlers.py` 文件查看完整的测试示例。

