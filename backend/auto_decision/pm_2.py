# -*- coding: utf-8 -*-
import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --------- 随机与数值工具 ---------
RNG = np.random.default_rng(12345)

def clip01(x, eps=1e-9):
    return float(min(1-eps, max(eps, x)))

# --------- 市场数据结构 ---------
@dataclass
class Market:
    id: int
    m: float       # yes price
    p_yes: float   # subjective yes probability
    d: int         # settle day (int index, > now)
    p_no: Optional[float] = None  # subjective no probability (optional)

# --------- 选择做多 YES 还是 NO（分别评估） ---------
def choose_side(m: float, p_yes: float, p_no: Optional[float], weight: float) -> Optional[Dict]:
    """
    根据边际对数效用在 f=0 的导数，选择 YES 或 NO 的方向（只选其一）。
    若两个方向边际都<=0，返回 None（不交易）。
    """
    m = clip01(m)
    p_yes = clip01(p_yes)
    if p_no is None:
        p_no = 1.0 - p_yes
    else:
        p_no = clip01(p_no)
    # 边际在 f=0 的导数（乘以时间权重）
    # YES: w*(p/m - 1); NO: w*(q/(1-m) - 1)
    deriv_yes = weight * (p_yes / m - 1.0)
    deriv_no  = weight * (p_no  / (1.0 - m) - 1.0)

    if max(deriv_yes, deriv_no) <= 0.0:
        return None

    if deriv_yes >= deriv_no:
        side = "YES"
        price = m
        p = p_yes
        b = 1.0 / m - 1.0
    else:
        side = "NO"
        price = 1.0 - m
        p = p_no
        b = 1.0 / (1.0 - m) - 1.0

    return {"side": side, "price": price, "p": p, "b": b, "deriv0": max(deriv_yes, deriv_no)}

# --------- 单市场：给定 μ 求最优 f 的二分 ---------
def f_from_mu(p: float, b: float, w: float, mu: float, f_cap: float = 0.95, iters: int = 40) -> float:
    """
    解方程： w * [ p*b/(1+f*b) - (1-p)/(1-f) ] = mu
    在区间 [0, f_cap] 上二分，注意该函数随 f 单调下降。
    """
    p = clip01(p)
    b = max(1e-9, b)
    w = max(1e-12, w)
    f_cap = min(0.999999, max(1e-6, f_cap))

    # 若边际在0处已经 <= mu，则 f=0
    deriv0 = w * (p * b - (1.0 - p))
    if deriv0 <= mu + 1e-12:
        return 0.0

    # 无约束（mu=0）的 Kelly 最优上界，用于二分右端点
    f_kelly = (p * b - (1.0 - p)) / b
    f_kelly = max(0.0, min(f_cap, f_kelly))

    lo, hi = 0.0, f_kelly
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        val = w * (p * b / (1.0 + mid * b) - (1.0 - p) / (1.0 - mid))
        if val > mu:
            lo = mid  # 需要更大 f 来降低边际
        else:
            hi = mid
    return hi

