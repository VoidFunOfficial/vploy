from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

# ----------------------------------------------------------------------
# 全局常量
# ----------------------------------------------------------------------
TICK = 0.01      # 价格精度（如有需要，可删掉）
EPS  = 1e-12     # 数值下限，避免除零 / 负值

# ----------------------------------------------------------------------
# 数据结构
# ----------------------------------------------------------------------
@dataclass
class SimpleMarket:
    """
    精简版的 Market，用于一次性仓位分配。

    属性
    ----
    mid    : 市场 id
    m      : YES 报价 (∈ (0,1))
    p_yes  : 我们对 YES 的预测概率
    p_no   : 我们对 NO  的预测概率（不要求 p_yes + p_no == 1）
    a      : 不利方向滑点（成本上浮）
    tau    : 距离结算的天数（≥1，越小代表越快结算）
    """
    mid   : Any
    m     : float
    p_yes : float
    p_no  : float
    a     : float
    tau   : int


# 如你有自己的 GammaMarket，可在此转换
def convert_to_simple_market(market: "GammaMarket") -> SimpleMarket:  # type: ignore
    """
    将 GammaMarket 对象转换为 SimpleMarket。
    假设 GammaMarket 有:
        - id
        - outcome_prices[0]  (YES 成交价)
        - p_yes, p_no        (预测概率)
        - a                  (滑点)
        - tau                (结算剩余天数)
    """
    return SimpleMarket(
        mid   = market.id,
        m     = market.outcome_prices[0],
        p_yes = market.p_yes,
        p_no  = market.p_no,
        a     = market.a,
        tau   = market.tau,
    )

# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def clip_cost(x: float) -> float:
    """把成本裁剪到 (0,1) 内，避免 log/除零 问题"""
    return max(min(x, 1.0 - 1e-6), 1.0e-6)


def kelly_fraction(p: float, c: float) -> float:
    """
    通用 Kelly 最优仓位 f* （未乘 Kelly 折扣）。
    p : 赢面
    c : 成本 (含滑点)
    """
    c = clip_cost(c)
    if p <= c:            # 期望收益 ≤0，f*=0
        return 0.0
    return (p - c) / (1.0 - c)


def marginal_gain_per_time(p: float, c: float, tau: int) -> float:
    """
    近似的单位时间边际收益 g'(0) / tau。
    用于比较不同市场 / 不同方向的“吸引力”。
    """
    c = clip_cost(c)
    g_prime = (p - c) / c          # g'(0) ≈ (p-c)/c
    return g_prime / max(1, tau)   # 按剩余天数折算


# ----------------------------------------------------------------------
# 核心：仓位分配
# ----------------------------------------------------------------------
def allocate(
    markets: List[SimpleMarket],
    gross_wealth: float,
    locked_cost: float,
    *,
    theta: float = 0.5,
    k: float = 0.6,
) -> List[Dict[str, Any]]:
    """
    按 Kelly 原理 & 资金约束，输出本次应下注的仓位方案。

    参数
    ----
    markets      : 当前待挑选的市场列表（无持仓）
    gross_wealth : 账户总盘子 = 现金 + 已锁仓成本
    locked_cost  : 目前已锁仓成本（已买入但未结算）
    theta        : 分数 Kelly 系数 (0,1]，常用 0.5
    k            : 总锁仓成本 / 账户总盘子 的上限 (0,1]，常用 0.6

    返回
    ----
    allocations  : list[dict]，字段：
        id                - 市场 id
        side              - "YES" / "NO"
        score             - 单位时间边际收益
        fraction_of_gross - 本方向下注占 gross_wealth 的比例 f
        dollars           - 本方向将花费的资金
        shares            - 预计买入份额数
        cost              - 实际成本价 (含滑点)
    """
    # --------------------------------------------------
    # 预算：最多锁 k*gross，其中 locked_cost 已经占用
    # --------------------------------------------------
    budget = max(0.0, k * gross_wealth - locked_cost)
    if budget <= EPS or gross_wealth <= EPS:
        return []  # 没钱 or 没空间：不买

    candidates: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # 1. 逐市场计算 YES / NO 的 Kelly*, score
    # --------------------------------------------------
    for mkt in markets:
        # 成本（含滑点）：YES = m+a；NO = 1-m+a
        c_yes = clip_cost(mkt.m + mkt.a)
        c_no  = clip_cost(1.0 - mkt.m + mkt.a)

        # Kelly*（未折扣）
        f_yes_star = kelly_fraction(mkt.p_yes, c_yes)
        f_no_star  = kelly_fraction(mkt.p_no,  c_no)

        # 单位时间边际收益
        score_yes = marginal_gain_per_time(mkt.p_yes, c_yes, mkt.tau)
        score_no  = marginal_gain_per_time(mkt.p_no,  c_no,  mkt.tau)

        # 选边：只挑得分更高那一侧（如需双边，请自行改进）
        if score_yes >= score_no:
            side   = "YES"
            score  = score_yes
            cost   = c_yes
            f_star = f_yes_star
        else:
            side   = "NO"
            score  = score_no
            cost   = c_no
            f_star = f_no_star

        # 过滤：需同时满足 (score>0) & (f*>0)
        if score > 0.0 and f_star > 0.0:
            # 分数 Kelly（加了 theta 上限 + 0.95 保护）
            f_cap = min(0.95, theta * f_star)
            desired_dollars = f_cap * gross_wealth
            if desired_dollars > EPS:
                candidates.append({
                    "id"             : mkt.mid,
                    "side"           : side,
                    "score"          : score,
                    "desired_dollars": desired_dollars,
                    "cost"           : cost,
                })

    # --------------------------------------------------
    # 2. 按 score 从高到低，用预算填仓
    # --------------------------------------------------
    candidates.sort(key=lambda x: x["score"], reverse=True)

    allocations: List[Dict[str, Any]] = []
    remaining = budget

    for cand in candidates:
        if remaining <= EPS:
            break
        spend = min(cand["desired_dollars"], remaining)
        if spend <= EPS:
            continue

        alloc = {
            "id"               : cand["id"],
            "side"             : cand["side"],
            "score"            : cand["score"],
            "fraction_of_gross": spend / gross_wealth,
            "dollars"          : spend,
            "shares"           : spend / cand["cost"],
            "cost"             : cand["cost"],
        }
        allocations.append(alloc)
        remaining -= spend

    return allocations

# ----------------------------------------------------------------------
# 示例（可删）
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # 构造三个示例市场
    markets = [
        SimpleMarket("M1", m=0.40, p_yes=0.55, p_no=0.47, a=0.02, tau=10),
        SimpleMarket("M2", m=0.65, p_yes=0.70, p_no=0.25, a=0.02, tau=20),
        SimpleMarket("M3", m=0.20, p_yes=0.30, p_no=0.80, a=0.02, tau=5),
    ]
    allocs = allocate(
        markets      = markets,
        gross_wealth = 10_000.0,
        locked_cost  = 1_500.0,
        theta        = 0.5,
        k            = 0.6,
    )
    from pprint import pprint
    pprint(allocs)
