# %%
# Simulation-augmented version (NO take-profit; hold to settlement).
# - Kelly sizing with time discount and risk shrink
# - Capacity cap kappa to preserve cash for future opportunities
# - Streaming markets: new markets appear over time with random settlement horizons
# - Forecast and risk factor have ±X% fluctuation vs. reality
#
# This cell both DEFINES the functions and RUNS a small simulation with random data.
# You can rerun with different parameters at the bottom.

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
import math, random
import matplotlib.pyplot as plt

# ------------------------ Core math ------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return float(min(max(x, lo), hi))

def gprime(s: float, r: float, f: float) -> float:
    """
    Derivative of expected log growth for a binary payoff share priced at r, success prob s.
    g'(f) = s*b/(1+f*b) - (1-s)/(1-f), where b = 1/r - 1
    """
    b = (1.0 / r) - 1.0
    return (s * b) / (1.0 + f * b) - (1.0 - s) / (1.0 - f)

def kelly_unconstrained(s: float, r: float) -> float:
    """
    For a binary 0/1 asset priced r with success prob s:
    Unconstrained Kelly fraction f* = (s - r) / (1 - r) if s > r else 0.
    (This is for the 'long the asset' side. For NO side we pass s=1-p and r=1-m.)
    """
    if s <= r:
        return 0.0
    return max(0.0, min((s - r) / (1.0 - r), 0.999999))

def optimize_allocation_per_time(
    s_list: List[float],
    r_list: List[float],
    tau_list: List[float],
    kappa: float
) -> List[float]:
    """
    Solve: maximize sum_i g_i(f_i)/tau_i  s.t. sum_i f_i <= kappa, 0<=f_i<=f_i_unconstrained
    Using Lagrange water-filling via bisection on lambda.
    """
    n = len(s_list)
    tau = [max(1e-9, float(t)) for t in tau_list]
    # Unconstrained Kelly caps
    f_free = [kelly_unconstrained(s_list[i], r_list[i]) for i in range(n)]
    # If sum free <= kappa, return them
    if sum(f_free) <= kappa + 1e-12:
        return f_free

    def f_i_given_lambda(i: int, lam: float) -> float:
        s, r, t = s_list[i], r_list[i], tau[i]
        f_cap = f_free[i]
        if f_cap <= 0:
            return 0.0
        if gprime(s, r, 0.0) / t <= lam:
            return 0.0
        # If even near cap derivative >= lam -> take cap
        if gprime(s, r, f_cap * 0.999) / t >= lam:
            return f_cap
        lo, hi = 0.0, f_cap
        for _ in range(60):
            mid = 0.5*(lo+hi)
            val = gprime(s, r, mid) / t
            if val > lam:
                lo = mid
            else:
                hi = mid
        return max(0.0, min(lo, f_cap))

    # Lambda bracket
    lam_lo, lam_hi = 0.0, 0.0
    for i in range(n):
        lam_hi = max(lam_hi, gprime(s_list[i], r_list[i], 0.0) / tau[i])
    lam_hi *= 1.2 if lam_hi > 0 else 1.0

    for _ in range(70):
        lam_mid = 0.5*(lam_lo + lam_hi)
        f_sum = sum(f_i_given_lambda(i, lam_mid) for i in range(n))
        if f_sum > kappa:
            lam_lo = lam_mid
        else:
            lam_hi = lam_mid
    lam_star = lam_lo
    return [f_i_given_lambda(i, lam_star) for i in range(n)]

# ------------------------ Policy (no take-profit) ------------------------

@dataclass
class Market:
    day_index: int        # arrival day
    name: str
    m_yes: float          # market price for YES (0..1)
    p_pred: float         # our predicted YES prob (decision uses this)
    p_true: float         # true YES prob (for settlement simulation)
    a_pred: float         # risk factor used by our policy
    a_true: float         # "true" underlying risk (for record)
    t_days: int           # settlement days from arrival

@dataclass
class Position:
    market_name: str
    side: str             # "YES" or "NO"
    entry_price: float    # price of the side we long (YES price or NO price)
    shares: float
    cost_cents: int
    open_day: int
    settle_day: int
    p_true: float         # true YES probability

