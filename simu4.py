# Let's refactor with outcome tracking in Position for correct settlement mapping.

import numpy as np
import math
import random
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List, Dict

rng = np.random.default_rng(42)
random.seed(42)

EPS = 1e-9

@dataclass
class Market:
    day: int
    tau: int
    settle_day: int
    m: float
    p: float
    a: float
    q_true: float
    outcome_yes: int

@dataclass
class Position:
    side: str
    cost: float
    shares: float
    notional_cost: float
    open_day: int
    settle_day: int
    outcome_yes: int  # attach outcome for the specific market

@dataclass
class SimResult:
    wealth_path: List[float]
    cash_path: List[float]
    locked_cost_path: List[float]
    locked_ratio_path: List[float]
    positions_count: int
    wins_count: int
    n_yes: int
    n_no: int
    final_wealth: float
    theta: float
    daily_log_growth: float

def clip_cost(x: float) -> float:
    x = max(min(x, 1.0 - 1e-6), 1e-6)
    return x

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

def log_growth_yes(p: float, c: float, f: float) -> float:
    c = clip_cost(c)
    f = min(max(f, 0.0), 0.95)
    return p * math.log(1.0 + f * (1.0/c - 1.0)) + (1.0 - p) * math.log(1.0 - f)

def log_growth_no(p: float, cN: float, f: float) -> float:
    cN = clip_cost(cN)
    f = min(max(f, 0.0), 0.95)
    winp = 1.0 - p
    return winp * math.log(1.0 + f * (1.0/cN - 1.0)) + p * math.log(1.0 - f)

def marginal_gain_per_time_yes(p: float, c: float, tau: int) -> float:
    c = clip_cost(c)
    val = (p - c) / c
    return val / max(1, tau)

def marginal_gain_per_time_no(p: float, cN: float, tau: int) -> float:
    cN = clip_cost(cN)
    val = ((1.0 - p) - cN) / cN
    return val / max(1, tau)

def generate_world(
    T_days: int = 365,
    lambda_per_day: float = 3.0,
    tau_min: int = 5,
    tau_max: int = 90,
    p_noise_sigma: float = 0.12,
    slip_max: float = 0.01,
    seed: int = 12345
) -> List[Market]:
    rng_local = np.random.default_rng(seed)
    markets: List[Market] = []
    for day in range(T_days):
        n_new = rng_local.poisson(lam=lambda_per_day)
        for _ in range(n_new):
            m = float(rng_local.uniform(0.05, 0.95))
            p = float(np.clip(m + rng_local.normal(0.0, p_noise_sigma), 0.0, 1.0))
            a = float(rng_local.uniform(0.0, slip_max))
            tau = int(rng_local.integers(tau_min, tau_max+1))
            settle_day = day + tau
            scale = float(rng_local.uniform(0.5, 1.5))
            q_true = float(np.clip(p * scale, 0.0, 1.0))
            outcome_yes = int(rng_local.random() < q_true)
            markets.append(Market(day=day, tau=tau, settle_day=settle_day,
                                  m=m, p=p, a=a, q_true=q_true, outcome_yes=outcome_yes))
    markets.sort(key=lambda x: x.day)
    return markets

