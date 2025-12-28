# Position Listener 与 Record 模块集成文档

## 概述

本文档描述了 `position_listener` 模块与 `backend/record/` 模块的集成方案,实现订单成交时自动记录交易信息到历史记录系统。

## 集成目标

1. **实时同步**: 当订单成交时,除了更新 position_listener 中的持仓份额外,还需要同步调用 record 模块的 `update_info` 方法记录交易操作
2. **自动化**: 在 order_monitor.py 的订单监控逻辑中,当检测到订单状态变化时自动调用 record 模块
3. **数据一致性**: 确保两个系统的数据保持一致
   - position_listener 负责实时持仓管理和订单状态跟踪
   - record 模块负责历史交易记录和日报统计

## 实现方案

### 1. 核心修改

#### 1.1 导入 record 模块

在 `order_monitor.py` 中添加:
```python
from ..record import RecordManager
from ..polymarket_api import GammaMarketsAPI
```

#### 1.2 初始化 RecordManager

在 `OrderMonitor.__init__()` 中:
```python
self.record_manager = RecordManager()
```

#### 1.3 辅助方法

添加两个辅助方法:

**获取市场结算日期**:
```python
def _get_market_end_date(self, market_id: str) -> Optional[str]:
    """从 GammaMarketsAPI 获取市场的结算日期 (yyyy-mm-dd)"""
```

**记录交易到 record 模块**:
```python
def _record_trade_to_record_module(
    self,
    position_id: int,
    market_id: str,
    filled_size: float,
    price: float
):
    """将成交信息记录到 record 模块"""
```

### 2. 处理场景

#### 2.1 订单完全成交 (FILLED/MATCHED)

在 `monitor_order()` 方法中:
```python
if clob_status == "MATCHED" or size_matched >= original_size:
    # 更新订单状态
    self.db.update_order_status(order_id, OrderStatus.FILLED, filled_size=size_matched)
    
    # 更新持仓份额
    if new_filled > 0 and order.position_id:
        self.db.update_position_shares(order.position_id, new_filled)
        
        # 记录到 record 模块
        self._record_trade_to_record_module(
            position_id=order.position_id,
            market_id=order.market_id,
            filled_size=new_filled,
            price=order.price
        )
```

#### 2.2 订单部分成交 (PARTIAL)

在 `monitor_order()` 方法中:
```python
elif size_matched > 0:
    # 计算新增成交量
    previous_filled = order.filled_size or 0.0
    new_filled = size_matched - previous_filled
    
    # 更新订单状态
    self.db.update_order_status(order_id, OrderStatus.PENDING, filled_size=size_matched)
    
    # 更新持仓份额并记录
    if new_filled > 0 and order.position_id:
        self.db.update_position_shares(order.position_id, new_filled)
        
        # 记录到 record 模块
        self._record_trade_to_record_module(
            position_id=order.position_id,
            market_id=order.market_id,
            filled_size=new_filled,
            price=order.price
        )
```

#### 2.3 订单取消 (CANCELLED)

订单取消时**不需要**额外记录到 record 模块,因为:
- 如果完全未成交,没有交易发生
- 如果部分成交,已经在之前的部分成交时记录过了

### 3. 批量处理

在 `process_monitor_results()` 方法中,同样的逻辑应用于批量处理场景。

## 数据流

```
订单成交 (CLOB API)
    ↓
OrderMonitor.monitor_order()
    ↓
更新订单状态 (orders表)
    ↓
更新持仓份额 (positions表)
    ↓
记录到 record 模块 (operations表)
    ↓
用于日报统计和历史查询
```

## 传递参数

调用 `record.update_info()` 时传递的参数:

- **market_id**: 从 order.market_id 获取
- **side**: 从 position.side 获取 (YES/NO)
- **end_date**: 通过 GammaMarketsAPI 获取市场的结算日期 (yyyy-mm-dd)
- **operation**: 固定为 'BUY'
- **price**: 从 order.price 获取 (成交价格)
- **amount**: 新增成交数量 (new_filled)
- **tips**: 自动生成的备注信息

## 错误处理

1. **获取结算日期失败**: 记录警告日志,跳过记录到 record 模块
2. **持仓不存在**: 记录警告日志,跳过记录
3. **记录失败**: 捕获异常并记录错误日志,不影响订单状态更新

## 日志记录

- `ORDER_MONITOR.RECORD.SUCCESS`: 成功记录到 record 模块
- `ORDER_MONITOR.RECORD.NO_POSITION`: 持仓不存在
- `ORDER_MONITOR.RECORD.NO_END_DATE`: 无法获取结算日期
- `ORDER_MONITOR.RECORD.ERROR`: 记录失败
- `ORDER_MONITOR.END_DATE.ERROR`: 获取结算日期失败

## 注意事项

1. **增量记录**: 只记录新增成交量,避免重复记录
2. **异步处理**: record 模块的调用不应阻塞订单状态更新
3. **容错性**: record 模块调用失败不应影响 position_listener 的核心功能
4. **数据一致性**: 确保 position_listener 和 record 模块记录的数据一致

## 测试建议

1. 测试完全成交场景
2. 测试部分成交场景
3. 测试多次部分成交场景
4. 测试订单取消场景
5. 测试获取结算日期失败的容错处理
6. 验证 record 模块中的数据与 position_listener 一致

