# Position Manager Pro - 仓位分配系统优化版

## 概述

`allocate_optimal_positions_pro` 是仓位分配系统的优化版本，专为高精度金融计算和数据结构整合而设计。

## 主要特性

### 1. 精度优化
- **全程整数计算**：使用美分（cents）作为基本单位，避免浮点数精度损失
- **价格精度**：价格使用整数表示（1-99 美分），精确到 0.01 美元
- **份额精度**：份额使用 10000 倍单位，精确到 0.0001 份

### 2. 数据结构整合
- **直接接收 Gamma Markets 数据**：无需手动转换，自动解析 API 返回的 Market 对象
- **AI 分析结果集成**：直接使用 `deep_analysis` 模块的输出格式
- **自动数据转换**：内置转换函数，处理日期、价格、概率等字段

### 3. 增强的输出格式
- **TradeInstruction 数据结构**：包含完整的交易指令信息
- **详细的元数据**：市场问题、交易量、流动性等
- **汇总统计**：总投入、预期收益、ROI、预算使用率等

### 4. VLogger 日志集成
- **结构化日志**：所有关键操作都有详细的日志记录
- **事件追踪**：支持全链路追踪（trace_id）
- **错误码体系**：标准化的错误码和错误处理

## 核心函数

### allocate_optimal_positions_pro

```python
def allocate_optimal_positions_pro(
    gamma_markets: List['GammaMarket'],
    ai_analysis_result: Dict[str, Any],
    M_cents: Optional[int] = None,
    kappa: float = 0.7,
    locked_cents: int = 0,
    xi: float = 0.5,
    shrink_with_a: bool = True
) -> Dict[str, Any]:
```

#### 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `gamma_markets` | `List[GammaMarket]` | Gamma API 返回的 Market 对象列表 | 必需 |
| `ai_analysis_result` | `Dict[str, Any]` | AI 分析结果字典 | 必需 |
| `M_cents` | `Optional[int]` | 当前可用现金（美分），None 则自动获取 | `None` |
| `kappa` | `float` | 全局锁定上限（0-1） | `0.7` |
| `locked_cents` | `int` | 现有未结算头寸的名义成本（美分） | `0` |
| `xi` | `float` | 分数 Kelly 系数（0-1） | `0.5` |
| `shrink_with_a` | `bool` | 是否用风险因子 a 对概率 p 做收缩 | `True` |

#### AI 分析结果格式

**重要更新**：AI 分析结果现在使用 `market_id` 作为键，而不是序号索引。

```json
{
  "68095": {
    "p": 0.6,
    "a": 0.3,
    "reasons_p": ["理由1", "理由2"],
    "reasons_n": ["理由1", "理由2"]
  },
  "68096": {
    "p": 0.7,
    "a": 0.2,
    "reasons_p": ["理由1"],
    "reasons_n": ["理由1"]
  }
}
```

**说明**：
- 键名从 `"Market #1"`, `"Market #2"` 改为实际的 `market_id`（例如 `"68095"`, `"68096"`）
- 这样可以确保 AI 分析结果与市场数据的精确匹配，避免索引错位问题

- `p`: AI 预测的 YES 概率（0-1）
- `a`: 风险因子（0-1），越大越保守
- `reasons_p`: 支持 YES 的理由列表
- `reasons_n`: 支持 NO 的理由列表

#### 返回值格式

```python
{
    "success": True,  # 是否成功
    "meta": {
        "B_cents": 100000,        # 基准财富（美分）
        "budget_cents": 70000,    # 可用预算（美分）
        "kappa": 0.7,             # 全局锁定上限
        "xi": 0.5,                # 分数 Kelly 系数
        "used_cents": 65000       # 实际使用金额（美分）
    },
    "instructions": [
        {
            "market_id": "market_001",
            "market_question": "Will Bitcoin reach $100,000?",
            "side": "BUY_YES",
            "alloc_cents": 30000,
            "alloc_dollars": 300.0,
            "entry_price": 0.42,
            "shares": 714.2857,
            "expected_profit_cents": 9285,
            "expected_profit_dollars": 92.85,
            "kelly_fraction": 0.15,
            "confidence_p": 0.55,
            "risk_factor_a": 0.3,
            "days_to_expiry": 365,
            "metadata": {...}
        }
    ],
    "summary": {
        "total_markets": 3,
        "valid_markets": 3,
        "tradable_markets": 2,
        "total_alloc_cents": 65000,
        "total_alloc_dollars": 650.0,
        "total_expected_profit_cents": 15000,
        "total_expected_profit_dollars": 150.0,
        "expected_roi": 23.08,
        "budget_utilization": 92.86
    },
    "error": None
}
```

