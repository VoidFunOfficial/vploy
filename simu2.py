# %%
# Re-define everything needed: Event, AllocationResult, allocate_short_term_events,
# then the streaming simulation using that allocator.

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
import math, random
import matplotlib.pyplot as plt

# -------------------- Core dataclasses --------------------

@dataclass
class Event:
    m: float       # market YES price (0..1)
    p: float       # our YES probability
    t: float       # time to resolution (days)
    a: float       # risk factor (>=0)
    name: str = "" # optional identifier

@dataclass
class AllocationResult:
    index: int
    name: str
    side: str                 # 'BUY_YES' | 'BUY_NO' | 'NO_TRADE'
    m: float
    p_raw: float
    p_adj: float
    t_days: float
    a: float
    kelly_f: float            # final fraction of base wealth B allocated (after xi)
    alloc_cents: int
    entry_price: float        # price for the direction we buy (YES or NO)
    shares: float
    EV_cents_if_hold: int     # expected P&L if held to resolution (based on p_adj)
    value_score_open: float   # marginal log-growth per "effective time" at f->0

# -------------------- Math utilities --------------------

EPS  = 1e-12
TICK = 0.01

def clamp01(x: float, lo: float = 0.01, hi: float = 0.99) -> float:
    return float(min(max(x, lo), hi))

def gprime(success_prob: float, entry_price: float, f: float) -> float:
    """
    Derivative of Kelly log-growth:
    g(f) = s * ln(1 + f*b) + (1-s) * ln(1 - f), where b = 1/r - 1
    g'(f) = s*b/(1+f*b) - (1-s)/(1-f)
    """
    b = (1.0 / entry_price) - 1.0
    return (success_prob * b) / (1.0 + f * b) - (1.0 - success_prob) / (1.0 - f)

def kelly_unconstrained(s: float, r: float) -> float:
    """
    For a 0/1 payoff asset priced at r with success prob s,
    unconstrained Kelly fraction (fraction of bankroll) is:
        f* = (s - r) / (1 - r)    if s > r else 0
    """
    if s <= r + EPS:
        return 0.0
    return max(0.0, min((s - r) / (1.0 - r), 0.999999))

def optimize_allocation_timeweighted(
    sides: List[str],
    s_vec: List[float],
    r_vec: List[float],
    D_vec: List[float],
    kappa_frac: float
) -> Tuple[List[float], float]:
    """
    Water-filling (Lagrange multiplier) to maximize sum_i g_i(f_i)/D_i,
    subject to sum_i f_i <= kappa_frac, 0 <= f_i <= f_i_cap (unconstrained Kelly).

    Returns:
        f_opt: optimal fractions (relative to base wealth B)
        lambda_star: shadow price of capital (marginal value)
    """
    n = len(s_vec)
    tradable = [1 if sides[i] != "NO_TRADE" else 0 for i in range(n)]
    D = [max(1.0, float(d)) for d in D_vec]
    f_cap = [kelly_unconstrained(s_vec[i], r_vec[i]) if tradable[i] else 0.0 for i in range(n)]

    if sum(f_cap) <= kappa_frac + 1e-12:
        return f_cap, 0.0

    def f_i_lambda(i: int, lam: float) -> float:
        if not tradable[i]:
            return 0.0
        s, r, t = s_vec[i], r_vec[i], D[i]
        cap = f_cap[i]
        if s <= r + EPS or cap <= 0:
            return 0.0
        if gprime(s, r, 0.0) / t <= lam + 1e-18:
            return 0.0
        if gprime(s, r, cap * 0.999) / t >= lam - 1e-18:
            return cap
        lo, hi = 0.0, cap
        for _ in range(64):
            mid = 0.5 * (lo + hi)
            val = gprime(s, r, mid) / t
            if val > lam:
                lo = mid
            else:
                hi = mid
        return max(0.0, min(lo, cap))

    lam_lo, lam_hi = 0.0, 0.0
    for i in range(n):
        if tradable[i]:
            lam_hi = max(lam_hi, gprime(s_vec[i], r_vec[i], 0.0) / D[i])
    lam_hi *= 1.2 if lam_hi > 0 else 1.0

    for _ in range(72):
        lam_mid = 0.5 * (lam_lo + lam_hi)
        f_sum = sum(f_i_lambda(i, lam_mid) for i in range(n))
        if f_sum > kappa_frac:
            lam_lo = lam_mid
        else:
            lam_hi = lam_mid

    lam_star = lam_lo
    f_opt = [f_i_lambda(i, lam_star) for i in range(n)]
    return f_opt, lam_star

