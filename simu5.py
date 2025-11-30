from dataclasses import dataclass
from typing import List, Dict, Any
import math

EPS = 1e-9

@dataclass
class SimpleMarket:
    """单次分配用的精简 market 信息"""
    mid: Any           # 市场 id，例如字符串/整数都行
    m: float           # YES 报价
    p: float           # 我们预测概率
    a: float           # 不利方向滑点
    tau: int           # 距离结算的天数

def clip_cost(x: float) -> float:
    """把成本裁剪在 (0,1) 内，避免 log 数值问题"""
    return max(min(x, 1.0 - 1e-6), 1e-6)

def kelly_yes_fraction(p: float, c: float) -> float:
    c = clip_cost(c)
    if p <= c:
        return 0.0
    return (p - c) / (1.0 - c)

def kelly_no_fraction(p: float, cN: float) -> float:
    cN = clip_cost(cN)
    winp = 1.0 - p
    if winp <= cN:
        return 0.0
    return (winp - cN) / (1.0 - cN)

def marginal_gain_per_time_yes(p: float, c: float, tau: int) -> float:
    c = clip_cost(c)
    val = (p - c) / c          # g'(0)
    return val / max(1, tau)   # 单位时间

def marginal_gain_per_time_no(p: float, cN: float, tau: int) -> float:
    cN = clip_cost(cN)
    val = ((1.0 - p) - cN) / cN
    return val / max(1, tau)

def allocate(
    markets: List[SimpleMarket],
    gross_wealth: float,
    locked_cost: float,
    theta: float = 0.5,
    k: float = 0.6
) -> List[Dict[str, Any]]:
    """
    根据当前资金状态和一批市场，输出仓位分配方案。

    参数
    ----
    markets: 一批待选择的市场（尚未持仓）
    gross_wealth: 当前总盘子 = 现金 + 未结算持仓成本
    locked_cost: 当前已锁仓成本
    theta: 分数 Kelly 系数 in (0,1]
    k: 锁仓上限比例 in (0,1]

    返回
    ----
    allocations: list[dict]，每个元素包含：
        {
            'id': 市场 id,
            'side': 'YES'/'NO',
            'score': 单位时间边际分数,
            'fraction_of_gross': 实际下注占总盘子比例 f,
            'dollars': 在该市场上的资金投入,
            'shares': 买入份额数,
            'cost': 实际买入成本价(含滑点)
        }
    """
    # 可用预算：最多锁到 k*gross，减去已经锁的
    budget = max(0.0, k * gross_wealth - locked_cost)
    if budget <= EPS or gross_wealth <= EPS:
        return []   # 没钱或者没空间就不下单

    candidates = []

    # 先算每个 market 的最优方向、Kelly* 和单位时间边际得分
    for mkt in markets:
        cY = clip_cost(mkt.m + mkt.a)
        cN = clip_cost(1.0 - mkt.m + mkt.a)

        fY_star = kelly_yes_fraction(mkt.p, cY)
        fN_star = kelly_no_fraction(mkt.p, cN)

        scoreY = marginal_gain_per_time_yes(mkt.p, cY, mkt.tau)
        scoreN = marginal_gain_per_time_no(mkt.p, cN, mkt.tau)

        # 选边：谁的单位时间边际收益更高选谁
        if scoreY >= scoreN:
            side = "YES"
            score = scoreY
            cost = cY
            f_star = fY_star
        else:
            side = "NO"
            score = scoreN
            cost = cN
            f_star = fN_star

        # 需要：边际为正 & Kelly* 为正，才考虑下单
        if score > 0.0 and f_star > 0.0:
            f_cap = min(0.95, theta * f_star)              # 分数 Kelly 上限
            desired_dollars = f_cap * gross_wealth
            if desired_dollars > EPS:
                candidates.append({
                    "id": mkt.mid,
                    "side": side,
                    "score": score,
                    "f_cap": f_cap,
                    "desired_dollars": desired_dollars,
                    "cost": cost
                })

    # 按单位时间边际分数从大到小排序
    candidates.sort(key=lambda x: x["score"], reverse=True)

    allocations: List[Dict[str, Any]] = []
    remaining_budget = budget

    # 贪心地用预算往高分市场填仓
    for cand in candidates:
        if remaining_budget <= EPS:
            break
        spend = min(cand["desired_dollars"], remaining_budget)
        if spend <= EPS:
            continue
        shares = spend / cand["cost"]
        f = spend / gross_wealth

        allocations.append({
            "id": cand["id"],
            "side": cand["side"],
            "score": cand["score"],
            "fraction_of_gross": f,
            "dollars": spend,
            "shares": shares,
            "cost": cand["cost"]
        })

        remaining_budget -= spend

    return allocations
