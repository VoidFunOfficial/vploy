# 价格涨幅AI分析功能实现说明

## 概述

在 `backend/position_listener/market_monitor.py` 中实现了 `_handle_price_surge` 方法，用于处理价格涨跌幅超过阈值（10%）的情况。该方法集成了AI分析模块，自动分析价格变动的驱动因素。

## 功能特性

### 1. AI分析集成

- **分析模块**: 使用 `AnalysisTaskManager` 的 `submit_info_sniff` 方法
- **分析类型**: Info Sniff（快速分析，消耗1积分）
- **响应时间**: 10秒首次轮询，10秒轮询间隔，最多等待5分钟

### 2. 分析结果格式

AI分析返回JSON格式数据：

```json
{
  "primary_driver": "HYPE" or "REALITY",
  "new_reasons_yes": ["理由1", "理由2", ...],
  "new_reasons_no": ["理由1", "理由2", ...]
}
```

- **primary_driver**: 价格变动的主要驱动类型
  - `HYPE`: 情绪/炒作驱动
  - `REALITY`: 基本面/事实驱动
- **new_reasons_yes**: 支持价格上涨的理由列表
- **new_reasons_no**: 支持价格下跌的理由列表

### 3. 持仓元数据更新

分析结果存储在 Position 对象的 `metadata` 字段中：

```json
{
  "price_surge_analyses": [
    {
      "task_id": 123,
      "timestamp": "2025-12-28T10:30:00",
      "price_change_pct": 0.15,
      "entry_price": 0.50,
      "current_price": 0.65,
      "status": "pending",
      "primary_driver": "HYPE",
      "reasons_yes": ["理由1", "理由2"],
      "reasons_no": ["理由1", "理由2"],
      "completed_at": "2025-12-28T10:35:00"
    }
  ]
}
```

## 工作流程

### 1. 价格涨幅检测

在 `monitor_position` 方法中，当检测到价格涨跌幅超过10%时，调用 `_handle_price_surge` 方法。

### 2. AI分析提交

`_handle_price_surge` 方法执行以下步骤：

1. **获取市场信息**: 从 GammaMarketsAPI 获取市场详情
2. **构建事件摘要**: 包含市场问题、持仓信息、价格变动等
3. **创建AsyncTask**: 创建分析任务记录
4. **提交Info Sniff**: 调用AI分析模块进行快速分析
5. **更新持仓metadata**: 记录分析任务ID和初始状态

### 3. 结果更新

定时任务 `update_price_surge_analysis_task` 每2分钟执行一次：

1. **查询所有持仓**: 获取所有未平仓的持仓
2. **检查待处理分析**: 遍历每个持仓的 `price_surge_analyses`
3. **获取分析结果**: 调用 `get_analysis_result` 获取完成的分析
4. **更新metadata**: 将分析结果（primary_driver、reasons等）写入持仓metadata
5. **保存持仓**: 更新数据库中的持仓记录

## 错误处理

- **市场信息获取失败**: 记录错误日志，终止分析
- **AI任务提交失败**: 记录错误日志，不影响价格监控
- **分析任务失败**: 标记为 `failed` 状态，记录失败时间

## 日志记录

使用 vlogger 记录关键操作：

- `MARKET_MONITOR.PRICE_SURGE`: 检测到价格涨幅
- `MARKET_MONITOR.PRICE_SURGE.TASK_CREATED`: 创建AI分析任务
- `MARKET_MONITOR.PRICE_SURGE.SUBMITTED`: 提交AI分析任务
- `MARKET_MONITOR.PRICE_SURGE.METADATA_UPDATED`: 更新持仓metadata
- `MARKET_MONITOR.ANALYSIS_UPDATE.COMPLETED`: 分析完成
- `MARKET_MONITOR.ANALYSIS_UPDATE.FAILED`: 分析失败

## 使用示例

### 查询持仓的价格涨幅分析

```python
from backend.position_listener import PositionDatabase

db = PositionDatabase()
position = db.get_position(position_id)

# 获取所有价格涨幅分析
analyses = position.metadata.get("price_surge_analyses", [])

for analysis in analyses:
    print(f"时间: {analysis['timestamp']}")
    print(f"价格变动: {analysis['price_change_pct'] * 100:.2f}%")
    print(f"状态: {analysis['status']}")
    
    if analysis['status'] == 'completed':
        print(f"驱动类型: {analysis['primary_driver']}")
        print(f"支持理由: {analysis['reasons_yes']}")
        print(f"反对理由: {analysis['reasons_no']}")
```

## 定时任务

- **市场监控**: 每5分钟执行 `monitor_markets_task`，检测价格变动
- **分析更新**: 每2分钟执行 `update_price_surge_analysis_task`，更新分析结果

## 注意事项

1. **积分消耗**: 每次Info Sniff分析消耗1积分
2. **频率限制**: 6小时内最多180积分，3天内最多1080积分
3. **异步处理**: AI分析是异步的，结果需要等待2-5分钟
4. **数据持久化**: 所有分析结果永久保存在持仓metadata中

