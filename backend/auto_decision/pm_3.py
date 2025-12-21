from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Dict, Tuple
import math
import numpy as np
import matplotlib.pyplot as plt

Side = Literal["YES", "NO"]

EPS = 1e-12


def clip01(x: float, eps: float = 1e-6) -> float:
    return float(min(1.0 - eps, max(eps, x)))


def sigmoid(x: float) -> float:
    # stable sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def softplus(x: float) -> float:
    # stable softplus
    if x > 30:
        return x
    return math.log1p(math.exp(x))


@dataclass
class Market:
    """A Polymarket-style binary contract."""
    market_id: int
    price_yes: float          # m
    p_pred_yes: float         # our forecast p
    true_p_yes: float         # probability used to settle in simulation
    days_to_settle: int       # T (>=1)


@dataclass
class Position:
    market_id: int
    side: Side
    entry_price: float        # price paid per share (m for YES, 1-m for NO)
    stake: float              # dollars spent (locked)
    shares: float             # stake / entry_price
    days_left: int            # countdown to settlement
    true_p_yes: float         # for simulation settlement


@dataclass
class Theta:
    """
    Strategy parameters (to be optimized).
    alpha: fractional Kelly multiplier (0..1)
    shrink: shrink p_pred towards market price (0..1)
    eta: liquidity shadow price (>=0). larger => prefer shorter T, keep more liquidity
    f_cap: max stake fraction per market (0..1)
    gamma_cap: extra time-based cap decay (>=0)
    min_edge: minimum |p_hat - m| to act (0..)
    """
    alpha: float = 0.5
    shrink: float = 0.8
    eta: float = 0.002
    f_cap: float = 0.10
    gamma_cap: float = 0.00
    min_edge: float = 0.01


@dataclass
class EnvConfig:
    horizon_days: int = 365
    markets_per_day: float = 3.0
    max_settle_days: int = 60

    # If settle_from_price=True, then true_p_yes := price_yes (as you requested).
    # If False, we create mispricing + prediction skill.
    settle_from_price: bool = True

    # Used when settle_from_price=False:
    beta_a: float = 2.0
    beta_b: float = 2.0
    sigma_market: float = 0.06   # market price noise around true p
    sigma_pred: float = 0.03     # our prediction noise around true p

    # Used when settle_from_price=True:
    sigma_pred_around_price: float = 0.05

    # Settlement time distribution
    geom_p: float = 0.15         # smaller => longer average T


def expected_log_derivative(f: float, p_win: float, price: float) -> float:
    """
    d/df [ p ln(1-f+f/price) + (1-p) ln(1-f) ]
    """
    # A = 1 - f + f/price
    A = 1.0 - f + f / price
    B = 1.0 - f

    # derivative terms
    term_win = p_win * ((1.0 / price) - 1.0) / A
    term_lose = (1.0 - p_win) * (-1.0) / B
    return term_win + term_lose


