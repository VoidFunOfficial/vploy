# 自动止盈系统

基于多因子决策算法的智能止盈系统，支持4种策略标签和自动化执行。

## 系统架构

```
surplus_dog/
├── surplus_cal.py       # 核心决策算法（多因子模型）
├── easy_info.py         # 数据获取模块（实时+历史）
├── auto_surplus.py      # 自动止盈执行模块
├── surplus_monitor.py   # 监控集成模块（定时任务）
└── README.md           # 本文档
```

## 核心功能

### 1. 多因子决策算法 (`surplus_cal.py`)

**10个决策因子：**
- `over`: 超涨因子（价格相对历史的z-score）
- `vol`: 放量因子（交易量异常）
- `exh`: 疲劳因子（价格加速度反转）
- `rsi`: RSI超买因子
- `para`: 抛物线因子（快慢趋势比）
- `book`: 订单簿失衡因子
- `spread`: 点差扩大因子
- `sat`: 收益饱和因子
- `time`: 时间衰减因子
- `dd`: 回撤因子

**4种策略标签：**

| 标签 | 适用场景 | 参数特点 |
|------|---------|---------|
| `short-term` | tau < 7天 | 快窗口10，阈值0.72，重视vol/exh |
| `long-term` | tau > 10天 | 慢窗口120，阈值0.78，重视sat/time |
| `speculation` | 入场价 < 0.3 | 阈值0.70，min_profit_mult=2.0 |
| `consensus` | 入场价 > 0.7 | 阈值0.65，重视sat因子(30%) |

### 2. 数据获取模块 (`easy_info.py`)

**实时数据：**
```python
from backend.surplus_dog.easy_info import get_market_realtime_data

# token_id 已经是具体的 YES 或 NO token 地址，无需指定 side
data = get_market_realtime_data(token_id="0x123...")
# 返回: current_price, bid_depth, ask_depth, spread, mid_price
```

**历史数据：**
```python
from backend.surplus_dog.easy_info import get_market_history_data

history = get_market_history_data(
    token_id="0x123...",
    interval="1d",  # 1h, 6h, 1d, 1w, 1m, max
    fidelity=60     # 分钟
)
# 返回: prices, volumes, spreads, timestamps
```

**完整决策数据：**
```python
from backend.surplus_dog.easy_info import prepare_decision_data
from datetime import datetime

# token_id 已经是具体的 YES 或 NO token 地址，无需指定 side
data = prepare_decision_data(
    token_id="0x123...",
    entry_time=datetime(2024, 1, 1),
    lookback_hours=168  # 7天
)
```

### 3. 自动止盈执行 (`auto_surplus.py`)

**单个持仓决策：**
```python
from backend.surplus_dog.auto_surplus import auto_surplus_decision

# token_id 已经是具体的 YES 或 NO token 地址
result = auto_surplus_decision(
    position_id=123,
    token_id="0x123...",
    tag="short-term",  # 可选，自动推断
    execute=True       # 是否执行卖出
)

# 返回结果：
{
    "success": True,
    "position_id": 123,
    "tag": "short-term",
    "decision": {
        "action": "SELL",  # 或 "HOLD"
        "score": 0.75,
        "threshold": 0.72,
        "suggested_sell_fraction": 0.8,
        "reason": "Score=0.75 ≥ 0.72 → SELL",
        "factors": {...},
        "raw": {...}
    },
    "executed": True,
    "sell_result": {...}
}
```

**批量止盈检查：**
```python
from backend.surplus_dog.auto_surplus import auto_surplus_all_positions

result = auto_surplus_all_positions(execute=True)
```

### 4. 监控集成模块 (`surplus_monitor.py`)

**手动触发监控：**
```python
from backend.surplus_dog.surplus_monitor import SurplusMonitor

monitor = SurplusMonitor()

# 监控单个持仓
result = monitor.monitor_position_with_surplus(
    position_id=123,
    execute_sell=True
)

# 监控所有持仓
result = monitor.monitor_all_positions_with_surplus(
    execute_sell=True
)
```

**定时任务（自动执行）：**
- `surplus_monitor_task()`: 每10分钟执行一次，自动监控所有持仓
- `surplus_monitor_position_task(position_id)`: 异步监控单个持仓

## 使用流程

### 场景1：手动检查单个持仓

```python
from backend.surplus_dog.auto_surplus import auto_surplus_decision

# 仅检查，不执行
result = auto_surplus_decision(
    position_id=123,
    token_id="token_xxx",
    execute=False
)

print(f"决策: {result['decision']['action']}")
print(f"评分: {result['decision']['score']}")
print(f"原因: {result['decision']['reason']}")
```

### 场景2：自动执行止盈

```python
from backend.surplus_dog.surplus_monitor import SurplusMonitor

monitor = SurplusMonitor()
result = monitor.monitor_all_positions_with_surplus(execute_sell=True)

print(f"检查了 {result['checked']} 个持仓")
print(f"触发卖出信号: {result['sell_signals']} 个")
```

### 场景3：集成到持仓监听

```python
from backend.position_listener.market_monitor import monitor_position_task
from backend.surplus_dog.surplus_monitor import surplus_monitor_position_task

# 在交易成功后，启动监控任务
position_id = 123
surplus_monitor_position_task(position_id, execute_sell=True)
```

## 参数调优指南

### 调整策略参数

编辑 `surplus_cal.py` 中的 `get_params()` 函数：

```python
if tag == "short-term":
    return Params(
        fast_window=10,      # 快窗口（数据点）
        slow_window=40,      # 慢窗口
        accel_k=3,           # 加速度计算窗口
        rsi_period=9,        # RSI周期
        threshold=0.72,      # 决策阈值
        hard_exit_price=0.97,# 硬退出价格
        min_profit_abs=0.03, # 最小绝对利润
        min_profit_mult_entry=0.0,  # 最小利润倍数
        dd_trigger=0.015,    # 回撤触发阈值
        weights={            # 因子权重
            "over": 0.14,
            "vol": 0.20,
            "exh": 0.18,
            ...
        }
    )
```

### 权重调整建议

- **短期交易**: 提高 `vol`, `exh`, `book` 权重
- **长期持有**: 提高 `sat`, `time` 权重
- **投机策略**: 提高 `over`, `para` 权重
- **共识策略**: 提高 `sat`, `book` 权重

## 错误码

| 错误码 | 说明 |
|--------|------|
| E-SURPLUS-001 | 获取实时市场数据失败 |
| E-SURPLUS-002 | 获取历史市场数据失败 |
| E-SURPLUS-003 | 准备决策数据失败 |
| E-SURPLUS-004 | 执行卖单失败 |
| E-SURPLUS-005 | 止盈决策失败 |
| E-SURPLUS-006 | 批量止盈检查失败 |
| E-SURPLUS-007 | 监控持仓失败 |
| E-SURPLUS-008 | 批量监控失败 |
| E-SURPLUS-009 | 定时止盈监控失败 |
| E-SURPLUS-010 | 监控持仓任务失败 |

## 注意事项

1. **数据依赖**: 需要至少3个历史数据点才能执行决策
2. **Token ID**:
   - 持仓的 `metadata` 中必须包含 `token_id` 字段
   - `token_id` 必须是具体的 YES 或 NO token 地址（链上地址）
   - 系统不再需要 `side` 参数，因为 token_id 本身已经代表了方向
3. **只止盈**: 系统只在盈利时触发卖出，亏损时始终返回 HOLD
4. **分批卖出**: `suggested_sell_fraction` 支持部分卖出（0-1）
5. **价格使用**: 使用 bid 价格（卖出时能获得的价格）进行决策