# -------------------- Main allocator (short-term–biased) --------------------

def allocate_short_term_events(
    events: List[Event],
    M_cents: int,
    kappa: float,
    xi: float = 0.5,
    tau_exp: float = 2.0,
    shrink_with_a: bool = True
) -> Dict[str, Any]:
    """
    对一批 Event{m,p,t,a} 做一次性分配：
    - 用 Kelly + 时间加权 (1 / t^tau_exp) 优先短线，
    - 在锁定比例 kappa 下，最多动用 kappa * M_cents 的资金，
    - 用分数 Kelly 系数 xi 控制整体激进度。
    """
    assert 0.0 <= kappa <= 1.0
    assert 0.0 <= xi <= 1.0

    B_cents = int(M_cents)
    budget_cents = int(round(kappa * B_cents))

    if budget_cents <= 0 or len(events) == 0:
        return {
            "meta": {
                "B_cents": B_cents,
                "budget_cents": budget_cents,
                "kappa": kappa,
                "xi": xi,
                "tau_exp": tau_exp,
                "lambda_star": 0.0,
                "used_cents": 0
            },
            "allocations": []
        }

    sides: List[str]   = []
    s_vec: List[float] = []
    r_vec: List[float] = []
    D_vec: List[float] = []
    p_adj_vec: List[float] = []

    for ev in events:
        m = clamp01(ev.m)
        p = clamp01(ev.p)
        a = max(0.0, float(ev.a))
        t = max(1.0, float(ev.t))

        p_adj = m + (p - m) / (1.0 + a) if shrink_with_a else p
        p_adj = clamp01(p_adj, 1e-6, 1 - 1e-6)

        if p_adj > m + 1e-9:
            side = "BUY_YES"; s = p_adj; r = m
        elif p_adj < m - 1e-9:
            side = "BUY_NO";  s = 1.0 - p_adj; r = 1.0 - m
        else:
            side = "NO_TRADE"; s = 0.0; r = 1.0  # dummy

        sides.append(side)
        s_vec.append(s)
        r_vec.append(max(TICK, r))
        D_vec.append(t ** tau_exp)      # 更强惩罚长久期
        p_adj_vec.append(p_adj)

    # 将预算换算为“相对 B 的比例”；再除以 xi 作为 solver 的上限
    kappa_frac_raw = budget_cents / max(1, B_cents)
    kappa_frac_for_solver = min(kappa_frac_raw / max(xi, 1e-9), 1.0)

    f_star, lambda_star = optimize_allocation_timeweighted(
        sides, s_vec, r_vec, D_vec, kappa_frac_for_solver
    )
    f_use = [xi * f if sides[i] != "NO_TRADE" else 0.0 for i, f in enumerate(f_star)]

    # 初步换算为金额（美分）
    cents = [int(round(B_cents * f)) for f in f_use]
    total = sum(cents)
    if total > budget_cents and total > 0:
        scale = budget_cents / total
        cents = [int(math.floor(c * scale)) for c in cents]
    # 把零头分给 f_use 较大的事件
    residual = budget_cents - sum(cents)
    if residual > 0:
        order = sorted(range(len(events)), key=lambda i: f_use[i], reverse=True)
        k = 0
        while residual > 0 and order:
            j = order[k % len(order)]
            cents[j] += 1
            residual -= 1
            k += 1

    allocs: List[AllocationResult] = []
    used_cents = 0

    for i, ev in enumerate(events):
        name = ev.name if ev.name else f"ev_{i}"
        side = sides[i]
        if side == "NO_TRADE" or cents[i] <= 0:
            allocs.append(AllocationResult(
                index=i, name=name, side="NO_TRADE",
                m=ev.m, p_raw=ev.p, p_adj=p_adj_vec[i],
                t_days=ev.t, a=ev.a,
                kelly_f=0.0, alloc_cents=0,
                entry_price=0.0, shares=0.0,
                EV_cents_if_hold=0,
                value_score_open=0.0
            ))
            continue

        entry_r = r_vec[i]
        alloc   = cents[i]
        shares  = alloc / (entry_r * 100.0)

        if side == "BUY_YES":
            EV_per_dollar = p_adj_vec[i] / ev.m - 1.0
        else:
            EV_per_dollar = (1.0 - p_adj_vec[i]) / (1.0 - ev.m) - 1.0
        EV_cents = int(round(alloc * EV_per_dollar))

        value_score_open = 0.0
        if s_vec[i] > 0:
            value_score_open = gprime(s_vec[i], entry_r, 0.0) / D_vec[i]

        allocs.append(AllocationResult(
            index=i, name=name, side=side,
            m=ev.m, p_raw=ev.p, p_adj=p_adj_vec[i],
            t_days=ev.t, a=ev.a,
            kelly_f=float(f_use[i]), alloc_cents=int(alloc),
            entry_price=float(entry_r), shares=float(shares),
            EV_cents_if_hold=int(EV_cents),
            value_score_open=float(value_score_open)
        ))
        used_cents += int(alloc)

    return {
        "meta": {
            "B_cents": B_cents,
            "budget_cents": budget_cents,
            "kappa": kappa,
            "xi": xi,
            "tau_exp": tau_exp,
            "lambda_star": float(lambda_star),
            "used_cents": used_cents
        },
        "allocations": allocs
    }