def p_shrink_with_risk(m: float, p: float, a: float) -> float:
    """Shrink p toward m by factor (1+a) to reflect risk/uncertainty."""
    return clamp(m + (p - m) / (1.0 + max(0.0, a)), 1e-6, 1 - 1e-6)

# ------------------------ Streaming simulation ------------------------

def poisson_sample(lam: float) -> int:
    """Knuth's method for Poisson(lam) nonnegative integer sampling."""
    L = math.exp(-lam)
    k = 0
    acc = 1.0
    while True:
        k += 1
        acc *= random.random()
        if acc <= L:
            return k - 1

def generate_markets_for_day(
    day: int,
    n_new: int,
    max_tau: int,
    noise_pct: float,
    skill_sigma: float
) -> List[Market]:
    """
    Create n_new markets with:
    - m_yes ~ Beta(2,2)
    - p_pred = clamp(m_yes + Normal(0, skill_sigma))
    - p_true = clamp(p_pred * (1 + U[-noise_pct, +noise_pct]))
    - a_pred ~ U[0, 2], a_true = a_pred*(1+U[-noise_pct, +noise_pct])
    - t_days ~ triangular [1, max_tau], mode near short horizon
    """
    out = []
    for j in range(n_new):
        m = clamp(random.betavariate(2, 2), 0.01, 0.99)
        p_pred = clamp(m + random.gauss(0.0, skill_sigma), 0.01, 0.99)
        eps = random.uniform(-noise_pct, noise_pct)
        p_true = clamp(p_pred * (1.0 + eps), 0.01, 0.99)
        a_pred = random.uniform(0.0, 2.0)
        a_true = max(0.0, a_pred * (1.0 + random.uniform(-noise_pct, noise_pct)))
        # settlement horizon: more weight on short
        t_days = int(round(clamp(random.triangular(1, max_tau, 4), 1, max_tau)))
        out.append(Market(
            day_index=day,
            name=f"D{day}_M{j}",
            m_yes=m,
            p_pred=p_pred,
            p_true=p_true,
            a_pred=a_pred,
            a_true=a_true,
            t_days=t_days
        ))
    return out

def allocate_today(
    markets_today: List[Market],
    wealth_base_cents: int,
    free_cents: int,
    xi_fraction: float,
    tau_pref: float
) -> List[Tuple[Market, int, str, float]]:
    """
    Decide how much to allocate to each of today's markets (no rebalancing of prior positions).
    Returns list of (market, alloc_cents, side, entry_price).
    - Uses risk-shrunk p' and time-normalized water-filling.
    - Then multiplies by xi_fraction (fractional Kelly) and fits to free_cents.
    """
    if not markets_today or free_cents <= 0 or wealth_base_cents <= 0:
        return []

    # Prepare s (success prob), r (entry price), tau for each market using p' (risk shrink)
    s_list, r_list, tau_list = [], [], []
    sides = []
    for mk in markets_today:
        p_adj = p_shrink_with_risk(mk.m_yes, mk.p_pred, mk.a_pred)
        if p_adj > mk.m_yes:          # long YES
            s, r, side = p_adj, mk.m_yes, "YES"
        elif p_adj < mk.m_yes:        # long NO
            s, r, side = 1.0 - p_adj, 1.0 - mk.m_yes, "NO"
        else:
            s, r, side = 0.0, 0.0, "SKIP"
        s_list.append(s)
        r_list.append(r if r > 1e-6 else 1e-6)
        tau_list.append(max(1.0, float(mk.t_days)))  # at least 1 day
        sides.append(side)

    # Fractional Kelly via scaling kappa upward before applying xi.
    free_frac = free_cents / wealth_base_cents
    kappa_for_solver = min(max(free_frac / max(1e-9, xi_fraction), 0.0), 1.0)

    f_sol = optimize_allocation_per_time(s_list, r_list, tau_list, kappa_for_solver)
    f_use = [xi_fraction * f for f in f_sol]

    # Turn into cents, fit to free_cents with proportional scaling
    cents = [int(math.floor(f * wealth_base_cents)) for f in f_use]
    total = sum(cents)
    if total > free_cents and total > 0:
        scale = free_cents / total
        cents = [int(math.floor(c * scale)) for c in cents]
    # distribute rounding residual
    residual = free_cents - sum(cents)
    if residual > 0:
        order = sorted(range(len(markets_today)),
                       key=lambda j: f_use[j], reverse=True)
        k = 0
        while residual > 0 and order:
            j = order[k % len(order)]
            cents[j] += 1
            residual -= 1
            k += 1

    allocs = []
    for mk, c, side, r in zip(markets_today, cents, sides, r_list):
        if side == "SKIP" or c <= 0:
            continue
        allocs.append((mk, c, side, r))
    return allocs