def optimal_fraction_with_liquidity_penalty(
    p_win: float,
    price: float,
    T_days: int,
    eta: float,
    f_max: float,
    iters: int = 60,
) -> float:
    """
    Solve:
        maximize  g(f) = [E log wealth multiplier]/T - eta*f
    Equivalent FOC:
        Elog'(f) = eta*T

    Because Elog is strictly concave on f in [0,1), we can use bisection on derivative.
    """
    p_win = clip01(p_win)
    price = clip01(price)

    f_max = min(float(f_max), 1.0 - 1e-9)
    if f_max <= 0.0:
        return 0.0

    target = eta * float(T_days)

    # marginal benefit at f=0: Elog'(0) = (p - price) / price
    d0 = (p_win - price) / price
    if d0 <= target:
        return 0.0

    # if even at f_max marginal still above target, we want the max allowed
    d_hi = expected_log_derivative(f_max, p_win, price)
    if d_hi >= target:
        return f_max

    lo, hi = 0.0, f_max
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        d_mid = expected_log_derivative(mid, p_win, price)
        # derivative decreases with f; if too high, increase f
        if d_mid > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def allocate(
    market: Market,
    positions: List[Position],
    total_wealth: float,
    k: float,
    theta: Theta,
) -> Dict[str, float | str]:
    """
    Decide how much to bet on the incoming market given existing positions.

    Inputs:
      - market: Market(price_yes=m, p_pred_yes=p, days_to_settle=T)
      - positions: list of open positions (locked until settlement)
      - total_wealth: current net asset value W (cash + locked at cost)
      - k: reserve ratio in [0,1). Keep at least k*W as liquid cash.
      - theta: strategy params.

    Output dict:
      {
        "stake": dollars to spend,
        "side": "YES"/"NO"/"NONE",
        "shares": shares to buy,
        "price": entry price,
        "p_hat_yes": shrunk probability used,
        "reason": str
      }
    """
    W = float(total_wealth)
    if W <= 0:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": 0.0, "reason": "W<=0"}

    k = float(min(max(k, 0.0), 0.999999))
    locked = sum(p.stake for p in positions)
    cash = W - locked

    # Hard liquidity constraint (reserve)
    reserve_cash = k * W
    spendable_cash = cash - reserve_cash
    if spendable_cash <= 0:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": 0.0, "reason": "cash<=reserve"}

    # Another equivalent hard constraint: total locked <= (1-k)*W
    max_locked = (1.0 - k) * W
    remaining_locked_budget = max_locked - locked
    if remaining_locked_budget <= 0:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": 0.0, "reason": "locked_budget_exhausted"}

    m = clip01(market.price_yes)
    p_pred = clip01(market.p_pred_yes)
    T = int(max(1, market.days_to_settle))

    # Robust shrinkage: move our forecast towards market-implied probability
    shrink = float(min(max(theta.shrink, 0.0), 1.0))
    p_hat_yes = clip01((1.0 - shrink) * m + shrink * p_pred)

    # Decide side by edge threshold
    min_edge = float(max(theta.min_edge, 0.0))
    edge = p_hat_yes - m

    if edge >= min_edge:
        side: Side = "YES"
        price = m
        p_win = p_hat_yes
    elif edge <= -min_edge:
        side = "NO"
        price = clip01(1.0 - m)
        p_win = clip01(1.0 - p_hat_yes)
    else:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": p_hat_yes, "reason": "edge_too_small"}

    # Time-based per-market cap
    f_cap = float(max(theta.f_cap, 0.0))
    gamma = float(max(theta.gamma_cap, 0.0))
    f_cap_time = f_cap * math.exp(-gamma * T)

    # Maximum fraction allowed by cash + global lock budget + per-market cap
    f_max_cash = spendable_cash / W
    f_max_lock = remaining_locked_budget / W
    f_max = min(f_max_cash, f_max_lock, f_cap_time)
    if f_max <= 0.0:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": p_hat_yes, "reason": "f_max<=0"}

    # Liquidity shadow price penalized Kelly optimization (1D concave optimization)
    eta = float(max(theta.eta, 0.0))
    f_star = optimal_fraction_with_liquidity_penalty(p_win=p_win, price=price, T_days=T, eta=eta, f_max=f_max)

    # Fractional Kelly scaling (extra robustness)
    alpha = float(min(max(theta.alpha, 0.0), 1.0))
    f = alpha * f_star

    stake = f * W
    stake = min(stake, spendable_cash, remaining_locked_budget)
    if stake <= 0.0:
        return {"stake": 0.0, "side": "NONE", "shares": 0.0, "price": 0.0, "p_hat_yes": p_hat_yes, "reason": "stake<=0_after_constraints"}

    shares = stake / price
    return {
        "stake": float(stake),
        "side": side,
        "shares": float(shares),
        "price": float(price),
        "p_hat_yes": float(p_hat_yes),
        "reason": "ok",
    }


def sample_settlement_days(rng: np.random.Generator, cfg: EnvConfig) -> int:
    # Geometric distribution biased to short maturities, truncated.
    T = int(rng.geometric(p=cfg.geom_p))
    return int(min(max(T, 1), cfg.max_settle_days))