## 参数详解

### M_cents（可用现金）
- **单位**：美分（1 美元 = 100 美分）
- **说明**：当前账户中可立即部署的现金
- **自动获取**：如果设置为 `None`，系统会自动调用 `get_available_balance()` 获取账户余额

### kappa（全局锁定上限）
- **范围**：0.0 - 1.0
- **说明**：允许锁定的最大资金比例（相对于基准财富 B）
- **基准财富 B**：`B = M_cents + locked_cents`
- **新增锁定上限**：`max(0, kappa * B - locked_cents)`
- **实际预算**：`min(M_cents, 新增锁定上限)`

**示例**：
- 可用现金：1000 美元（100,000 美分）
- 已锁定：300 美元（30,000 美分）
- kappa = 0.7
- 基准财富 B = 1300 美元（130,000 美分）
- 允许总锁定 = 0.7 × 1300 = 910 美元（91,000 美分）
- 新增锁定上限 = 910 - 300 = 610 美元（61,000 美分）
- 实际预算 = min(1000, 610) = 610 美元（61,000 美分）

### locked_cents（已锁定资金）
- **单位**：美分
- **说明**：现有未结算头寸的名义成本
- **用途**：计算基准财富 B 和可用预算

### xi（分数 Kelly 系数）
- **范围**：0.0 - 1.0
- **说明**：Kelly 公式的缩放系数，用于控制风险
- **推荐值**：
  - `0.25`：四分之一 Kelly（非常保守）
  - `0.5`：半 Kelly（推荐，平衡风险和收益）
  - `1.0`：完整 Kelly（激进，最大化对数增长）

**Kelly 公式**：
```
f* = (p - r) / (1 - r)
```
其中：
- `p`：成功概率
- `r`：入场价格
- `f*`：最优下注比例

**分数 Kelly**：
```
f_use = xi * f*
```

### shrink_with_a（风险收缩）
- **类型**：布尔值
- **说明**：是否使用风险因子 a 对概率 p 进行收缩
- **收缩公式**：
  ```
  p_adj = m + (p - m) / (1 + a)
  ```
  其中：
  - `m`：市场价格
  - `p`：AI 预测概率
  - `a`：风险因子
  - `p_adj`：调整后的概率

**效果**：
- `a = 0`：不收缩，`p_adj = p`
- `a > 0`：向市场价格收缩，越大越保守
- `a → ∞`：完全收缩到市场价格，`p_adj → m`

## 交易方向判断

系统根据调整后的概率 `p_adj` 和市场价格 `m` 自动判断交易方向：

1. **BUY_YES**：当 `p_adj > m` 时
   - 成功概率：`s = p_adj`
   - 入场价格：`r = m`
   - 含义：AI 认为 YES 被低估

2. **BUY_NO**：当 `p_adj < m` 时
   - 成功概率：`s = 1 - p_adj`
   - 入场价格：`r = 1 - m`
   - 含义：AI 认为 NO 被低估

3. **NO_TRADE**：当 `p_adj ≈ m` 时
   - 含义：市场价格合理，无套利空间

## 精度说明

### 价格精度
- **存储格式**：整数（1-99）
- **实际价格**：整数 / 100
- **示例**：42 表示 0.42 美元

### 金额精度
- **存储格式**：整数（美分）
- **实际金额**：整数 / 100
- **示例**：30000 表示 300.00 美元