# -------------------- Streaming simulation using new allocator --------------------

@dataclass
class Position:
    name: str
    side: str          # 'BUY_YES' or 'BUY_NO'
    entry_price: float
    shares: float
    cost_cents: int
    open_day: int
    settle_day: int
    p_true: float      # true YES probability

def poisson_sample(lam: float) -> int:
    L = math.exp(-lam)
    k = 0
    acc = 1.0
    while True:
        k += 1
        acc *= random.random()
        if acc <= L:
            return k - 1

def simulate_strategy_once(
    days: int = 180,
    M_cents: int = 100_000,
    kappa_global: float = 0.7,
    xi: float = 0.5,
    tau_exp: float = 2.0,
    lam_new_per_day: float = 3.0,
    max_tau: int = 60,
    noise_pct: float = 0.15,
    sigma_market: float = 0.10,
    seed: int = 123
) -> Dict[str, Any]:
    """
    使用短线偏好的 Kelly 分配器，模拟多个交易日：
    - 每日新市场到达（泊松分布），真实概率 p_true，市场价 m_yes，预测 p_pred 和风险因子 a_pred
      都相对真实值有 ±noise_pct 的浮动；
    - 资金总额 M_cents，允许最多锁定 kappa_global * (现金+已锁定成本)，
      通过短线偏好分配器给当日新市场分配仓位；
    - 不止损、不中途止盈，只在结算日按真实结果兑现。
    """
    random.seed(seed)

    cash_cents = int(M_cents)
    open_positions: List[Position] = []

    history = {
        "day": [],
        "cash_cents": [],
        "locked_cents": [],
        "wealth_cents": [],
        "locked_frac": [],
        "n_open": [],
        "n_new": [],
        "invested_today_cents": [],
        "pnl_today_cents": [],
    }
    trades: List[Dict[str, Any]] = []
    total_markets_seen = 0

    for day in range(days):
        # 1) 结算当日到期的仓位
        pnl_today = 0
        new_open_positions: List[Position] = []
        locked_cents = 0

        for pos in open_positions:
            if pos.settle_day == day:
                if pos.side == "BUY_YES":
                    success_prob = pos.p_true
                else:
                    success_prob = 1.0 - pos.p_true
                win = (random.random() < success_prob)
                payout_cents = int(round(pos.shares * 100.0 * (1 if win else 0)))
                pnl = payout_cents - pos.cost_cents
                cash_cents += payout_cents
                pnl_today += pnl
                trades.append({
                    "open_day": pos.open_day,
                    "settle_day": pos.settle_day,
                    "name": pos.name,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "shares": pos.shares,
                    "p_true": pos.p_true,
                    "payout_cents": payout_cents,
                    "cost_cents": pos.cost_cents,
                    "pnl_cents": pnl
                })
            else:
                new_open_positions.append(pos)
                locked_cents += pos.cost_cents

        open_positions = new_open_positions
        B_cents = cash_cents + locked_cents

        # 2) 生成今日新市场
        n_new = poisson_sample(lam_new_per_day) if B_cents > 0 else 0
        events_today: List[Event] = []
        p_true_list: List[float] = []
        t_list: List[int] = []

        for j in range(n_new):
            p_true = max(0.01, min(0.99, random.betavariate(2, 2)))
            m_yes = max(0.01, min(0.99, p_true + random.gauss(0.0, sigma_market)))
            eps_p = random.uniform(-noise_pct, noise_pct)
            p_pred = max(0.01, min(0.99, p_true * (1.0 + eps_p)))
            a_true = random.uniform(0.0, 2.0)
            eps_a = random.uniform(-noise_pct, noise_pct)
            a_pred = max(0.0, a_true * (1.0 + eps_a))
            t_days = int(round(max(1.0, random.triangular(1.0, max_tau, 8.0))))
            name = f"D{day}_E{j}"

            events_today.append(Event(m=m_yes, p=p_pred, t=t_days, a=a_pred, name=name))
            p_true_list.append(p_true)
            t_list.append(t_days)

        total_markets_seen += n_new
        invested_today = 0

        # 3) 用短线偏好的 Kelly 分配当日新市场
        if events_today and B_cents > 0:
            allowed_new_locked = max(0, int(round(kappa_global * B_cents - locked_cents)))
            if allowed_new_locked > 0:
                kappa_local = allowed_new_locked / B_cents
                res_alloc = allocate_short_term_events(
                    events_today,
                    M_cents=B_cents,
                    kappa=kappa_local,
                    xi=xi,
                    tau_exp=tau_exp,
                    shrink_with_a=True
                )
                for ar in res_alloc["allocations"]:
                    if ar.alloc_cents <= 0 or ar.side == "NO_TRADE":
                        continue
                    if ar.alloc_cents > cash_cents:
                        continue  # 不应该发生，保险
                    idx = ar.index
                    t_days = t_list[idx]
                    settle_day = day + t_days
                    p_true = p_true_list[idx]
                    shares = ar.alloc_cents / (ar.entry_price * 100.0)

                    pos = Position(
                        name=ar.name,
                        side=ar.side,
                        entry_price=ar.entry_price,
                        shares=shares,
                        cost_cents=ar.alloc_cents,
                        open_day=day,
                        settle_day=settle_day,
                        p_true=p_true
                    )
                    cash_cents -= ar.alloc_cents
                    invested_today += ar.alloc_cents
                    open_positions.append(pos)

        # 4) 记录当日状态
        locked_cents = sum(p.cost_cents for p in open_positions)
        B_cents = cash_cents + locked_cents
        locked_frac = (locked_cents / B_cents) if B_cents > 0 else 0.0

        history["day"].append(day)
        history["cash_cents"].append(cash_cents)
        history["locked_cents"].append(locked_cents)
        history["wealth_cents"].append(B_cents)
        history["locked_frac"].append(locked_frac)
        history["n_open"].append(len(open_positions))
        history["n_new"].append(n_new)
        history["invested_today_cents"].append(invested_today)
        history["pnl_today_cents"].append(pnl_today)

    # 5) 最后将剩余仓位全部按真实概率结算，得到最终财富
    final_pnl = 0
    for pos in open_positions:
        if pos.side == "BUY_YES":
            success_prob = pos.p_true
        else:
            success_prob = 1.0 - pos.p_true
        win = (random.random() < success_prob)
        payout_cents = int(round(pos.shares * 100.0 * (1 if win else 0)))
        pnl = payout_cents - pos.cost_cents
        final_pnl += pnl
        cash_cents += payout_cents
        trades.append({
            "open_day": pos.open_day,
            "settle_day": pos.settle_day,
            "name": pos.name,
            "side": pos.side,
            "entry_price": pos.entry_price,
            "shares": pos.shares,
            "p_true": pos.p_true,
            "payout_cents": payout_cents,
            "cost_cents": pos.cost_cents,
            "pnl_cents": pnl
        })

    end_wealth_cents = cash_cents
    summary = {
        "days": days,
        "start_cents": M_cents,
        "end_cents": end_wealth_cents,
        "absolute_return_pct": (end_wealth_cents / M_cents - 1.0) * 100.0,
        "total_markets_seen": total_markets_seen,
        "total_trades": len(trades),
        "avg_locked_frac": sum(history["locked_frac"]) / max(1, len(history["locked_frac"])),
        "kappa_global": kappa_global,
        "xi": xi,
        "tau_exp": tau_exp,
        "lam_new_per_day": lam_new_per_day,
        "noise_pct": noise_pct,
        "sigma_market": sigma_market,
        "max_tau": max_tau
    }
    return {"history": history, "trades": trades, "summary": summary}