def generate_market(rng: np.random.Generator, market_id: int, cfg: EnvConfig) -> Market:
    T = sample_settlement_days(rng, cfg)

    if cfg.settle_from_price:
        # As requested: settle with probability = market price
        price_yes = float(rng.uniform(0.05, 0.95))
        true_p_yes = price_yes
        p_pred_yes = clip01(price_yes + rng.normal(0.0, cfg.sigma_pred_around_price))
    else:
        # More realistic: true probability exists, market price is noisy, we have some skill
        true_p_yes = float(rng.beta(cfg.beta_a, cfg.beta_b))
        price_yes = clip01(true_p_yes + rng.normal(0.0, cfg.sigma_market))
        p_pred_yes = clip01(true_p_yes + rng.normal(0.0, cfg.sigma_pred))

    return Market(
        market_id=market_id,
        price_yes=clip01(price_yes),
        p_pred_yes=clip01(p_pred_yes),
        true_p_yes=clip01(true_p_yes),
        days_to_settle=int(T),
    )


def settle_position(rng: np.random.Generator, pos: Position) -> float:
    """
    Return payoff amount (cash inflow) at settlement time.
    Stake was already paid when opening.
    """
    outcome_yes = (rng.random() < pos.true_p_yes)
    win = (outcome_yes and pos.side == "YES") or ((not outcome_yes) and pos.side == "NO")
    return pos.shares if win else 0.0


def simulate(
    theta: Theta,
    cfg: EnvConfig,
    initial_wealth: float = 1000.0,
    k: float = 0.2,
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)

    cash = float(initial_wealth)
    positions: List[Position] = []
    equity = np.zeros(cfg.horizon_days + 1, dtype=float)
    equity[0] = initial_wealth

    market_id = 0

    for day in range(1, cfg.horizon_days + 1):
        # 1) countdown + settle matured
        matured: List[Position] = []
        for pos in positions:
            pos.days_left -= 1
            if pos.days_left <= 0:
                matured.append(pos)

        if matured:
            # remove matured positions
            positions = [p for p in positions if p.days_left > 0]
            # settle
            for pos in matured:
                cash += settle_position(rng, pos)

        # 2) new markets arrive
        n_new = int(rng.poisson(cfg.markets_per_day))
        for _ in range(n_new):
            market_id += 1
            mkt = generate_market(rng, market_id, cfg)

            W = cash + sum(p.stake for p in positions)
            decision = allocate(mkt, positions, total_wealth=W, k=k, theta=theta)

            stake = float(decision["stake"])
            side = decision["side"]

            if stake > 0.0 and (side == "YES" or side == "NO"):
                price = float(decision["price"])
                shares = stake / price
                cash -= stake

                positions.append(Position(
                    market_id=mkt.market_id,
                    side=side,
                    entry_price=price,
                    stake=stake,
                    shares=shares,
                    days_left=mkt.days_to_settle,
                    true_p_yes=mkt.true_p_yes,
                ))

        # 3) record equity (NAV at cost for open positions)
        W = cash + sum(p.stake for p in positions)
        equity[day] = W

    t = np.arange(cfg.horizon_days + 1)
    return t, equity


def growth_rate_log(equity: np.ndarray) -> float:
    # average per-day log growth
    W0 = float(equity[0])
    WT = float(equity[-1])
    if W0 <= 0 or WT <= 0:
        return -1e9
    return math.log(WT / W0) / max(1, len(equity) - 1)


def theta_from_z(z: np.ndarray) -> Theta:
    """
    Map unconstrained vector z -> constrained theta.
    Adjust these ranges as you like.
    """
    z = np.asarray(z, dtype=float).reshape(-1)
    alpha = sigmoid(z[0])                    # 0..1
    shrink = sigmoid(z[1])                   # 0..1
    eta = softplus(z[2]) * 0.01              # ~0.. (typical 0~0.01)
    f_cap = sigmoid(z[3]) * 0.25             # 0..0.25
    gamma_cap = softplus(z[4]) * 0.05        # 0.. (time cap decay)
    min_edge = sigmoid(z[5]) * 0.05          # 0..0.05

    return Theta(
        alpha=float(alpha),
        shrink=float(shrink),
        eta=float(eta),
        f_cap=float(f_cap),
        gamma_cap=float(gamma_cap),
        min_edge=float(min_edge),
    )


