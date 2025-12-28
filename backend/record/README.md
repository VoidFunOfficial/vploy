# Record Manager 模块

## 概述

Record Manager 模块负责管理投资记录、自动结算和日报生成。

## 核心功能

### 1. 自动结算 (auto_settle)

自动检测并结算已到达结算日期的持仓。

**功能特点：**
- 检测所有活跃持仓的结算日期
- 使用 GammaMarketsAPI 获取市场当前状态
- 对于已结算的市场（active=False），获取最终价格（0或1）
- 自动调用 update_info 记录 SETTLE 操作

**使用示例：**
```python
from backend.record.core import RecordManager

manager = RecordManager()
result = manager.auto_settle()

print(f"Settled {result['settled_count']} positions")
print(f"Total settled amount: ${result['settled_amount']:.2f}")
```

**返回值：**
```python
{
    "settled_count": 5,           # 结算的持仓数量
    "settled_amount": 1250.50,    # 结算总金额
    "errors": []                  # 错误列表
}
```

### 2. 日报记录 (record_daily)

自动计算并记录每日数据统计。

**计算内容：**
- 当日总收益（未实现）
- 当日结算金额
- 当日新投资金额
- 当前锁定资金
- 当前可用资金

**使用示例：**
```python
manager = RecordManager()
success = manager.record_daily()

if success:
    print("Daily summary recorded successfully")
```

### 3. 生成日报 (generate_today_report)

生成当日交易和收益的详细报告。

**报告内容：**
- 资金状态（总资金、可用资金、锁定资金）
- 当日活动（新投资、结算金额、未实现盈亏）
- 持仓状态（活跃持仓数、当日结算数）
- 操作统计

**使用示例：**
```python
manager = RecordManager()
report = manager.generate_today_report()

# 打印格式化报告
print(report['report_text'])

# 访问具体数据
print(f"Active positions: {report['active_positions']}")
print(f"Today's profit: ${report['profit_today']:.2f}")
```

**报告格式：**
```
=== Daily Report for 2025-12-27 ===

Fund Status:
  Total Fund:      $10000.00
  Available Cash:  $7500.00
  Locked Fund:     $2500.00

Today's Activity:
  New Investment:  $500.00
  Settled Amount:  $1200.00
  Unrealized P&L:  $150.00

Positions:
  Active:          8
  Settled Today:   3

Operations:        12

================================
```

## 数据库方法

### RecordDBManager 新增方法

#### get_daily_summary(date: str)
获取指定日期的日报摘要。

#### get_operations_by_date(date: str)
获取指定日期的所有操作记录。

#### get_settle_operations_by_date(date: str)
获取指定日期的所有结算操作。

## 技术细节

### 结算逻辑

1. 遍历所有市场ID
2. 检查每个市场的操作历史
3. 计算当前持仓
4. 检查是否已结算
5. 验证结算日期是否已到
6. 从API获取市场状态
7. 如果市场已关闭（active=False），获取最终价格
8. 记录SETTLE操作

### 日报计算

1. 获取昨日摘要（用于对比）
2. 计算当日总收益（调用 get_today_total_profit）
3. 统计当日结算金额
4. 统计当日新投资
5. 从 purse 模块获取资金状态
6. 保存到数据库

## 依赖模块

- `backend.polymarket_api.GammaMarketsAPI` - 市场数据获取
- `backend.purse` - 资金管理
- `backend.sys_configs.global_event_reg.vlogger` - 日志记录

## 错误处理

所有方法都包含完善的错误处理和日志记录：
- 使用 try-except 捕获异常
- 通过 vlogger 记录详细错误信息
- 返回明确的错误状态或错误列表

## 注意事项

1. **结算日期格式**：必须是 `yyyy-mm-dd` 格式
2. **最终价格验证**：结算时会验证价格是否为 0 或 1
3. **持仓忽略阈值**：小于 0.0001 的持仓会被忽略
4. **并发安全**：数据库操作使用连接管理确保安全

