# Position Listener 模块增强功能

## 概述

本次更新为 position_listener 模块添加了两个重要的增强功能,并在前端界面中添加了持仓和订单的管理功能。

---

## 后端增强功能

### 1. 订单监控增强 (order_monitor.py)

**功能**: 自动删除不存在的订单

当 Polymarket API 返回空结果或订单不存在时:
- 自动停止对该订单的监听
- 从数据库的 `orders` 表中删除该订单记录
- 记录相应的日志信息

**实现位置**: `backend/position_listener/order_monitor.py`

**关键代码**:
```python
# 检查API返回结果是否有效
if clob_order is None:
    vlogger.warn("ORDER_MONITOR.API.NULL_RESPONSE", ...)
    
    # 自动删除不存在的订单记录
    try:
        deleted = self.db.delete_order(order_id)
        if deleted:
            vlogger.info("ORDER_MONITOR.AUTO_DELETE", ...)
    except Exception as e:
        vlogger.error("ORDER_MONITOR.AUTO_DELETE.ERROR", ...)
```

**日志标识**:
- `ORDER_MONITOR.API.NULL_RESPONSE` - API返回空结果
- `ORDER_MONITOR.AUTO_DELETE` - 自动删除成功
- `ORDER_MONITOR.AUTO_DELETE.ERROR` - 自动删除失败

---

### 2. 市场监控增强 (market_monitor.py)

**功能**: 价格涨幅检测

在现有的市场监控任务中添加价格涨幅检测逻辑:
- 对每个未平仓持仓,计算当前价格相对于购买价格的涨跌幅百分比
- 当涨跌幅超过 10% 时触发预警
- 调用占位函数 `_handle_price_surge(position, price_change_pct)`
- 记录详细的日志信息

**实现位置**: `backend/position_listener/market_monitor.py`

**关键代码**:
```python
class MarketMonitor:
    # 价格涨幅阈值（10%）
    PRICE_SURGE_THRESHOLD = 0.10
    
    def _handle_price_surge(self, position: Position, price_change_pct: float):
        """
        处理价格涨幅超过阈值的情况
        
        TODO: 实现具体的价格涨幅处理逻辑，例如：
        - 发送价格预警通知
        - 触发自动止盈/止损策略
        - 记录到专门的价格异动表
        - 调整持仓风险等级
        """
        vlogger.info("MARKET_MONITOR.PRICE_SURGE", ...)
```

**日志标识**:
- `MARKET_MONITOR.PRICE_SURGE` - 检测到价格涨幅超过阈值

**日志包含信息**:
- position_id - 持仓ID
- market_id - 市场ID
- side - 交易方向
- entry_price - 入场价格
- current_price - 当前价格
- price_change_pct - 价格涨跌幅百分比
- threshold - 阈值
- pnl - 盈亏

---

## 前端界面增强

### 1. 持仓管理功能

**位置**: 前端 > 持仓监控 > 持仓列表

**新增功能**:
- ✅ **编辑持仓**: 可以修改当前价格、状态、结算信息
- ✅ **删除持仓**: 删除持仓记录(包括关联的交易记录)

**编辑持仓对话框字段**:
- 市场ID (只读)
- 方向 (只读)
- 入场价格 (只读)
- 当前价格 (可编辑)
- 状态 (可编辑: open/closed/monitoring)
- 结算结果 (状态为closed时可编辑: YES/NO)
- 结算收益 (状态为closed时可编辑)

---

### 2. 订单管理功能

**位置**: 前端 > 持仓监控 > 订单列表

**新增功能**:
- ✅ **编辑订单**: 可以修改已成交数量、订单状态
- ✅ **删除订单**: 删除订单记录

**编辑订单对话框字段**:
- 订单ID (只读)
- 市场ID (只读)
- 方向 (只读)
- 价格 (只读)
- 数量 (只读)
- 已成交数量 (可编辑)
- 状态 (可编辑: pending/filled/cancelled/failed)

---

## API 接口

### 持仓相关

#### 更新持仓
```
PUT /api/positions/{position_id}
```

请求体:
```json
{
  "current_price": 0.65,
  "status": "open",
  "settlement_result": "YES",
  "settlement_payout": 100.0
}
```

#### 删除持仓
```
DELETE /api/positions/{position_id}
```

### 订单相关

#### 更新订单
```
PUT /api/positions/orders/{order_id}
```

请求体:
```json
{
  "status": "filled",
  "filled_size": 100.0
}
```

#### 删除订单
```
DELETE /api/positions/orders/{order_id}
```

---

## 使用说明

### 后端功能

1. **订单自动删除**: 无需手动操作,定时任务会自动检测并删除不存在的订单
2. **价格涨幅预警**: 定时任务每5分钟自动检测,超过10%涨跌幅会记录日志

### 前端操作

1. **编辑持仓**:
   - 进入"持仓监控"页面
   - 在持仓列表中找到要编辑的持仓
   - 点击"编辑"按钮
   - 修改相关字段
   - 点击"保存"

2. **删除持仓**:
   - 在持仓列表中找到要删除的持仓
   - 点击"删除"按钮
   - 确认删除操作

3. **编辑/删除订单**: 操作方式同持仓

---

## 注意事项

1. **删除操作不可恢复**: 删除持仓或订单后无法恢复,请谨慎操作
2. **关联数据**: 删除持仓时会同时删除关联的交易记录
3. **价格涨幅阈值**: 当前设置为10%,可在代码中修改 `PRICE_SURGE_THRESHOLD` 常量
4. **日志记录**: 所有操作都会记录详细日志,便于追踪和调试

---

## 文件修改清单

### 后端文件
- `backend/position_listener/database.py` - 添加 `delete_order()` 方法
- `backend/position_listener/order_monitor.py` - 添加自动删除逻辑
- `backend/position_listener/market_monitor.py` - 添加价格涨幅检测
- `backend/core/routes/positions.py` - 添加更新和删除API接口

### 前端文件
- `frontend/src/api/positions.js` - 添加API调用函数
- `frontend/src/components/PositionMonitor.vue` - 添加编辑和删除功能

---

## 后续扩展建议

1. **价格预警通知**: 在 `_handle_price_surge()` 中实现邮件/短信通知
2. **自动止盈止损**: 根据价格涨跌幅自动执行交易
3. **批量操作**: 支持批量编辑和删除持仓/订单
4. **操作历史**: 记录所有编辑和删除操作的历史
5. **权限控制**: 添加操作权限验证

