# Position Listener - 持仓监听系统

全新的持仓监听系统，提供交易记录、市场监控、订单状态追踪等功能。

## 核心功能

### 1. 交易记录功能
- 根据TradeAllocation数据结构记录交易信息
- 自动创建持仓记录和交易流水
- 支持订单ID关联
- 完整的交易历史追踪

### 2. 市场监控功能
- 实时监控已交易市场的价格变化
- 自动更新持仓的当前价格和盈亏
- 检测市场结算状态
- 定时任务自动执行（每5分钟）

### 3. 订单状态监控功能
- 根据orderID追踪订单状态
- 监控订单成交情况
- 监控订单撤销状态
- **订单取消自动处理**：
  - 自动解锁purse中的锁定资金
  - 自动更新关联任务的状态
  - 支持部分成交的资金计算
- 定时任务自动执行（每2分钟）

## 技术架构

### 数据库设计

系统使用独立的SQLite数据库（`positions.db`），包含三个核心表：

#### positions表（持仓表）
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,              -- 市场ID
    side TEXT NOT NULL,                   -- 交易方向（YES/NO）
    entry_price REAL NOT NULL,            -- 入场价格
    shares REAL NOT NULL,                 -- 持有份额
    invest_amount REAL NOT NULL,          -- 投资金额
    settle_day INTEGER NOT NULL,          -- 预计结算日期
    status TEXT NOT NULL DEFAULT 'open',  -- 持仓状态
    current_price REAL,                   -- 当前价格
    pnl REAL,                            -- 盈亏
    is_settled INTEGER DEFAULT 0,         -- 是否已结算
    settlement_result TEXT,               -- 结算结果
    settlement_payout REAL,               -- 结算收益
    create_time TIMESTAMP,
    update_time TIMESTAMP,
    close_time TIMESTAMP,
    metadata TEXT                         -- JSON格式元数据
)
```

#### trades表（交易记录表）
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER,                  -- 关联持仓ID
    market_id TEXT NOT NULL,              -- 市场ID
    side TEXT NOT NULL,                   -- 交易方向
    price REAL NOT NULL,                  -- 交易价格
    shares REAL NOT NULL,                 -- 交易份额
    amount REAL NOT NULL,                 -- 交易金额
    trade_type TEXT NOT NULL,             -- 交易类型（OPEN/CLOSE）
    order_id TEXT,                        -- 关联订单ID
    trade_time TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (position_id) REFERENCES positions (id)
)
```

#### orders表（订单状态表）
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,        -- 订单ID
    position_id INTEGER,                  -- 关联持仓ID
    market_id TEXT NOT NULL,              -- 市场ID
    token_id TEXT NOT NULL,               -- Token ID
    side TEXT NOT NULL,                   -- 交易方向（BUY/SELL）
    price REAL NOT NULL,                  -- 订单价格
    size REAL NOT NULL,                   -- 订单数量
    status TEXT NOT NULL DEFAULT 'pending', -- 订单状态
    filled_size REAL DEFAULT 0,           -- 已成交数量
    create_time TIMESTAMP,
    update_time TIMESTAMP,
    filled_time TIMESTAMP,
    cancelled_time TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (position_id) REFERENCES positions (id)
)
```

### Huey任务调度

系统使用Huey任务队列处理异步任务：

#### 定时任务
- `monitor_markets_task`: 每5分钟监控所有未平仓持仓的市场状态
- `monitor_orders_task`: 每2分钟监控所有待成交订单的状态

#### 手动任务
- `monitor_position_task(position_id)`: 监控单个持仓
- `monitor_order_task(order_id)`: 监控单个订单

## 使用示例

### 1. 记录交易

```python
from backend.position_listener import record_trade
from backend.types import TradeAllocation

# 创建TradeAllocation对象
allocation = TradeAllocation(
    id="market_123",
    side="YES",
    price=0.55,
    p=0.60,
    b=1.82,
    f=0.05,
    invest=100.0,
    shares=181.82,
    settle_day=30
)

# 记录交易（带订单ID）
position_id = record_trade(
    allocation=allocation,
    order_id="ORDER-123456",
    token_id="TOKEN-789"
)

print(f"创建持仓ID: {position_id}")
```

### 2. 获取持仓信息

```python
from backend.position_listener import (
    get_position,
    get_open_positions,
    get_position_summary
)

# 获取单个持仓
position = get_position(position_id)
print(f"持仓: {position.to_dict()}")

# 获取所有未平仓持仓
open_positions = get_open_positions()
print(f"未平仓数量: {len(open_positions)}")

# 获取持仓汇总
summary = get_position_summary()
print(f"总投资: {summary['total_invest']}")
print(f"总盈亏: {summary['total_pnl']}")
```

### 3. 手动监控市场

```python
from backend.position_listener import monitor_position, monitor_all_positions

# 监控单个持仓
result = monitor_position(position_id)
print(f"监控结果: {result}")

# 监控所有持仓
all_results = monitor_all_positions()
print(f"监控了 {all_results['total_positions']} 个持仓")
```

### 4. 手动监控订单

```python
from backend.position_listener import monitor_order, monitor_all_orders

# 监控单个订单
result = monitor_order("ORDER-123456")
print(f"订单状态: {result['status']}")

# 监控所有待成交订单
all_results = monitor_all_orders()
print(f"监控了 {all_results['total_orders']} 个订单")
```

### 5. 更新持仓价格

```python
from backend.position_listener import update_position_price