### 份额精度
- **存储格式**：整数（单位：0.0001 份）
- **实际份额**：整数 / 10000
- **示例**：7142857 表示 714.2857 份

### 计算示例

假设：
- 投入金额：300 美元（30000 美分）
- 入场价格：0.42（42 美分）

**份额计算**：
```python
shares_units = (alloc_cents * 10000) // price_cents
             = (30000 * 10000) // 42
             = 7142857

shares = shares_units / 10000.0
       = 714.2857 份
```

**预期收益计算**（假设成功概率 55%）：
```python
success_prob_cents = 55  # 55%

expected_profit_cents = (alloc_cents * success_prob_cents) // entry_price_cents - alloc_cents
                      = (30000 * 55) // 42 - 30000
                      = 39285 - 30000
                      = 9285 美分
                      = 92.85 美元
```

## 使用示例

### 基础用法

```python
from position_manager import allocate_optimal_positions_pro
from polymarket_api.gamma_markets import GammaMarketsAPI

# 1. 获取市场数据
with GammaMarketsAPI() as api:
    markets = api.get_active_markets(limit=5)

# 2. 准备 AI 分析结果
ai_analysis = {
    "Market #1": {"p": 0.6, "a": 0.3, "reasons_p": [...], "reasons_n": [...]},
    "Market #2": {"p": 0.7, "a": 0.2, "reasons_p": [...], "reasons_n": [...]}
}

# 3. 调用仓位分配
result = allocate_optimal_positions_pro(
    gamma_markets=markets,
    ai_analysis_result=ai_analysis,
    M_cents=100_000,  # 1000 美元
    kappa=0.7,
    xi=0.5
)

# 4. 处理结果
if result["success"]:
    for instruction in result["instructions"]:
        print(f"市场: {instruction['market_question']}")
        print(f"方向: {instruction['side']}")
        print(f"金额: ${instruction['alloc_dollars']:.2f}")
```

### 完整工作流

参考 `example_pro_allocation.py` 文件中的完整示例。

## 辅助函数

### get_trade_instructions_summary

生成交易指令的可读摘要。

```python
from position_manager import get_trade_instructions_summary

summary = get_trade_instructions_summary(result["instructions"])
print(summary)
```

### export_instructions_to_json

导出交易指令到 JSON 文件。

```python
from position_manager import export_instructions_to_json

export_instructions_to_json(result["instructions"], "trade_instructions.json")
```

## 日志系统

系统使用 VLogger 记录所有关键操作：

### 事件类型
- `EVT-POS-001`: 开始仓位分配
- `EVT-POS-002`: 仓位分配成功
- `EVT-POS-003`: 获取账户余额
- `EVT-POS-004`: 市场数据转换完成
- `EVT-POS-005`: 市场数据转换失败
- `EVT-POS-006`: 交易指令导出成功

### 错误码
- `E-POS-001`: 没有有效的市场数据
- `E-POS-002`: 仓位分配异常
- `E-POS-003`: 交易指令导出失败

## 注意事项

1. **Market ID 匹配**：AI 分析结果必须使用 `market_id` 作为键，确保与 Gamma Markets 数据精确匹配
2. **数据完整性**：每个市场必须在 AI 分析结果中有对应的条目，否则该市场会被跳过
3. **精度处理**：所有金额计算使用整数，避免浮点数精度问题
4. **余额获取**：如果 `M_cents=None`，系统会自动调用 API 获取余额，需要确保 API 配置正确
5. **风险控制**：建议使用 `xi=0.5`（半 Kelly）和 `kappa=0.7` 作为默认参数
6. **日期字段**：系统会优先使用 `closedTime` 字段，如果不存在则使用 `end_date` 字段

## 性能优化

- 使用整数运算替代浮点数运算，提高计算速度
- 批量处理市场数据，减少 API 调用次数
- 缓存中间计算结果，避免重复计算

## 未来改进

- [ ] 支持多币种
- [ ] 支持止盈止损策略
- [ ] 支持动态调整 kappa 和 xi
- [ ] 支持回测功能
- [ ] 支持实时监控和告警

