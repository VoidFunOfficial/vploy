# Position Listener 集成说明

本文档说明如何将新的Position Listener系统集成到VoidPoly任务流程中。

## 已完成的集成

### 1. task_manager/tasks.py 集成

已修改 `handle_trade_processing` 函数，使用新的position_listener系统：

#### 修改前（旧系统）
```python
from ..position_listener.database import get_db

# 添加仓位监听记录（包含订单信息）
position_id = db.add_position(
    market_id=market.get("id"),
    buy_price=cost,
    buy_side=side,
    marks=marks_str,
    shares=shares,
    ...
)
```

#### 修改后（新系统）
```python
from ..position_listener import record_trade, create_order_record
from ..types import TradeAllocation

# 创建TradeAllocation对象
trade_allocation = TradeAllocation(
    id=market.get("id"),
    side=side,
    price=cost,
    p=allocation_data.get("p", 0.5),
    b=allocation_data.get("b", 2.0),
    f=allocation_data.get("f", 0.0),
    invest=dollars,
    shares=shares,
    settle_day=allocation_data.get("settle_day", 30)
)

# 记录交易到position_listener
position_id = record_trade(
    allocation=trade_allocation,
    order_id=order_id,
    token_id=clobtoken
)

# 创建订单记录
if order_id:
    create_order_record(
        order_id=order_id,
        position_id=position_id,
        market_id=market.get("id"),
        token_id=clobtoken,
        side="BUY",
        price=cost,
        size=shares,
        metadata={"task_id": task.id, "trade_result": trade_result}
    )
```

### 2. LISTEN阶段集成

已修改 `handle_listen_processing` 函数，集成订单监控：

```python
from ..position_listener import monitor_order

# 使用position_listener监控订单
monitor_result = monitor_order(order_id)

# 同时从CLOB API获取订单详情
order_info = get_order(order_id)
```

## 任务流程说明

### 完整流程

```
TRADE(PROCESSING)
    ↓
执行交易 (auto_trade_exec.trade)
    ↓
创建TradeAllocation对象
    ↓
record_trade() → 创建Position和Trade记录
    ↓
create_order_record() → 创建Order记录
    ↓
转换到 LISTEN(WAITING)
    ↓
用户批准 → LISTEN(PROCESSING)
    ↓
monitor_order() → 检查订单状态
    ↓
订单成交 → FINISHED
```

### 后台监控任务

同时，Huey定时任务会自动运行：

```
monitor_orders_task (每2分钟)
    ↓
检查所有待成交订单
    ↓
更新订单状态到数据库

monitor_markets_task (每5分钟)
    ↓
检查所有未平仓持仓
    ↓
更新市场价格和盈亏
    ↓
检测市场结算
```

## 数据流

### TRADE阶段数据流

1. **输入数据**（来自task.result）：
   - `decision`: 决策结果
   - `allocation`: 交易分配信息
     - `side`: YES/NO
     - `dollars`: 投资金额
     - `shares`: 购买份额
     - `cost`: 价格
     - `p`, `b`, `f`: 概率、赔率、仓位比例
     - `settle_day`: 结算日期

2. **执行交易**：
   - 调用 `auto_trade_exec.trade()`
   - 获得 `order_id` 和交易结果

3. **记录到position_listener**：
   - 创建 `Position` 记录（持仓）
   - 创建 `Trade` 记录（交易流水）
   - 创建 `Order` 记录（订单追踪）

4. **输出数据**（保存到task.result）：
   - `position_id`: 持仓ID
   - `order_id`: 订单ID
   - `order_created_at`: 订单创建时间
   - 其他交易信息

### LISTEN阶段数据流

1. **输入数据**（来自task.result）：
   - `order_id`: 订单ID
   - `order_created_at`: 订单创建时间

2. **监控订单**：
   - 调用 `monitor_order(order_id)`
   - position_listener自动更新订单状态

3. **判断逻辑**：
   - 订单成交 → 任务完成
   - 订单取消/失败 → 执行扫单
   - 超过10分钟未成交 → 取消订单并扫单
   - 未超时 → 继续等待

## 数据库对比

### 旧系统 vs 新系统

