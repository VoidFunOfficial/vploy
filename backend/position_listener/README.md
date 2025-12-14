# Polymarket 仓位监听模块

## 概述

仓位监听模块提供了对Polymarket仓位的实时监听和价格更新功能。通过Huey任务队列实现周期性轮询,自动更新仓位的当前价格和市场状态,并支持阈值触发检测。

## 功能特性

- ✅ **周期性监听**: 每5分钟自动轮询所有活跃仓位
- ✅ **价格更新**: 实时获取并更新市场当前价格
- ✅ **状态跟踪**: 自动检测市场是否已结束
- ✅ **阈值检测**: 支持百分比和绝对值两种阈值触发方式
- ✅ **日志记录**: 使用VLogger记录所有监听活动和异常
- ✅ **独立数据库**: 使用独立的listen.db数据库存储数据

## 数据库说明

### 数据库位置

- **数据库文件**: `backend/position_listener/listen.db`
- **独立存储**: 不依赖系统配置数据库,完全独立管理

### position_listen 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键,自增 |
| market_id | TEXT | 市场ID |
| marks | TEXT | 标记/备注信息 |
| buy_price | REAL | 买入价格 (0-1之间) |
| buy_side | TEXT | 买入方向 (YES/NO) |
| shares | REAL | 持仓数量 |
| current_price | REAL | 当前价格 (自动更新) |
| market_closed | INTEGER | 市场是否已结束 (0/1) |
| threshold_config | TEXT | 阈值配置 (JSON格式) |
| is_active | INTEGER | 是否激活 (0/1) |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 使用方法

### 1. 添加仓位监听

```python
from backend.sys_configs import add_position_listen
import json

# 配置阈值
threshold_config = json.dumps({
    "percent": 0.1,      # 价格变动10%触发
    "absolute": 0.05     # 价格绝对变动0.05触发
})

# 添加监听
success = add_position_listen(
    market_id="705811",
    buy_price=0.52,
    buy_side="YES",
    marks="我的第一个仓位",
    shares=100.0,
    threshold_config=threshold_config
)
```

### 2. 查询仓位列表

```python
from backend.sys_configs import get_position_listen_list

# 获取所有活跃仓位
positions = get_position_listen_list(is_active=True)

for pos in positions:
    print(f"市场ID: {pos['market_id']}")
    print(f"买入价格: {pos['buy_price']}")
    print(f"当前价格: {pos['current_price']}")
    print(f"市场状态: {'已结束' if pos['market_closed'] else '活跃'}")
```

### 3. 手动触发监听

```python
from backend.position_listener import monitor_all_positions

# 手动执行一次监听
result = monitor_all_positions()

print(f"总仓位数: {result['total']}")
print(f"成功更新: {result['success']}")
print(f"更新失败: {result['failed']}")
print(f"已结束市场: {result['closed_markets']}")
```

### 4. 更新仓位信息

```python
from backend.sys_configs import update_position_listen

# 更新仓位
success = update_position_listen(
    listen_id=1,
    marks="更新后的备注",
    is_active=True
)
```

### 5. 停用仓位监听

```python
from backend.sys_configs import deactivate_position_listen

# 软删除(停用)
success = deactivate_position_listen(listen_id=1)
```

## 阈值配置说明

阈值配置使用JSON格式存储,支持两种触发方式:

### 百分比阈值

```json
{
    "percent": 0.1
}
```

当价格变动超过10%时触发。

### 绝对值阈值

```json
{
    "absolute": 0.05
}
```

当价格绝对变动超过0.05时触发。

### 组合阈值

```json
{
    "percent": 0.1,
    "absolute": 0.05
}
```

满足任一条件即触发。

## 定时任务配置

仓位监听任务已自动注册到Huey任务队列中:

- **任务名称**: `position_monitor`
- **执行频率**: 每5分钟
- **任务类型**: cron表达式 `*/5 * * * *`
- **执行器**: 动态调度器 (DynamicScheduler)

### 修改执行频率

可以通过修改定时任务配置来调整执行频率:

```python
from backend.task_manager import update_scheduled_task

# 修改为每10分钟执行一次
update_scheduled_task(
    name="position_monitor",
    schedule="*/10 * * * *"
)
```

## 日志事件类型

模块使用以下VLogger事件类型:

| 事件类型 | 说明 |
|---------|------|
| POSITION_MONITOR.MONITOR_START | 开始监听所有仓位 |
| POSITION_MONITOR.POSITIONS_LOADED | 加载活跃仓位列表 |
| POSITION_MONITOR.UPDATE_START | 开始更新单个仓位 |
| POSITION_MONITOR.UPDATE_SUCCESS | 仓位更新成功 |
| POSITION_MONITOR.UPDATE_FAILED | 仓位更新失败 |
| POSITION_MONITOR.THRESHOLD_TRIGGERED | 阈值触发 |
| POSITION_MONITOR.MONITOR_COMPLETE | 监听完成 |
| POSITION_MONITOR.MARKET_NOT_FOUND | 市场未找到 |
| POSITION_MONITOR.NO_PRICE_DATA | 无价格数据 |
| POSITION_MONITOR.INVALID_PRICE_FORMAT | 价格格式无效 |
| POSITION_MONITOR.GET_PRICE_ERROR | 获取价格失败 |
| POSITION_MONITOR.CHECK_STATUS_ERROR | 检查状态失败 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| E-PM-001 | 价格解析失败 |
| E-PM-002 | 获取市场价格失败 |
| E-PM-003 | 检查市场状态失败 |
| E-PM-004 | 更新仓位数据失败 |
| E-PM-005 | 更新仓位数据异常 |

## 测试

运行测试脚本:

```bash
python test_position_monitor.py
```

测试脚本会执行以下操作:
1. 添加测试仓位
2. 查询仓位列表
3. 执行监听任务
4. 查看更新后的仓位状态

## 注意事项

1. **价格格式**: 买入价格必须在0到1之间
2. **买入方向**: 只支持 "YES" 或 "NO"
3. **市场ID**: 必须是有效的Polymarket市场ID
4. **阈值配置**: 必须是有效的JSON字符串
5. **API限制**: 注意Polymarket API的调用频率限制

## 架构说明

```
backend/position_listener/
├── __init__.py              # 模块导出
├── position_monitor.py      # 核心监听逻辑
└── README.md               # 本文档

backend/sys_configs/
├── position_listen_config.py  # 数据库操作
└── config_manager.py         # 数据库表结构

backend/task_manager/
├── scheduler.py             # 定时任务注册
└── dynamic_scheduler.py     # 任务执行器
```

## 工作流程

1. **初始化**: 系统启动时自动注册定时任务
2. **周期执行**: 每5分钟触发一次监听任务
3. **获取仓位**: 从数据库加载所有活跃仓位
4. **更新数据**: 
   - 调用Polymarket API获取市场数据
   - 解析价格和状态信息
   - 更新数据库记录
5. **阈值检测**: 
   - 计算价格变动
   - 检查是否触发阈值
   - 记录触发日志
6. **完成**: 返回统计结果

## 未来扩展

当前版本仅实现了基础监听和日志记录功能,未来可以扩展:

- [ ] 阈值触发后的自动交易
- [ ] 邮件/短信通知
- [ ] WebSocket实时推送
- [ ] 收益统计和报表
- [ ] 风险预警机制
- [ ] 多账户支持

