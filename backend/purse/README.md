# Purse - 本地钱包管理模块

基于SQLite实现的单例模式钱包管理系统，专为交易系统设计。

## 特性

- ✅ **单例模式**: 全局唯一实例，线程安全
- ✅ **SQLite持久化**: 数据持久化存储，支持事务
- ✅ **资金管理**: 总资金、锁定资金、可用现金自动计算
- ✅ **盈亏追踪**: 实时记录盈利、亏损、预期盈利
- ✅ **市场统计**: 成功/失败市场数、胜率统计
- ✅ **VLogger集成**: 完整的日志记录和审计
- ✅ **线程安全**: 所有操作都有线程锁保护

## 数据库字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_fund` | REAL | 总资金（初始投入 + 盈利 - 亏损） |
| `locked_fund` | REAL | 锁定资金（当前投注中的资金） |
| `available_cash` | REAL | 可用现金（= total_fund - locked_fund） |
| `loss` | REAL | 总亏损（已实现亏损） |
| `expect_profit` | REAL | 预期盈利（未结算订单的潜在盈利） |
| `real_profit` | REAL | 实际盈利（已结算订单的实际盈利） |
| `success_market` | INTEGER | 成功市场数（盈利的市场数量） |
| `lost_market` | INTEGER | 失败市场数（亏损的市场数量） |

## 快速开始

### 基础使用

```python
from backend.purse import Purse, get_purse

# 获取钱包实例（单例模式）
purse = Purse.get_instance()
# 或使用便捷函数
purse = get_purse()

# 初始化钱包（设置初始资金）
purse.initialize(total_fund=10000.0)

# 查询钱包状态
status = purse.get_status()
print(status)
# {
#     'total_fund': 10000.0,
#     'locked_fund': 0.0,
#     'available_cash': 10000.0,
#     'loss': 0.0,
#     'expect_profit': 0.0,
#     'real_profit': 0.0,
#     'success_market': 0,
#     'lost_market': 0,
#     'updated_at': '2025-12-07 10:30:00'
# }
```

### 资金锁定与解锁

```python
# 下注时锁定资金
purse.lock_fund(100.0)  # 锁定100元用于下注

# 取消订单时解锁资金
purse.unlock_fund(100.0)  # 解锁100元

# 查询可用现金
available = purse.get_available_cash()
print(f"可用现金: {available}")
```

### 盈亏记录

```python
# 记录盈利（订单结算后）
# 假设下注100元，盈利50元，总共收回150元
purse.lock_fund(100.0)  # 先锁定资金
purse.record_profit(
    amount=50.0,        # 盈利金额
    unlock_amount=100.0  # 解锁本金
)

# 记录亏损（订单结算后）
# 假设下注100元，亏损30元，收回70元
purse.lock_fund(100.0)  # 先锁定资金
purse.record_loss(
    amount=30.0,        # 亏损金额
    unlock_amount=70.0  # 解锁剩余本金
)
```

### 预期盈利管理

```python
# 更新预期盈利（增量更新）
purse.update_expect_profit(50.0)   # 增加50元预期盈利
purse.update_expect_profit(-20.0)  # 减少20元预期盈利

# 设置预期盈利（直接设置）
purse.set_expect_profit(100.0)  # 设置预期盈利为100元
```

### 盈亏统计

```python
# 获取盈亏汇总
summary = purse.get_profit_loss_summary()
print(summary)
# {
#     'loss': 300.0,
#     'expect_profit': 100.0,
#     'real_profit': 500.0,
#     'net_profit': 200.0,  # 净盈利 = real_profit - loss
#     'success_market': 15,
#     'lost_market': 5,
#     'total_market': 20,
#     'win_rate': 75.0  # 胜率 = 15/20 * 100%
# }
```

### 资金追加与提取

```python
# 追加资金
purse.add_fund(5000.0)  # 追加5000元

# 提取资金
purse.withdraw_fund(2000.0)  # 提取2000元
```

### 重置钱包

```python
# 重置钱包（清空所有数据）
purse.reset()
```

## 完整交易流程示例