| 功能 | 旧系统 | 新系统 |
|------|--------|--------|
| 数据库文件 | `positions.db` | `positions.db` |
| 持仓表 | `positions` | `positions` |
| 交易记录 | 无独立表 | `trades` 表 |
| 订单追踪 | 字段在positions表 | `orders` 独立表 |
| 数据模型 | 字典 | 数据类（Position/Trade/Order） |
| 状态管理 | 字符串 | 枚举（PositionStatus/OrderStatus） |
| 监控任务 | 无 | Huey定时任务 |

## 迁移注意事项

### 1. 数据库兼容性

新系统使用完全独立的数据库结构，不会影响旧数据。如果需要迁移旧数据：

```python
# 迁移脚本示例（需要根据实际情况调整）
from backend.position_listener import record_trade
from backend.types import TradeAllocation

# 读取旧数据
old_positions = old_db.get_all_positions()

# 转换为新格式
for old_pos in old_positions:
    allocation = TradeAllocation(
        id=old_pos['market_id'],
        side=old_pos['buy_side'],
        price=old_pos['buy_price'],
        # ... 其他字段
    )
    record_trade(allocation, order_id=old_pos.get('order_id'))
```

### 2. API变化

| 旧API | 新API |
|-------|-------|
| `db.add_position()` | `record_trade()` |
| `db.get_position()` | `get_position()` |
| `db.update_position()` | `update_position_price()` |
| 无 | `settle_position()` |
| 无 | `monitor_order()` |
| 无 | `monitor_position()` |

### 3. 导入路径变化

```python
# 旧导入
from ..position_listener.database import get_db

# 新导入
from ..position_listener import (
    record_trade,
    get_position,
    monitor_order,
    monitor_position
)
```

## 测试建议

### 1. 单元测试

测试各个功能模块：

```python
# 测试交易记录
def test_record_trade():
    allocation = TradeAllocation(...)
    position_id = record_trade(allocation, order_id="TEST-001")
    assert position_id > 0

# 测试订单监控
def test_monitor_order():
    result = monitor_order("TEST-001")
    assert result['success'] == True
```

### 2. 集成测试

测试完整的任务流程：

```python
# 创建TRADE任务
task = create_task(stage=TaskStage.TRADE, status=TaskStatus.PROCESSING)

# 执行任务
result = handle_trade_processing(task)

# 验证结果
assert result['status'] == 'traded'
assert 'position_id' in result
assert 'order_id' in result
```

### 3. 监控任务测试

测试Huey定时任务：

```python
# 手动触发监控任务
from backend.position_listener import monitor_all_positions, monitor_all_orders

# 测试市场监控
market_result = monitor_all_positions()
assert market_result['success'] == True

# 测试订单监控
order_result = monitor_all_orders()
assert order_result['success'] == True
```

## 启动Huey Worker

为了让定时监控任务运行，需要启动Huey worker：

```bash
# 在项目根目录执行
huey_consumer backend.task_manager.tasks.huey
```

或者使用项目的启动脚本（如果有）。

## 常见问题

### Q1: 旧的position数据怎么办？

A: 新系统使用独立的数据库，不会影响旧数据。可以保留旧数据作为历史记录，或编写迁移脚本转换到新系统。

### Q2: 监控任务会重复监控吗？

A: 不会。监控任务只处理未完成的订单和未平仓的持仓。一旦订单成交或持仓结算，就不会再监控。

### Q3: 如果Huey worker没有运行会怎样？

A: 定时监控任务不会执行，但手动调用的监控函数仍然可以工作。建议在生产环境中始终运行Huey worker。

### Q4: 如何查看监控日志？

A: 所有监控操作都会记录到VLogger，可以通过日志系统查看：
- 事件类型：`MARKET_MONITOR.*`, `ORDER_MONITOR.*`
- 错误码：`E-POSITION-013` 到 `E-POSITION-023`

## 下一步

1. ✅ 完成task_manager集成
2. ✅ 实现监控任务
3. ⏳ 编写单元测试
4. ⏳ 编写集成测试
5. ⏳ 生产环境部署
6. ⏳ 监控和优化