# 手动更新持仓价格
success = update_position_price(position_id, current_price=0.58)
if success:
    print("价格更新成功")
```

### 6. 结算持仓

```python
from backend.position_listener import settle_position

# 结算持仓
success = settle_position(
    position_id=position_id,
    settlement_result="YES",
    settlement_payout=181.82
)
if success:
    print("持仓结算完成")
```

### 7. 使用Huey任务

```python
from backend.position_listener import (
    monitor_position_task,
    monitor_order_task
)

# 提交监控任务到Huey队列
monitor_position_task(position_id)
monitor_order_task("ORDER-123456")
```

### 8. 订单取消自动处理

当订单监控检测到订单被取消时，系统会自动执行以下操作：

```python
# 订单监控会自动处理取消的订单
# 无需手动调用，以下是内部处理流程：

# 1. 检测订单状态为CANCELLED
# 2. 计算需要解锁的资金
#    - 完全未成交：解锁全部投资金额
#    - 部分成交：解锁未成交部分的资金
# 3. 调用purse.unlock_fund()解锁资金
# 4. 更新关联任务的result字段
#    - order_cancelled: true
#    - order_cancelled_time: 时间戳
#    - filled_size: 已成交数量
#    - original_size: 原始订单数量
#    - unlock_amount: 解锁金额
```

**示例场景**：

```python
# 场景1: 订单完全未成交被取消
# order_id: "0x9f1d134dfb..."
# market_id: "916392"
# clob_status: "CANCELED"
# filled_size: 0.0
# original_size: 8.26
# invest_amount: 100.0

# 系统自动执行：
# 1. purse.unlock_fund(100.0)  # 解锁全部投资金额
# 2. 更新task.result["order_cancelled"] = True
# 3. 记录TRADE级别日志

# 场景2: 订单部分成交后被取消
# filled_size: 3.0
# original_size: 8.26
# invest_amount: 100.0

# 系统自动执行：
# unfilled_ratio = (8.26 - 3.0) / 8.26 = 0.637
# unlock_amount = 100.0 * 0.637 = 63.7
# 1. purse.unlock_fund(63.7)  # 只解锁未成交部分
# 2. 更新task.result
```

## 日志系统

系统集成VLogger日志系统，提供完整的日志记录：

### 日志等级
- **INFO**: 正常操作日志
- **TRADE**: 交易证据级流水（永不采样）
- **WARN**: 警告信息
- **ERROR**: 错误信息

### 事件类型
- `POSITION.DB.INIT`: 数据库初始化
- `POSITION.CREATE`: 创建持仓
- `POSITION.UPDATE`: 更新持仓
- `POSITION.TRADE.CREATE`: 记录交易
- `POSITION.ORDER.CREATE`: 创建订单记录
- `MARKET_MONITOR.*`: 市场监控相关
- `ORDER_MONITOR.*`: 订单监控相关

### 错误码
- `E-POSITION-001`: 数据库初始化失败
- `E-POSITION-002`: 创建持仓记录失败
- `E-POSITION-003`: 更新持仓记录失败
- `E-POSITION-004`: 创建交易记录失败
- `E-POSITION-005`: 创建订单记录失败
- `E-POSITION-006`: 更新订单状态失败
- `E-POSITION-007`: 记录交易分配失败
- `E-POSITION-008~012`: 交易记录器相关错误
- `E-POSITION-013~018`: 市场监控相关错误
- `E-POSITION-019~023`: 订单监控相关错误
- `E-POSITION-024`: 订单取消资金解锁失败
- `E-POSITION-025`: 处理订单取消失败

## API参考

系统使用以下Polymarket API：

### Gamma Markets API
- `get_market(market_id)`: 获取市场信息
- 用于检查市场状态和获取当前价格

### CLOB API
- `get_order(order_id)`: 获取订单详情
- 用于查询订单成交和撤销状态

## 数据结构参考

### TradeAllocation
```python
@dataclass
class TradeAllocation:
    id: Any           # 市场ID
    side: str         # 交易方向（YES/NO）
    price: float      # 交易价格
    p: float          # 主观概率
    b: float          # 赔率
    f: float          # 仓位比例
    invest: float     # 投资金额
    shares: float     # 购买份额
    settle_day: int   # 结算日期
```

## 注意事项

1. **数据库路径**: 默认为 `./backend/position_listener/positions.db`
2. **定时任务**: 需要启动Huey worker才能执行定时任务
3. **API限流**: 注意Polymarket API的调用频率限制
4. **价格更新**: 市场监控任务每5分钟执行一次
5. **订单监控**: 订单监控任务每2分钟执行一次
6. **日志记录**: 所有交易操作都会记录TRADE级别日志

## 与VoidPoly任务流程集成

Position Listener可以与VoidPoly任务处理流程无缝集成：

```
TRADE(PROCESSING) → 执行交易 → record_trade() → 创建持仓和订单记录
                                              ↓
                                    monitor_orders_task (每2分钟)
                                              ↓
                                    订单成交 → LISTEN(WAITING)
                                              ↓
                                    monitor_markets_task (每5分钟)
                                              ↓
                                    市场结算 → settle_position()
```

## 未来扩展

- [ ] 支持批量交易记录
- [ ] 添加持仓分析和统计功能
- [ ] 支持WebSocket实时价格更新
- [ ] 添加持仓风险管理功能
- [ ] 支持多账户管理