```python
from backend.purse import get_purse

# 1. 初始化钱包
purse = get_purse()
purse.initialize(total_fund=10000.0)

# 2. 下注前锁定资金
bet_amount = 100.0
if purse.lock_fund(bet_amount):
    print(f"成功锁定 {bet_amount} 元")
    
    # 3. 设置预期盈利
    expected = 50.0
    purse.set_expect_profit(expected)
    
    # 4. 订单结算
    # 情况A: 盈利
    actual_profit = 45.0
    purse.record_profit(
        amount=actual_profit,
        unlock_amount=bet_amount
    )
    purse.set_expect_profit(0.0)  # 清空预期盈利
    
    # 情况B: 亏损
    # loss_amount = 30.0
    # remaining = bet_amount - loss_amount
    # purse.record_loss(
    #     amount=loss_amount,
    #     unlock_amount=remaining
    # )
    # purse.set_expect_profit(0.0)

# 5. 查看最终状态
status = purse.get_status()
summary = purse.get_profit_loss_summary()
print(f"钱包状态: {status}")
print(f"盈亏汇总: {summary}")
```

## API参考

### 核心方法

- `get_instance(db_path="purse.db")` - 获取单例实例
- `initialize(total_fund)` - 初始化钱包总资金
- `get_status()` - 获取钱包完整状态
- `reset()` - 重置钱包（清空所有数据）

### 资金操作

- `lock_fund(amount)` - 锁定资金
- `unlock_fund(amount)` - 解锁资金
- `add_fund(amount)` - 追加资金
- `withdraw_fund(amount)` - 提取资金

### 盈亏记录

- `record_profit(amount, unlock_amount)` - 记录盈利
- `record_loss(amount, unlock_amount)` - 记录亏损
- `update_expect_profit(amount)` - 更新预期盈利（增量）
- `set_expect_profit(amount)` - 设置预期盈利（直接设置）

### 查询方法

- `get_available_cash()` - 获取可用现金
- `get_total_fund()` - 获取总资金
- `get_locked_fund()` - 获取锁定资金
- `get_profit_loss_summary()` - 获取盈亏汇总

## 日志事件

Purse模块集成了VLogger日志系统，记录以下事件：

| 事件 | 等级 | 说明 |
|------|------|------|
| `PURSE.INIT` | INFO | 钱包管理器初始化 |
| `PURSE.DB.INIT` | INFO | 数据库初始化 |
| `PURSE.INIT.SUCCESS` | INFO | 钱包资金初始化成功 |
| `PURSE.LOCK.SUCCESS` | INFO | 资金锁定成功 |
| `PURSE.UNLOCK.SUCCESS` | INFO | 资金解锁成功 |
| `PURSE.PROFIT.RECORD` | TRADE | 记录盈利（交易级日志） |
| `PURSE.LOSS.RECORD` | TRADE | 记录亏损（交易级日志） |
| `PURSE.ADD.SUCCESS` | INFO | 追加资金成功 |
| `PURSE.WITHDRAW.SUCCESS` | INFO | 提取资金成功 |
| `PURSE.RESET` | WARN | 钱包重置 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| `E-PURSE-001` | 数据库操作失败 |
| `E-PURSE-002` | 初始资金不能为负数 |
| `E-PURSE-003` | 锁定金额必须大于0 |
| `E-PURSE-004` | 可用资金不足（锁定失败） |
| `E-PURSE-005` | 解锁金额必须大于0 |
| `E-PURSE-006` | 锁定资金不足（解锁失败） |
| `E-PURSE-007` | 解锁金额必须大于0（记录盈利） |
| `E-PURSE-008` | 锁定资金不足（记录盈利） |
| `E-PURSE-009` | 亏损金额不能为负数 |
| `E-PURSE-010` | 锁定资金不足（记录亏损） |
| `E-PURSE-011` | 钱包重置 |
| `E-PURSE-012` | 追加资金必须大于0 |
| `E-PURSE-013` | 提取资金必须大于0 |
| `E-PURSE-014` | 可用资金不足（提取失败） |

## 注意事项

1. **单例模式**: Purse使用单例模式，整个应用只有一个实例
2. **线程安全**: 所有操作都有线程锁保护，可以在多线程环境中安全使用
3. **事务支持**: 所有数据库操作都在事务中执行，确保数据一致性
4. **资金计算**: `available_cash = total_fund - locked_fund` 自动维护
5. **盈亏记录**: 使用TRADE级别日志，永不采样，长期保留
6. **数据库位置**: 默认在项目根目录创建`purse.db`文件

## 数据库文件

数据库文件默认存储在项目根目录：
- 文件名: `purse.db`
- 格式: SQLite3
- 表名: `purse_status`
- 记录数: 1（单例记录，id=1）

