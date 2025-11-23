# 自动交易模块 (Auto Trade)

## 概述

自动交易模块实现了完整的自动化交易流程，包括交易决策获取、订单簿分析、滑点控制和限价单执行。该模块专为 Polymarket 预测市场设计，提供了智能的风险管理和流动性分析功能。

## 主要功能

### 1. 交易指令获取
- 从 `auto_decision` 模块获取基于 Kelly 公式的最优仓位分配
- 支持多市场并行分析和资金分配
- 集成 AI 分析结果和风险因子

### 2. 订单簿数据分析
- 获取实时订单簿深度数据
- 分析买卖盘流动性
- 计算流动性评分和价差指标

### 3. 滑点控制
- 基于订单簿深度计算预期滑点
- 分析市场冲击价格
- 确定最大安全交易量
- 提供风险等级评估

### 4. 智能限价单执行
- 根据滑点分析调整限价单价格
- 支持价格改善策略
- 实现风险阈值控制
- 提供重试机制和错误处理

## 核心组件

### 数据结构

#### OrderBookAnalysis
订单簿分析结果，包含：
- 最优买卖价格
- 买卖盘深度数据
- 总交易量和价差
- 流动性评分

#### SlippageAnalysis
滑点分析结果，包含：
- 预期滑点百分比
- 市场冲击价格
- 推荐限价单价格
- 最大安全交易量
- 风险等级评估

#### TradeExecution
交易执行结果，包含：
- 原始交易指令
- 订单簿和滑点分析
- 最终执行价格和数量
- 订单响应和执行状态

### 核心类

#### AutoTrader
自动交易器主类，提供：
- 交易指令获取
- 订单簿分析
- 滑点计算
- 交易执行
- 批量处理

## 配置参数

### 滑点控制
```python
MAX_SLIPPAGE_PERCENT = 2.0      # 最大允许滑点 2%
LIQUIDITY_THRESHOLD = 100.0     # 最小流动性阈值（USDC）
MIN_ORDER_SIZE = 1.0            # 最小订单金额（USDC）
MAX_ORDER_SIZE = 10000.0        # 最大订单金额（USDC）
```

### 价格调整
```python
PRICE_IMPROVEMENT_FACTOR = 0.1  # 价格改善因子（10%）
SAFETY_MARGIN = 0.05            # 安全边距（5%）
```

### 重试机制
```python
MAX_RETRIES = 3                 # 最大重试次数
RETRY_DELAY = 1.0               # 重试延迟（秒）
```

## 使用方法

### 基础使用

```python
from backend.auto_trade.auto_trade import execute_auto_trading
from backend.polymarket_api.gamma_markets import GammaMarketsAPI

# 获取市场数据
with GammaMarketsAPI() as api:
    markets = api.get_active_markets(limit=10)

# AI 分析结果（示例）
ai_analysis = {
    "market_id_1": {"p": 0.6, "a": 0.3},
    "market_id_2": {"p": 0.7, "a": 0.2}
}

# 执行自动交易
result = execute_auto_trading(
    gamma_markets=markets,
    ai_analysis=ai_analysis,
    M_cents=50000,  # 500美元
    kappa=0.7,      # 70%最大锁定比例
    xi=0.5          # 50% Kelly分数
)

# 查看结果
if result["success"]:
    print(f"成功执行 {result['summary']['successful_executions']} 个交易")
else:
    print(f"交易失败: {result['error']}")
```

### 高级使用

```python
from backend.auto_trade.auto_trade import AutoTrader

with AutoTrader() as trader:
    # 获取交易指令
    instructions = trader.get_trade_instructions(markets, ai_analysis)
    
    # 逐个执行交易
    executions = []
    for instruction in instructions:
        execution = trader.execute_trade(instruction)
        executions.append(execution)
        
        # 检查执行结果
        if execution.success:
            print(f"交易成功: {execution.final_price}")
        else:
            print(f"交易失败: {execution.error_message}")
```

### 风险分析

```python
# 分析订单簿
orderbook_analysis = trader.analyze_orderbook(token_id)

# 计算滑点
slippage_analysis = trader.calculate_slippage(orderbook_analysis, instruction)

# 检查风险
if slippage_analysis.risk_level == "HIGH":
    print("风险过高，建议降低交易量")
elif slippage_analysis.expected_slippage > 2.0:
    print(f"滑点过大: {slippage_analysis.expected_slippage:.2f}%")
```

## 风险管理

### 滑点控制
- 自动计算预期滑点
- 设置最大滑点阈值（默认2%）
- 根据订单簿深度调整交易量

### 流动性检查
- 评估市场流动性评分
- 确保最小流动性阈值
- 计算最大安全交易量

### 风险等级
- **LOW**: 滑点 < 1%，流动性评分 > 60
- **MEDIUM**: 滑点 1-2%，流动性评分 30-60
- **HIGH**: 滑点 > 2%，流动性评分 < 30

## 日志记录

模块使用 VLogger 系统记录所有关键操作：

### 事件码
- `EVT-AT-001`: 自动交易器初始化
- `EVT-AT-002`: 获取交易决策指令
- `EVT-AT-003`: 获取交易指令成功
- `EVT-AT-004`: 分析订单簿
- `EVT-AT-005`: 订单簿分析完成
- `EVT-AT-006`: 计算滑点
- `EVT-AT-007`: 滑点计算完成
- `EVT-AT-008`: 开始执行交易
- `EVT-AT-009`: 交易执行成功

### 错误码
- `E-AT-001`: 获取交易指令失败
- `E-AT-002`: 获取交易指令异常
- `E-AT-003`: 订单簿分析失败
- `E-AT-004`: 滑点计算异常
- `E-AT-005`: 无法获取token_id
- `E-AT-006`: 交易执行异常
- `E-AT-007`: 获取token_id失败
- `E-AT-008`: 自动交易流程异常

## 依赖模块

- `backend.auto_decision.position_manager`: 仓位分配算法
- `backend.polymarket_api.orderbook_api`: 订单簿数据获取
- `backend.polymarket_api.clob_api`: 限价单下单
- `backend.polymarket_api.gamma_markets`: 市场数据获取
- `backend.sys_configs.global_event_reg`: VLogger 日志系统

## 注意事项

1. **API 密钥**: 需要配置有效的 Polymarket API 私钥
2. **网络连接**: 需要稳定的网络连接访问 Polymarket API
3. **资金管理**: 确保账户有足够的 USDC 余额
4. **风险控制**: 建议在测试环境中先验证交易逻辑
5. **Token ID 映射**: 当前版本的 `_get_token_id_from_market` 方法需要根据实际 API 实现

## 示例程序

运行示例程序查看完整使用演示：

```bash
cd backend/auto_trade
python example_usage.py
```

示例包含：
- 基础使用示例
- 高级控制示例  
- 风险分析示例

## 扩展开发

### 添加新的风险指标
继承 `SlippageAnalysis` 类并添加自定义风险指标。

### 自定义价格策略
重写 `calculate_slippage` 方法实现自定义定价逻辑。

### 集成其他交易所
实现新的订单簿客户端并替换 `PolymarketOrderbookClient`。