# --------- 组合层：水位二分的 allocate 函数（核心） ---------
def allocate(
    markets_today: List[Market],
    wealth: float,
    locked_value_now: float,
    now_day: int,
    k: float,
    theta: Dict
) -> List[Dict]:
    """
    基于凯利 + 水位法 + 时间贴现的多市场自动仓位分配
    ------------------------------------------------
    inputs:
      - markets_today: 今天新到的若干 Market
      - wealth: 当前总权益（现金 + 未结算仓位成本）
      - locked_value_now: 目前已锁仓成本金额
      - now_day: 当前天索引（整数）
      - k: 最大锁仓占比（0~1）
      - theta: 策略参数 dict，包含
          * 'lambda_time': 久期指数贴现系数 λ >= 0
          * 'c_fraction':  分数凯利系数 c ∈ (0,1]
          * 'f_cap':       单市场上限（默认 0.95）
    returns:
      - allocations: 列表；每个元素包含
          { 'id', 'side', 'price', 'p', 'b', 'f', 'invest', 'shares', 'settle_day' }
    备注：
      - 只在“今天”上新市场中做选择，不动已有仓位（持有到期）。
      - 保证新增锁仓占比不超过 k_rem = k - locked_value_now/wealth
    """
    lam = float(theta.get("lambda_time", 0.0))
    c_frac = float(theta.get("c_fraction", 1.0))
    f_cap = float(theta.get("f_cap", 0.95))

    wealth = max(1e-9, wealth)
    locked_frac = locked_value_now / wealth
    k_rem = max(0.0, k - locked_frac)
    if k_rem <= 1e-12:
        return []

    # 组装候选（择优只选 YES or NO 一边）
    candidates = []
    for mk in markets_today:
        T = max(1, mk.d - now_day)  # 至少1天
        w = math.exp(-lam * T)
        sd = choose_side(mk.m, mk.p_yes, mk.p_no, w)
        if sd is None:
            continue
        candidates.append({
            "id": mk.id,
            "w": w,
            "p": clip01(sd["p"]),
            "b": max(1e-9, sd["b"]),
            "price": sd["price"],
            "side": sd["side"],
            "settle_day": mk.d
        })

    if not candidates:
        return []

    # 若 mu=0 的总和就不超过预算，直接用各自 Kelly，再乘分数系数 c
    f_kelly = np.array([(c["p"] * c["b"] - (1.0 - c["p"])) / c["b"] for c in candidates], dtype=float)
    f_kelly = np.clip(f_kelly, 0.0, f_cap)
    sum_kelly = float(f_kelly.sum())
    if sum_kelly <= k_rem + 1e-12:
        f_use = f_kelly * max(1e-9, min(1.0, c_frac))
    else:
        # 水位二分：找到 mu 使得 sum f(mu) = k_rem
        def sum_f(mu: float) -> float:
            s = 0.0
            for c in candidates:
                s += f_from_mu(c["p"], c["b"], c["w"], mu, f_cap=f_cap)
            return s

        lo, hi = 0.0, 1.0
        # 扩大 hi 直到 sum_f(hi) <= k_rem
        while sum_f(hi) > k_rem:
            hi *= 2.0
            if hi > 1e6:
                break
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if sum_f(mid) > k_rem:
                lo = mid
            else:
                hi = mid
        mu_star = hi
        f_use = np.array([f_from_mu(c["p"], c["b"], c["w"], mu_star, f_cap=f_cap) for c in candidates], dtype=float)
        # 额外分数 Kelly（更保守）：整体缩放
        f_use *= max(1e-9, min(1.0, c_frac))

    # 生成最终下单
    allocations = []
    for c, f in zip(candidates, f_use):
        if f <= 1e-9:
            continue
        invest = f * wealth
        shares = invest / c["price"]
        allocations.append({
            "id": c["id"],
            "side": c["side"],
            "price": c["price"],
            "p": c["p"],
            "b": c["b"],
            "f": float(f),
            "invest": float(invest),
            "shares": float(shares),
            "settle_day": c["settle_day"],
        })
    return allocations

# --------- 随机市场生成与结算 ---------
def gen_markets_for_day(day: int, base_id: int, n_new: int, min_T=3, max_T=45,
                        p_low=0.05, p_high=0.95, misprice_sigma=0.06,
                        allow_incoherent_q=False) -> Tuple[List[Market], int]:
    """
    生成 n_new 个市场：
      - 主观 p_yes ~ U[p_low, p_high]
      - 报价 m = clip( p_yes + Normal(0, sigma) )
      - 结算期 T ~ U[min_T, max_T]
      - 可选：提供 p_no != 1-p_yes 的轻微不一致（演示分别分析）
    """
    mkts = []
    for i in range(n_new):
        p = float(RNG.uniform(p_low, p_high))
        m = float(np.clip(RNG.normal(loc=p, scale=misprice_sigma), 0.01, 0.99))
        T = int(RNG.integers(min_T, max_T + 1))
        if allow_incoherent_q:
            # 让 q 在 1-p 周围扰动一点点，但仍裁剪到 0~1
            q = float(np.clip((1.0 - p) + RNG.normal(0.0, 0.05), 0.0, 1.0))
        else:
            q = None
        mkts.append(Market(id=base_id + i, m=m, p_yes=p, d=day + T, p_no=q))
    return mkts, base_id + n_new