def monte_carlo_simulation(
    n_runs: int = 20,
    days: int = 180,
    M_cents: int = 100_000,
    kappa_global: float = 0.7,
    xi: float = 0.5,
    tau_exp: float = 2.0,
    lam_new_per_day: float = 3.0,
    max_tau: int = 60,
    noise_pct: float = 0.15,
    sigma_market: float = 0.10,
    base_seed: int = 2025
) -> Dict[str, Any]:
    """
    多次独立模拟，观察收益分布。
    """
    summaries = []
    for i in range(n_runs):
        seed = base_seed + i
        out = simulate_strategy_once(
            days=days,
            M_cents=M_cents,
            kappa_global=kappa_global,
            xi=xi,
            tau_exp=tau_exp,
            lam_new_per_day=lam_new_per_day,
            max_tau=max_tau,
            noise_pct=noise_pct,
            sigma_market=sigma_market,
            seed=seed
        )
        summaries.append(out["summary"])

    final_returns = [s["absolute_return_pct"] for s in summaries]
    end_wealth = [s["end_cents"] for s in summaries]
    avg_ret = sum(final_returns) / len(final_returns)
    min_ret = min(final_returns)
    max_ret = max(final_returns)

    print("=== Monte Carlo summary (short-term-biased strategy) ===")
    print(f"Runs: {n_runs}, Days per run: {days}, Start bankroll: ${M_cents/100:.2f}")
    print(f"Average final wealth: ${sum(end_wealth)/n_runs/100:.2f}")
    print(f"Average return: {avg_ret:.2f}%")
    print(f"Min return: {min_ret:.2f}%  |  Max return: {max_ret:.2f}%")

    plt.figure()
    plt.hist(final_returns, bins=10)
    plt.xlabel("Final return (%)")
    plt.ylabel("Frequency")
    plt.title("Distribution of final returns (short-term-biased Kelly, Monte Carlo)")
    plt.show()

    return {"summaries": summaries, "final_returns": final_returns, "end_wealth": end_wealth}