def simulate(world: List[Market],
             theta: float = 0.5,
             k: float = 0.6,
             W0: float = 100000.0,
             T_days: int = 365) -> SimResult:
    cash = W0
    locked_positions: List[Position] = []
    locked_cost = 0.0

    wealth_path = []
    cash_path = []
    locked_cost_path = []
    locked_ratio_path = []

    # index by arrival day
    by_day: Dict[int, List[Market]] = {}
    for m in world:
        by_day.setdefault(m.day, []).append(m)

    wins = 0
    n_yes_orders = 0
    n_no_orders = 0
    total_orders = 0

    max_day = T_days
    for day in range(max_day+1):
        # 1) allocate into today's markets
        todays = by_day.get(day, [])

        gross = cash + locked_cost
        budget = max(0.0, k * gross - locked_cost)

        # build candidates with priority score
        candidates = []
        for mkt in todays:
            cY = clip_cost(mkt.m + mkt.a)
            cN = clip_cost(1.0 - mkt.m + mkt.a)

            fY_star = kelly_yes_fraction(mkt.p, cY)
            fN_star = kelly_no_fraction(mkt.p, cN)

            scoreY = marginal_gain_per_time_yes(mkt.p, cY, mkt.tau)
            scoreN = marginal_gain_per_time_no(mkt.p, cN, mkt.tau)

            # choose side with higher marginal per-time score
            if scoreY >= scoreN:
                side = 'YES'
                score = scoreY
                c_cost = cY
                f_star = fY_star
            else:
                side = 'NO'
                score = scoreN
                c_cost = cN
                f_star = fN_star

            if score > 0.0 and f_star > 0.0:
                f_cap = min(0.95, theta * f_star)
                desired_dollars = f_cap * gross
                candidates.append((score, side, c_cost, mkt, f_cap, desired_dollars))

        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, side, c_cost, mkt, f_cap, desired_dollars in candidates:
            if budget <= EPS:
                break
            spend = min(desired_dollars, budget)
            if spend <= EPS:
                continue
            shares = spend / c_cost
            locked_positions.append(Position(
                side=side, cost=c_cost, shares=shares, notional_cost=spend,
                open_day=day, settle_day=mkt.settle_day, outcome_yes=mkt.outcome_yes
            ))
            cash -= spend
            locked_cost += spend
            budget -= spend
            total_orders += 1
            if side == 'YES':
                n_yes_orders += 1
            else:
                n_no_orders += 1

        # 2) settle positions whose settle_day == day
        new_locked_positions: List[Position] = []
        for pos in locked_positions:
            if pos.settle_day == day:
                win = 1 if (pos.side == 'YES' and pos.outcome_yes == 1) or (pos.side == 'NO' and pos.outcome_yes == 0) else 0
                if win:
                    cash += pos.shares * 1.0  # payout $1 per share
                    wins += 1
                # remove locked cost
                locked_cost -= pos.notional_cost
            else:
                new_locked_positions.append(pos)
        locked_positions = new_locked_positions

        # record paths (after settlement)
        gross = cash + locked_cost
        wealth_path.append(gross)
        cash_path.append(cash)
        locked_cost_path.append(locked_cost)
        locked_ratio_path.append(0.0 if gross <= 0 else locked_cost / gross)

    final_wealth = wealth_path[-1] if wealth_path else W0
    daily_log_growth = (0.0 if final_wealth <= 0 else (math.log(final_wealth / W0) / max(1, T_days)))

    return SimResult(
        wealth_path=wealth_path, cash_path=cash_path, locked_cost_path=locked_cost_path,
        locked_ratio_path=locked_ratio_path, positions_count=total_orders, wins_count=wins,
        n_yes=n_yes_orders, n_no=n_no_orders, final_wealth=final_wealth,
        theta=theta, daily_log_growth=daily_log_growth
    )

def optimize_theta(world: List[Market], k: float, W0: float, T_days: int) -> float:
    # Simple pattern search over theta in [0.05, 1.0]
    theta = 0.5
    step = 0.25
    best_score = simulate(world, theta=theta, k=k, W0=W0, T_days=T_days).daily_log_growth

    for _ in range(12):
        improved = False
        for delta in [+step, -step]:
            cand = max(0.05, min(1.0, theta + delta))
            score = simulate(world, theta=cand, k=k, W0=W0, T_days=T_days).daily_log_growth
            if score > best_score + 1e-9:
                theta = cand
                best_score = score
                improved = True
        if not improved:
            step *= 0.6
            if step < 0.02:
                break
    return theta

# ----------------------------
# Run experiment
# ----------------------------

T_days = 365
W0 = 100.0
k = 0.6

world = generate_world(
    T_days=T_days,
    lambda_per_day=3.0,
    tau_min=5,
    tau_max=90,
    p_noise_sigma=0.12,
    slip_max=0.01,
    seed=232341
)

theta_star = optimize_theta(world, k=k, W0=W0, T_days=T_days)
sim = simulate(world, theta=theta_star, k=k, W0=W0, T_days=T_days)

print(f"优化后的 theta*: {theta_star:.3f}")
print(f"最终资产: {sim.final_wealth:,.2f} (收益: {sim.final_wealth - W0:,.2f})")
print(f"平均每日收益: {sim.daily_log_growth:.6f}  -> 年化收益 ~ {sim.daily_log_growth*365:.4f}")
print(f"下单总数: {sim.positions_count} (YES: {sim.n_yes}, NO: {sim.n_no}), 赢单数: {sim.wins_count}")
print(f"平均锁仓比例: {np.mean(sim.locked_ratio_path):.3f}, 最大锁仓比例: {np.max(sim.locked_ratio_path):.3f}")

# Plot profit curve (single chart as required)
plt.figure(figsize=(9, 5))
profit = np.array(sim.wealth_path) - W0
plt.plot(range(len(profit)), profit)
plt.title("Profit Curve (Wealth - Initial)")
plt.xlabel("Day")
plt.ylabel("Profit")
plt.tight_layout()
plt.show()