def optimize_theta_cem(
    cfg: EnvConfig,
    initial_wealth: float,
    k: float,
    seeds: List[int],
    iters: int = 15,
    pop_size: int = 60,
    elite_frac: float = 0.2,
    init_sigma: float = 1.0,
    seed: int = 123,
) -> Tuple[Theta, Dict[str, List[float]]]:
    """
    Cross-Entropy Method (evolutionary search) to maximize average per-day log growth.

    Returns:
      best_theta, history
    """
    rng = np.random.default_rng(seed)
    dim = 6
    mu = np.zeros(dim, dtype=float)
    sigma = np.ones(dim, dtype=float) * float(init_sigma)

    n_elite = max(2, int(pop_size * elite_frac))

    best_theta = theta_from_z(mu)
    best_score = -1e18

    hist = {"best_score": [], "mean_score": []}

    # Common random numbers: use fixed seeds list to reduce noise across candidates
    for it in range(iters):
        Z = rng.normal(loc=mu, scale=sigma, size=(pop_size, dim))

        scores = np.zeros(pop_size, dtype=float)
        for i in range(pop_size):
            th = theta_from_z(Z[i])
            vals = []
            for sd in seeds:
                _, eq = simulate(th, cfg, initial_wealth=initial_wealth, k=k, seed=sd)
                vals.append(growth_rate_log(eq))
            scores[i] = float(np.mean(vals))

        mean_score = float(np.mean(scores))
        elite_idx = np.argsort(scores)[-n_elite:]
        elites = Z[elite_idx]
        elite_scores = scores[elite_idx]

        # Update distribution
        mu = np.mean(elites, axis=0)
        sigma = np.std(elites, axis=0) + 1e-6

        # Track best
        elite_best_i = int(elite_idx[np.argmax(elite_scores)])
        if scores[elite_best_i] > best_score:
            best_score = float(scores[elite_best_i])
            best_theta = theta_from_z(Z[elite_best_i])

        hist["best_score"].append(best_score)
        hist["mean_score"].append(mean_score)

        print(f"[CEM] iter={it:02d} mean={mean_score:.6f} best={best_score:.6f} theta={best_theta}")

    return best_theta, hist


def plot_profit_curve(t: np.ndarray, equity: np.ndarray, title: str = "Profit Curve") -> None:
    profit = equity - equity[0]
    plt.figure()
    plt.plot(t, profit)
    plt.xlabel("Day")
    plt.ylabel("Profit")
    plt.title(title)
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    # --- 1) Environment ---
    cfg = EnvConfig(
        horizon_days=365,
        markets_per_day=3.0,
        max_settle_days=60,
        settle_from_price=False,  # <= 按你的要求：用 market price 作为结算概率
        sigma_pred_around_price=0.06,
        # If you want an "alpha" environment, set settle_from_price=False and tune noise:
        # settle_from_price=False, sigma_market=0.06, sigma_pred=0.03
    )

    initial_wealth = 1000.0
    k = 0.25  # keep 25% liquid cash always

    # --- 2) Optimize theta by Monte Carlo (evolutionary search) ---
    seeds = list(range(10))  # increase for more stable optimization
    best_theta, hist = optimize_theta_cem(
        cfg=cfg,
        initial_wealth=initial_wealth,
        k=k,
        seeds=seeds,
        iters=12,
        pop_size=50,
        elite_frac=0.2,
        init_sigma=1.0,
        seed=2025,
    )

    # --- 3) Run one simulation path and plot profit curve ---
    t, equity = simulate(best_theta, cfg, initial_wealth=initial_wealth, k=k, seed=999)
    print("Best theta:", best_theta)
    print("Final wealth:", equity[-1])

    plot_profit_curve(t, equity, title="Polymarket Multi-Kelly Profit Curve")