def simulate_stream(
    days: int = 90,
    M_cents: int = 100_00,
    lam_new_per_day: float = 3.0,
    max_tau: int = 30,
    xi_fraction: float = 0.5,
    kappa: float = 0.7,
    tau_pref: float = 7.0,
    noise_pct: float = 0.12,       # X% fluctuation for p and a
    skill_sigma: float = 0.08,     # forecasting displacement vs market
    seed: int = 42
) -> Dict[str, Any]:
    """
    Run a streaming simulation for `days`.
    - M_cents: starting bankroll (cents)
    - lam_new_per_day: Poisson intensity of new markets per day
    - max_tau: max settlement horizon (days)
    - xi_fraction: fractional Kelly
    - kappa: max proportion of wealth_base we allow to be locked (cost) at any time
    - tau_pref: time preference constant (only used inside allocation_per_time via tau_list)
    - noise_pct: ±X% fluctuation between our p_pred/a_pred and reality
    - skill_sigma: our forecast displacement vs market price (Normal std)
    """
    random.seed(seed)

    cash_cents = int(M_cents)
    open_positions: List[Position] = []
    history = {
        "day": [], "cash_cents": [], "open_cost_cents": [],
        "wealth_base_cents": [], "locked_frac": [], "n_open": [],
        "n_new": [], "invested_today_cents": [], "pnl_today_cents": []
    }
    all_trades = []
    all_markets_seen = 0

    for day in range(days):
        # 1) settle matured
        pnl_today = 0
        remaining_positions = []
        open_cost_cents = 0

        for pos in open_positions:
            if pos.settle_day == day:
                # Resolve outcome
                if pos.side == "YES":
                    success_prob = pos.p_true
                else:
                    success_prob = 1.0 - pos.p_true
                win = (random.random() < success_prob)
                payout_cents = int(round(pos.shares * 100.0 * (1 if win else 0)))
                pnl = payout_cents - pos.cost_cents
                cash_cents += payout_cents  # cost already paid at entry
                pnl_today += pnl
                all_trades.append({
                    "open_day": pos.open_day,
                    "settle_day": pos.settle_day,
                    "market": pos.market_name,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "shares": pos.shares,
                    "p_true": pos.p_true,
                    "payout_cents": payout_cents,
                    "cost_cents": pos.cost_cents,
                    "pnl_cents": pnl
                })
            else:
                remaining_positions.append(pos)
                open_cost_cents += pos.cost_cents
        open_positions = remaining_positions

        # Wealth base and capacity
        wealth_base_cents = cash_cents + open_cost_cents
        cap_cents = int(round(kappa * wealth_base_cents))
        free_cents = max(0, cap_cents - open_cost_cents)

        # 2) new markets arrive today
        n_new = poisson_sample(lam_new_per_day)
        markets_today = generate_markets_for_day(day, n_new, max_tau, noise_pct, skill_sigma)
        all_markets_seen += n_new

        # 3) allocate to today's markets using available capacity
        allocs = allocate_today(
            markets_today, wealth_base_cents, free_cents, xi_fraction, tau_pref
        )
        invested_today = 0

        for mk, cents, side, entry_r in allocs:
            if cents <= 0 or cents > cash_cents:
                continue  # cannot spend more than cash
            shares = cents / (100.0 * entry_r)
            settle_day = day + mk.t_days
            pos = Position(
                market_name=mk.name,
                side=side,
                entry_price=entry_r,
                shares=shares,
                cost_cents=cents,
                open_day=day,
                settle_day=settle_day,
                p_true=mk.p_true
            )
            cash_cents -= cents
            open_positions.append(pos)
            invested_today += cents

        # Recompute for record
        open_cost_cents = sum(p.cost_cents for p in open_positions)
        wealth_base_cents = cash_cents + open_cost_cents
        locked_frac = (open_cost_cents / wealth_base_cents) if wealth_base_cents > 0 else 0.0

        history["day"].append(day)
        history["cash_cents"].append(cash_cents)
        history["open_cost_cents"].append(open_cost_cents)
        history["wealth_base_cents"].append(wealth_base_cents)
        history["locked_frac"].append(locked_frac)
        history["n_open"].append(len(open_positions))
        history["n_new"].append(n_new)
        history["invested_today_cents"].append(invested_today)
        history["pnl_today_cents"].append(pnl_today)

    # Optionally settle remaining positions at the end (for final wealth)
    final_pnl = 0
    for pos in open_positions:
        if pos.side == "YES":
            success_prob = pos.p_true
        else:
            success_prob = 1.0 - pos.p_true
        win = (random.random() < success_prob)
        payout_cents = int(round(pos.shares * 100.0 * (1 if win else 0)))
        final_pnl += (payout_cents - pos.cost_cents)
        cash_cents += payout_cents
        all_trades.append({
            "open_day": pos.open_day,
            "settle_day": pos.settle_day,  # may be > days-1
            "market": pos.market_name,
            "side": pos.side,
            "entry_price": pos.entry_price,
            "shares": pos.shares,
            "p_true": pos.p_true,
            "payout_cents": payout_cents,
            "cost_cents": pos.cost_cents,
            "pnl_cents": payout_cents - pos.cost_cents
        })
    open_positions = []

    result = {
        "history": history,
        "trades": all_trades,
        "summary": {
            "days": days,
            "start_cents": M_cents,
            "end_cents": cash_cents,
            "absolute_return_pct": (cash_cents / M_cents - 1.0) * 100.0,
            "total_markets_seen": all_markets_seen,
            "total_trades": len(all_trades),
            "avg_daily_locked_frac": sum(history["locked_frac"]) / max(1, len(history["locked_frac"])),
            "kappa": kappa,
            "xi_fraction": xi_fraction,
            "lam_new_per_day": lam_new_per_day,
            "noise_pct": noise_pct,
            "skill_sigma": skill_sigma,
            "max_tau": max_tau
        }
    }
    return result

