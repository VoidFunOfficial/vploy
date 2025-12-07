# AI分析任务工作流程

## 概述

基于Huey任务队列的AI分析系统，采用**提交-轮询分离**的设计模式，确保任务提交快速返回，后台异步处理。

## 核心设计理念

**提交成功的定义**: 获取到 `conversation_id` 即为提交成功，无需等待完整分析结果。

## 任务状态流转

```
PENDING (待处理)
    ↓
REQUESTING (请求中) - 发送GPT请求
    ↓
POLLING (轮询中) - 获取到conversation_id，开始轮询
    ↓
VALIDATING (验证中) - 获取到结果，验证JSON格式
    ↓
SUCCESS (成功) / FAILED (失败)
```

## 工作流程

### 1. 提交阶段 (`submit_gpt_request`)

**目标**: 快速提交GPT请求并获取conversation_id

**步骤**:
1. 获取任务对象
2. 验证Token（access_token, auth_token）
3. 加载分析提示词（analysis.md）
4. 发送GPT请求
5. **提取conversation_id** ← 提交成功的标志
6. 更新任务状态为 `POLLING`
7. 记录提交时间

**返回**: 立即返回，不等待分析结果

### 2. 轮询阶段 (`poll_gpt_result`)

**目标**: 定期轮询直到获取分析结果或超时

**步骤**:
1. 检查conversation_id是否存在
2. 等待初始延迟（默认300秒）
3. 开始轮询循环:
   - 检查是否超时
   - 调用 `get_result()` 查询结果
   - 处理三种情况:
     - **成功**: 验证JSON格式 → 更新为SUCCESS
     - **思考中**: 继续等待
     - **失败**: 重试或标记失败

**超时处理**: 超过 `max_timeout` 后标记为FAILED

**验证失败处理**: 直接标记为FAILED（不再重新请求）

## 任务管理函数

### `submit_analysis_task()`

提交分析任务到Huey队列

```python
def submit_analysis_task(
    async_task_id: int,
    event_summary: str,
    initial_delay: int = 300,      # 首次轮询延迟（秒）
    polling_interval: int = 60,    # 轮询间隔（秒）
    max_timeout: int = 3600        # 最大超时时间（秒）
) -> bool
```

**工作流程**:
1. 保存 `event_summary` 到任务（用于重试）
2. 调用 `submit_gpt_request()` 提交请求
3. 调用 `poll_gpt_result()` 调度轮询任务
4. 立即返回 `True`

**返回值**: 
- `True`: 任务已提交到Huey队列
- `False`: 提交失败

### `retry_analysis_task()`

重试失败的分析任务

```python
def retry_analysis_task(async_task_id: int) -> bool
```

**工作流程**:
1. 获取任务对象
2. 从 `task.result["event_summary"]` 获取原始摘要
3. 重置任务状态（清除错误、conversation_id等）
4. 调用 `submit_analysis_task()` 重新提交

## 使用示例

### 基本使用

```python
from backend.ai_analysis.deep_analysis import AnalysisTaskManager
from backend.task_manager.models import AsyncTask, TaskStage, TaskStatus

# 创建任务
task = AsyncTask(
    stage=TaskStage.ANALYSIS,
    status=TaskStatus.PROCESSING,
    metadata={"event_id": "event_123"}
)
db.create_async_task(task)

# 提交分析
manager = AnalysisTaskManager()
success = manager.submit_analysis(
    async_task_id=task.id,
    event_summary="事件摘要文本...",
    initial_delay=300,      # 5分钟后开始轮询
    polling_interval=60,    # 每分钟轮询一次
    max_timeout=3600        # 最多等待1小时
)

if success:
    print("✓ 任务已提交到Huey队列")
else:
    print("✗ 提交失败")
```

### 查询任务状态

```python
# 获取分析状态
status = manager.get_analysis_status(task.id)
print(f"分析状态: {status}")  # PENDING/REQUESTING/POLLING/VALIDATING/SUCCESS/FAILED

# 获取分析结果
result = manager.get_analysis_result(task.id)
if result:
    print(f"分析结果: {result}")
    # 格式: {"705811": {"p": 0.72, "n": 0.28, "a": 0.68, "reasons_y": [...], "reasons_n": [...]}, ...}

# 获取完整任务信息
info = manager.get_task_info(task.id)
print(f"任务信息: {info}")
```

### 重试失败任务

```python
# 重试失败的任务
success = manager.retry_analysis(task.id)
if success:
    print("✓ 任务已重新提交")
else:
    print("✗ 重试失败")
```

## 数据结构

### AsyncTask.result 字段

```json
{
  "event_summary": "事件摘要文本（用于重试）",
  "analysis_status": "POLLING",
  "conversation_id": "conv_abc123",
  "submit_time": 1234567890.123,
  "raw_response": "GPT原始响应",
  "analysis_result": {
    "705811": {
      "p": 0.72,
      "n": 0.28,
      "a": 0.68,
      "reasons_y": ["支持原因1", "支持原因2"],
      "reasons_n": ["反对原因1", "反对原因2"]
    }
  },
  "market_ids": ["705811", "705812"],
  "error": "错误信息（如果失败）"
}
```

### AsyncTask.metadata 字段

```json
{
  "event_id": "event_123",
  "analysis_result": { ... },  // 同步到metadata
  "market_ids": ["68095", "68096"]
}
```

## 关键特性

### 1. 快速提交

- 提交函数立即返回，不阻塞
- 获取到conversation_id即为成功
- 后台Huey任务异步处理

### 2. 状态追踪

- 6种分析状态精确追踪
- conversation_id全程保留
- 提交时间记录

### 3. 错误处理

- Token过期检测
- 超时自动失败
- 验证失败直接标记（不重新请求）
- 支持手动重试

### 4. 日志记录

- VLogger结构化日志
- trace_id全链路追踪
- 事件类型分类（SUBMIT/POLL/VALIDATION）
- 错误码体系（E-SUBMIT-xxx, E-POLL-xxx）

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_delay` | 300秒 | 首次轮询延迟（GPT思考时间） |
| `polling_interval` | 60秒 | 轮询间隔 |
| `max_timeout` | 3600秒 | 最大超时时间（1小时） |
| `max_retries` | 3次 | 查询失败最大重试次数 |
| `max_validation_retries` | 3次 | 验证失败最大重试次数（已废弃） |

## 与旧版本的区别

### 旧版本（单一任务）

- 提交后等待完整分析结果
- 阻塞式执行
- 验证失败会重新发送GPT请求

### 新版本（提交-轮询分离）

- ✅ 提交立即返回（获取conversation_id即成功）
- ✅ 提交和轮询分离为两个独立的Huey任务
- ✅ 验证失败直接标记，不重新请求
- ✅ 支持手动重试机制
- ✅ event_summary保存在任务中，便于重试

## 注意事项

1. **提交成功 ≠ 分析完成**: 提交成功只表示获取到conversation_id，需要继续轮询获取结果
2. **重试机制**: 只有手动调用 `retry_analysis()` 才会重试，验证失败不会自动重新请求
3. **event_summary保存**: 提交时会将event_summary保存到task.result中，确保重试时可用
4. **Token有效性**: 提交和轮询都会检查Token，确保在整个流程中Token有效

