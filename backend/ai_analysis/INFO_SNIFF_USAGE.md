# Info Sniff 功能使用说明

## 概述

Info Sniff 是一个轻量级的信息嗅探功能，用于快速收集和分析事件相关信息。相比于完整的 Analysis 任务，Info Sniff 具有以下特点：

- **更快的响应时间**：默认30秒首次轮询，20秒轮询间隔
- **更低的积分消耗**：每次仅消耗1积分（Analysis消耗6积分）
- **更简洁的输出**：返回主要驱动因素和支持/反对理由

## 积分系统

### 额度限制

- **6小时内**：最多180积分
- **3天内**：最多1080积分

### 积分消耗

- **Analysis 任务**：每次消耗 6 积分
- **Info Sniff 任务**：每次消耗 1 积分

### 示例计算

在6小时内，你可以：
- 执行 30 次 Analysis 任务（30 × 6 = 180积分）
- 执行 180 次 Info Sniff 任务（180 × 1 = 180积分）
- 或混合使用：20次 Analysis + 60次 Info Sniff（120 + 60 = 180积分）

## 使用方法

### 1. 基本使用

```python
from backend.ai_analysis.deep_analysis import AnalysisTaskManager
from backend.task_manager.models import AsyncTask, TaskStage, TaskStatus, TaskDatabase

# 初始化
db = TaskDatabase()
manager = AnalysisTaskManager()

# 创建任务
task = AsyncTask(
    stage=TaskStage.ANALYSIS,
    status=TaskStatus.PROCESSING,
    metadata={"event_id": "event_123"}
)
task_id = db.create_async_task(task)

# 提交 Info Sniff 任务
event_summary = """
Event: Will Trump mention "tariffs" in his next speech?
Date: 2025-01-15
Market ID: 12345
"""

success = manager.submit_info_sniff(
    async_task_id=task_id,
    event_summary=event_summary,
    initial_delay=30,      # 30秒后开始轮询
    polling_interval=20,   # 每20秒轮询一次
    max_timeout=1800       # 最多等待30分钟
)

if success:
    print("✓ Info Sniff任务已提交")
```

### 2. 查询任务状态

```python
# 获取任务状态
status = manager.get_analysis_status(task_id)
print(f"任务状态: {status}")

# 获取完整任务信息
task_info = manager.get_task_info(task_id)
print(f"任务信息: {task_info}")
```

### 3. 获取结果

```python
# 获取分析结果
result = manager.get_analysis_result(task_id)

if result:
    print(f"主要驱动因素: {result['primary_driver']}")
    print(f"\n支持理由 ({len(result['new_reasons_yes'])}条):")
    for reason in result['new_reasons_yes']:
        print(f"  - {reason}")
    
    print(f"\n反对理由 ({len(result['new_reasons_no'])}条):")
    for reason in result['new_reasons_no']:
        print(f"  - {reason}")
```

### 4. 重试失败的任务

```python
# 如果任务失败，可以重试
success = manager.retry_info_sniff(task_id)
if success:
    print("✓ 任务已重新提交")
```

## 返回结果格式

Info Sniff 任务成功后，返回以下JSON格式：

```json
{
  "primary_driver": "HYPE",
  "new_reasons_yes": [
    "特朗普在过去三次演讲中都提到了关税问题",
    "当前贸易政策是其核心议题之一",
    "最近的民调显示选民关注贸易问题"
  ],
  "new_reasons_no": [
    "演讲主题是国内政策，不涉及贸易",
    "时间有限，可能只聚焦核心议题",
    "顾问建议避免争议性话题"
  ]
}
```

### 字段说明

- **primary_driver**: 主要驱动因素
  - `"HYPE"`: 主要由炒作、情绪、投机驱动
  - `"REALITY"`: 主要由实际事实、数据、客观情况驱动

- **new_reasons_yes**: 支持事件发生的理由列表（字符串数组）

- **new_reasons_no**: 反对事件发生的理由列表（字符串数组）

## 任务状态

Info Sniff 任务使用与 Analysis 相同的状态枚举：

- `PENDING`: 待处理
- `WAITING_QUOTA`: 等待额度恢复
- `REQUESTING`: 正在发送GPT请求
- `POLLING`: 正在轮询结果
- `VALIDATING`: 正在验证结果格式
- `SUCCESS`: 任务成功
- `FAILED`: 任务失败

## 注意事项

1. **额度管理**：Info Sniff 和 Analysis 共享同一个积分池，请合理分配使用
2. **验证失败**：如果返回结果格式不符合要求，任务会标记为失败，可以重试
3. **超时设置**：Info Sniff 默认超时时间为30分钟，可根据需要调整
4. **Token过期**：如果 access_token 或 auth_token 过期，任务会失败，需要刷新token后重试