# ------------------------ Run a demo simulation ------------------------
if __name__ == "__main__":
    sim = simulate_stream(
        days=30,
        M_cents=100_00,        # $100
        lam_new_per_day=40.0,   # ~3 new markets/day
        max_tau=10,
        xi_fraction=0.5,       # 1/2 Kelly
        kappa=0.7,             # at most 70% of wealth_base locked at any time
        tau_pref=7.0,          # short-term preference
        noise_pct=0.12,        # X = 12% fluctuation between prediction/risk and reality
        skill_sigma=1,      # forecasting deviation vs market
        seed=84
    )

    # Print summary
    summary = sim["summary"]
    print("=== Simulation Summary ===")
    for k, v in summary.items():
        if isinstance(v, float):
            if "return" in k or "locked" in k:
                print(f"{k}: {v:.2f}")
            else:
                print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print()

    # Show last 8 trades
    print("=== Last 8 trades ===")
    for row in sim["trades"][-8:]:
        print({k: row[k] for k in ["open_day","settle_day","market","side","entry_price","shares","p_true","payout_cents","cost_cents","pnl_cents"]})

    # Plot wealth_base over time (cash + open cost), and locked fraction
    days = sim["history"]["day"]
    wealth = sim["history"]["wealth_base_cents"]
    locked = sim["history"]["locked_frac"]

    plt.figure()
    plt.plot(days, [w/100.0 for w in wealth])
    plt.title("Wealth base over time ($)")
    plt.xlabel("Day")
    plt.ylabel("Wealth base ($)")
    plt.show()

    plt.figure()
    plt.plot(days, locked)
    plt.title("Locked fraction over time")
    plt.xlabel("Day")
    plt.ylabel("Locked fraction")
    plt.show()