def realize_outcome_from_ptrue(p_subjective: float) -> int:
    """
    真概率围绕主观 p 上下浮动 50%：
      p_true = clip( p * (1 + U[-0.5, 0.5]) )
      然后 Bernoulli(p_true)
    """
    p_true = p_subjective * (1.0 + float(RNG.uniform(-0.5, 0.5)))
    p_true = float(np.clip(p_true, 0.0, 1.0))
    return int(RNG.uniform() < p_true)

# --------- 单次完整模拟 ---------
def simulate_path(
    T_days: int,
    M0: float,
    k: float,
    theta: Dict,
    mean_new_markets: float = 6.0,
    seed: Optional[int] = None
) -> Tuple[List[float], float]:
    """
    返回 (wealth_curve, final_wealth)
    wealth_curve 是每天结束后的“权益”（现金 + 已投入成本）轨迹。
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
        global RNG
        RNG = np.random.default_rng(seed)

    day = 0
    cash = float(M0)
    positions = []  # 未结算：每个元素含 {id, side, price, shares, invest, settle_day, p_used}
    next_id = 0

    wealth_curve = []

    for day in range(T_days):
        # 1) 结算到期仓位
        to_keep = []
        for pos in positions:
            if pos["settle_day"] <= day:
                # 用 pos["p_used"] 的主观 p 来生成真实概率（围绕它上下50%）
                # YES: payoff = 1 若 outcome=1； NO: payoff = 1 若 outcome=0
                outcome_yes = realize_outcome_from_ptrue(pos["p_used"])
                if pos["side"] == "YES":
                    payoff = pos["shares"] * (1.0 if outcome_yes == 1 else 0.0)
                else:  # NO
                    payoff = pos["shares"] * (1.0 if outcome_yes == 0 else 0.0)
                cash += payoff  # 成交回款
                # 成本 invest 早在买入时已从 cash 扣除，这里只加回结算兑付
            else:
                to_keep.append(pos)
        positions = to_keep

        # 2) 统计当前锁仓成本总额
        locked_value = sum(p["invest"] for p in positions)
        wealth = cash + locked_value

        # 3) 生成今天的新市场
        n_new = max(0, int(RNG.poisson(mean_new_markets)))
        mkts, next_id = gen_markets_for_day(day, next_id, n_new)

        # 4) 进行分配
        allocs = allocate(
            mkts,
            wealth=wealth,
            locked_value_now=locked_value,
            now_day=day,
            k=k,
            theta=theta
        )

        # 5) 执行下单（锁仓）
        for al in allocs:
            if al["invest"] <= 0.0 or al["invest"] > cash:
                continue
            cash -= al["invest"]
            positions.append({
                "id": al["id"],
                "side": al["side"],
                "price": al["price"],
                "shares": al["shares"],
                "invest": al["invest"],
                "settle_day": al["settle_day"],
                "p_used": al["p"],  # 用于产生 p_true
            })

        # 6) 记录当日权益
        locked_value = sum(p["invest"] for p in positions)
        wealth = cash + locked_value
        wealth_curve.append(wealth)

    # 结束后，把所有剩余仓位在 T_days 时点统一结算（便于得到最终财富）
    # 仅用于返回 final_wealth，不改变曲线（曲线是按日记录的权益）。
    final_cash = cash
    for pos in positions:
        outcome_yes = realize_outcome_from_ptrue(pos["p_used"])
        if pos["side"] == "YES":
            payoff = pos["shares"] * (1.0 if outcome_yes == 1 else 0.0)
        else:
            payoff = pos["shares"] * (1.0 if outcome_yes == 0 else 0.0)
        final_cash += payoff
    final_wealth = final_cash

    return wealth_curve, final_wealth

# --------- 进化搜索 θ=(lambda, c) ---------
def evolutionary_search_theta(
    generations: int,
    pop_size: int,
    bounds: Dict[str, Tuple[float, float]],
    M0: float,
    k: float,
    T_days: int,
    mean_new_markets: float,
    trials_per_theta: int = 2,
    seed: Optional[int] = None
) -> Tuple[Dict, pd.DataFrame]:
    """
    简单进化搜索：随机初始化 -> 精英保留 -> 高斯扰动
    目标：最大化平均 (1/T)*log(W_T / M0)
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    def sample_theta():
        lam = RNG.uniform(bounds["lambda_time"][0], bounds["lambda_time"][1])
        c = RNG.uniform(bounds["c_fraction"][0], bounds["c_fraction"][1])
        return {"lambda_time": float(lam), "c_fraction": float(c), "f_cap": 0.95}

    def mutate(theta):
        # 对数域上更稳定：对 lambda 采用对数扰动（避免负数），对 c 做小扰动
        lam = max(0.0, theta["lambda_time"] * math.exp(RNG.normal(0, 0.25)))
        lam = float(np.clip(lam, bounds["lambda_time"][0], bounds["lambda_time"][1]))
        c = float(np.clip(theta["c_fraction"] + RNG.normal(0, 0.05), bounds["c_fraction"][0], bounds["c_fraction"][1]))
        return {"lambda_time": lam, "c_fraction": c, "f_cap": theta.get("f_cap", 0.95)}

    def score_theta(theta, base_seed):
        acc = 0.0
        for t in range(trials_per_theta):
            # 使用不同种子，减少噪声
            _, Wf = simulate_path(
                T_days=T_days,
                M0=M0,
                k=k,
                theta=theta,
                mean_new_markets=mean_new_markets,
                seed=(base_seed + t if base_seed is not None else None)
            )
            acc += (math.log(max(1e-9, Wf / M0)) / T_days)
        return acc / trials_per_theta

    # 初始化
    pop = [sample_theta() for _ in range(pop_size)]
    rows = []
    best = None
    best_score = -1e18
    base_seed = int(RNG.integers(0, 10_000_000))

    for g in range(generations):
        scored = []
        for th in pop:
            sc = score_theta(th, base_seed + g * 1000)
            scored.append((sc, th))
        scored.sort(key=lambda x: x[0], reverse=True)
        elite = [th for _, th in scored[: max(2, pop_size // 4)]]
        # 记录
        for rank, (sc, th) in enumerate(scored):
            rows.append({"gen": g, "rank": rank, "lambda_time": th["lambda_time"], "c_fraction": th["c_fraction"], "score": sc})

        if scored[0][0] > best_score:
            best_score = scored[0][0]
            best = scored[0][1]

        # 产生下一代
        next_pop = elite.copy()
        while len(next_pop) < pop_size:
            parent = elite[int(RNG.integers(0, len(elite)))]
            child = mutate(parent)
            next_pop.append(child)
        pop = next_pop

    df = pd.DataFrame(rows)
    return best, df

# --------------- 主流程：参数 & 演示 ----------------
M0 = 1_0000.0   # 初始资金（例如 10000）
k  = 0.60       # 允许锁仓比例（最多 60% 资金被锁定）
T_days_search = 120
mean_new_markets = 6.0

# 进化搜索边界
bounds = {
    "lambda_time": (0.0, 0.08),  # 久期贴现 0~0.08/天
    "c_fraction": (0.2, 1.0),    # 分数凯利 0.2~1.0
}

best_theta, df_log = evolutionary_search_theta(
    generations=3,
    pop_size=14,
    bounds=bounds,
    M0=M0,
    k=k,
    T_days=T_days_search,
    mean_new_markets=mean_new_markets,
    trials_per_theta=2,
    seed=2025
)

print("Best theta found:", best_theta)

# 用最优 theta 跑一条更长的路径并画曲线
T_days_final = 180
wealth_curve, W_final = simulate_path(
    T_days=T_days_final,
    M0=M0,
    k=k,
    theta=best_theta,
    mean_new_markets=mean_new_markets,
    seed=777
)
print(f"Final wealth after {T_days_final} days: {W_final:.2f}")

# 画资金曲线（单图、默认配色）
plt.figure(figsize=(9, 4.8))
plt.plot(range(T_days_final), wealth_curve)
plt.xlabel("Day")
plt.ylabel("Wealth (equity)")
plt.title("Wealth Curve with Kelly + Water-filling under Lock-up Constraint")
plt.tight_layout()
plt.show()