# ------------- Run one path + Monte Carlo demo -------------
if __name__ == "__main__":
    # 单次路径：看资金曲线、锁定比例
    single = simulate_strategy_once(
        days=30,
        M_cents=100_000,      # $1000
        kappa_global=0.7,
        xi=0.5,
        tau_exp=2.0,          # 强调短线
        lam_new_per_day=3.0,
        max_tau=30,
        noise_pct=0.2,
        sigma_market=0.10,
        seed=1432
    )
    print("=== Single-run summary ===")
    for k, v in single["summary"].items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")

    days_axis = single["history"]["day"]
    wealth = [w/100.0 for w in single["history"]["wealth_cents"]]
    locked_frac = single["history"]["locked_frac"]

    plt.figure()
    plt.plot(days_axis, wealth)
    plt.xlabel("Day")
    plt.ylabel("Wealth ($)")
    plt.title("Wealth trajectory (single run)")
    plt.show()

    plt.figure()
    plt.plot(days_axis, locked_frac)
    plt.xlabel("Day")
    plt.ylabel("Locked fraction")
    plt.title("Locked capital fraction over time (single run)")
    plt.show()

    # 多次模拟收益分布
    mc = monte_carlo_simulation(
        n_runs=20,
        days=180,
        M_cents=100_000,
        kappa_global=0.4,
        xi=0.3,
        tau_exp=2.0,
        lam_new_per_day=3.0,
        max_tau=30,
        noise_pct=0.15,
        sigma_market=0.10,
        base_seed=1432
    )
