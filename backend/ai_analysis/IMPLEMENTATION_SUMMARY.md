# Info Sniff 功能实现总结

## 实现概述

本次实现在AI分析系统中添加了 `info_sniff` 功能，并将GPT请求系统从简单计数改为基于积分的管理系统。

## 主要修改

### 1. GPT请求积分系统 (analysis_tasks.py)

#### 数据库表结构更新

在 `gpt_requests` 表中添加了两个新字段：
- `credits INTEGER DEFAULT 6`: 记录每次请求消耗的积分
- `task_type TEXT DEFAULT 'analysis'`: 记录任务类型（'analysis' 或 'info_sniff'）

#### 额度限制更新

```python
# 旧配置（基于请求次数）
LIMITS = [
    {"hours": 6, "max_requests": 30},
    {"hours": 72, "max_requests": 180},
]

# 新配置（基于积分）
LIMITS = [
    {"hours": 6, "max_credits": 180},    # 6小时内最多180积分
    {"hours": 72, "max_credits": 1080},  # 3天内最多1080积分
]
```

#### 新增方法

**GPTRequestDatabase 类：**
- `get_credits_in_window(hours)`: 获取指定时间窗口内消耗的总积分
- `record_request()`: 更新为支持 `credits` 和 `task_type` 参数

**GPTQuotaManager 类：**
- `check_quota(required_credits)`: 检查是否有足够积分，支持差异化积分消耗
- `record_request()`: 更新为支持 `credits` 和 `task_type` 参数

#### 积分消耗规则

- **Analysis 任务**: 每次消耗 6 积分
- **Info Sniff 任务**: 每次消耗 1 积分
- **失败的请求**: 不消耗积分（credits=0）

### 2. Info Sniff 任务实现 (analysis_tasks.py)

#### 新增函数

**Huey 异步任务：**
- `submit_info_sniff_request()`: 提交 Info Sniff GPT 请求
- `poll_info_sniff_result()`: 轮询 Info Sniff 结果并验证

**任务管理函数：**
- `submit_info_sniff_task()`: 提交 Info Sniff 任务到 Huey 队列
- `retry_info_sniff_task()`: 重试失败的 Info Sniff 任务

**验证函数：**
- `validate_info_sniff_result()`: 验证 Info Sniff 返回的 JSON 格式

#### 任务特点

- **更快的响应**: 默认30秒首次轮询，20秒轮询间隔（vs Analysis的100秒/60秒）
- **更短的超时**: 默认1800秒（30分钟）超时（vs Analysis的3600秒）
- **使用 gpt-5-instant 模型**: 更快的响应速度
- **完整的错误处理**: 包括额度检查、Token验证、超时处理等

### 3. 公共API (deep_analysis.py)

#### AnalysisTaskManager 类新增方法

```python
def submit_info_sniff(
    async_task_id: int,
    event_summary: str,
    initial_delay: int = 30,
    polling_interval: int = 20,
    max_timeout: int = 1800
) -> bool

def retry_info_sniff(async_task_id: int) -> bool
```

这些方法提供了与 `submit_analysis()` 和 `retry_analysis()` 一致的接口。

### 4. Prompt 模板 (info.md)

创建了专门的 Info Sniff prompt 模板，要求返回：

```json
{
  "primary_driver": "HYPE" or "REALITY",
  "new_reasons_yes": ["理由1", "理由2", ...],
  "new_reasons_no": ["理由1", "理由2", ...]
}
```

## 技术实现要点

### 1. 积分计算逻辑

在 `get_next_available_time()` 方法中实现了基于积分的滑动窗口计算：

```python
# 按时间顺序获取所有请求及其积分
requests = cursor.fetchall()

# 计算累积积分，找到需要移除的最早请求
cumulative_credits = current_credits
for req in requests:
    cumulative_credits -= req['credits']
    if cumulative_credits < max_credits:
        # 找到了需要移除的请求，计算下一个可用时间
        earliest_request_time = datetime.fromisoformat(req['request_time'])
        next_available = earliest_request_time + timedelta(hours=hours)
        return next_available
```

### 2. JSON 验证

Info Sniff 的验证逻辑包括：
- 提取 JSON（支持 markdown 代码块）
- 验证必需字段存在
- 验证 `primary_driver` 值为 "HYPE" 或 "REALITY"
- 验证 `new_reasons_yes` 和 `new_reasons_no` 为字符串数组

### 3. 状态追踪

Info Sniff 复用了 Analysis 的状态枚举 (`AnalysisStatus`)，确保状态管理的一致性。

### 4. 日志记录

所有 Info Sniff 相关操作使用 `INFO_SNIFF.*` 前缀的日志事件，便于追踪和调试。

## 兼容性

### 向后兼容

- 现有的 Analysis 任务不受影响
- 数据库表结构向后兼容（新字段有默认值）
- 旧的请求记录会被视为 6 积分的 analysis 任务

### 数据库迁移

由于使用了 `DEFAULT` 值，现有数据会自动获得：
- `credits = 6`
- `task_type = 'analysis'`

## 使用示例

```python
from backend.ai_analysis.deep_analysis import AnalysisTaskManager

manager = AnalysisTaskManager()

# 提交 Info Sniff 任务
success = manager.submit_info_sniff(
    async_task_id=task_id,
    event_summary="事件描述...",
    initial_delay=30,
    polling_interval=20,
    max_timeout=1800
)

# 获取结果
result = manager.get_analysis_result(task_id)
# {
#   "primary_driver": "HYPE",
#   "new_reasons_yes": [...],
#   "new_reasons_no": [...]
# }
```

## 文件清单

### 修改的文件
- `backend/ai_analysis/analysis_tasks.py`: 核心实现
- `backend/ai_analysis/deep_analysis.py`: 公共API
- `backend/ai_analysis/info.md`: Prompt 模板

### 新增的文件
- `backend/ai_analysis/INFO_SNIFF_USAGE.md`: 使用说明
- `backend/ai_analysis/IMPLEMENTATION_SUMMARY.md`: 实现总结（本文件）

## 测试建议

1. **积分系统测试**
   - 验证积分正确计算
   - 验证额度限制正确执行
   - 验证混合使用 Analysis 和 Info Sniff 时的积分消耗

2. **Info Sniff 功能测试**
   - 提交任务并验证状态转换
   - 验证 JSON 格式验证逻辑
   - 测试失败重试机制

3. **集成测试**
   - 验证与现有 Analysis 任务的兼容性
   - 验证数据库表结构更新
   - 验证日志记录完整性

