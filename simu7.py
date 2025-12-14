# -*- coding: utf-8 -*-
"""
交互式（带优雅输出）的 Polymarket 多期 Kelly+水位分配模拟器

说明：
- 尝试使用 ipywidgets 提供交互控制；若环境不支持，会自动退化为直接运行默认参数并展示结果。
- 图表：严格使用 matplotlib、每个 figure 只放一张图、未显式设置颜色。
- 表格：通过 caas_jupyter_tools.display_dataframe_to_user 提供交互式 DataFrame 视图（可排序/滚动）。
- 生成 CSV 到 /mnt/data，便于下载或后续分析。
"""
import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 供 UI 使用
from IPython.display import display, clear_output
try:
    import ipywidgets as widgets
    HAS_WIDGETS = True
except Exception:
    HAS_WIDGETS = False

# DataFrame 交互显示
from caas_jupyter_tools import display_dataframe_to_user

# ------------------ 公共工具 ------------------
RNG = np.random.default_rng(7)

def clip01(x, eps=1e-9):
    return float(min(1-eps, max(eps, x)))

@dataclass
class Market:
    id: int
    m: float       # yes price
    p_yes: float   # subjective yes probability
    d: int         # settle day (index)
    p_no: Optional[float] = None  # (可选)主观 no 概率

def choose_side(m: float, p_yes: float, p_no: Optional[float], weight: float):
    m = clip01(m)
    p_yes = clip01(p_yes)
    if p_no is None:
        p_no = 1.0 - p_yes
    else:
        p_no = clip01(p_no)
    deriv_yes = weight * (p_yes / m - 1.0)
    deriv_no  = weight * (p_no  / (1.0 - m) - 1.0)
    if max(deriv_yes, deriv_no) <= 0.0:
        return None
    if deriv_yes >= deriv_no:
        side = "YES"; price = m; p = p_yes; b = 1.0/m - 1.0
    else:
        side = "NO";  price = 1.0 - m; p = p_no; b = 1.0/(1.0-m) - 1.0
    return {"side": side, "price": price, "p": p, "b": b, "deriv0": max(deriv_yes, deriv_no)}

def f_from_mu(p: float, b: float, w: float, mu: float, f_cap: float = 0.95, iters: int = 40) -> float:
    p = clip01(p); b = max(1e-9, b); w = max(1e-12, w)
    f_cap = min(0.999999, max(1e-6, f_cap))
    deriv0 = w * (p * b - (1.0 - p))
    if deriv0 <= mu + 1e-12:
        return 0.0
    f_kelly = (p * b - (1.0 - p)) / b
    f_kelly = max(0.0, min(f_cap, f_kelly))
    lo, hi = 0.0, f_kelly
    for _ in range(iters):
        mid = 0.5*(lo+hi)
        val = w*(p*b/(1.0+mid*b) - (1.0-p)/(1.0-mid))
        if val > mu:
            lo = mid
        else:
            hi = mid
    return hi

def allocate(markets_today: List[Market], wealth: float, locked_value_now: float,
             now_day: int, k: float, theta: Dict) -> List[Dict]:
    lam = float(theta.get("lambda_time", 0.0))
    c_frac = float(theta.get("c_fraction", 1.0))
    f_cap = float(theta.get("f_cap", 0.95))
    wealth = max(1e-9, wealth)
    locked_frac = locked_value_now / wealth
    k_rem = max(0.0, k - locked_frac)
    if k_rem <= 1e-12:
        return []
    # 候选
    cands = []
    for mk in markets_today:
        T = max(1, mk.d - now_day)
        w = math.exp(-lam * T)
        sd = choose_side(mk.m, mk.p_yes, mk.p_no, w)
        if sd is None:
            continue
        cands.append({
            "id": mk.id, "w": w, "p": clip01(sd["p"]), "b": max(1e-9, sd["b"]),
            "price": sd["price"], "side": sd["side"], "settle_day": mk.d, "T": T
        })
    if not cands:
        return []
    f_k = np.array([(c["p"]*c["b"] - (1.0-c["p"])) / c["b"] for c in cands], dtype=float)
    f_k = np.clip(f_k, 0.0, f_cap)
    if float(f_k.sum()) <= k_rem + 1e-12:
        f_use = f_k * max(1e-9, min(1.0, c_frac))
    else:
        def sum_f(mu: float) -> float:
            return sum(f_from_mu(c["p"], c["b"], c["w"], mu, f_cap=f_cap) for c in cands)
        lo, hi = 0.0, 1.0
        while sum_f(hi) > k_rem:
            hi *= 2.0
            if hi > 1e6: break
        for _ in range(40):
            mid = 0.5*(lo+hi)
            if sum_f(mid) > k_rem: lo = mid
            else: hi = mid
        mu_star = hi
        f_use = np.array([f_from_mu(c["p"], c["b"], c["w"], mu_star, f_cap=f_cap) for c in cands], dtype=float)
        f_use *= max(1e-9, min(1.0, c_frac))

    allocs = []
    for c, f in zip(cands, f_use):
        if f <= 1e-9: continue
        invest = f*wealth
        shares = invest / c["price"]
        allocs.append({
            "id": c["id"], "side": c["side"], "price": c["price"], "p": c["p"], "b": c["b"],
            "f": float(f), "invest": float(invest), "shares": float(shares),
            "settle_day": c["settle_day"], "T": c["T"], "w": c["w"]
        })
    return allocs

def gen_markets_for_day(day: int, base_id: int, n_new: int, min_T=3, max_T=45,
                        p_low=0.05, p_high=0.95, misprice_sigma=0.06,
                        allow_incoherent_q=False) -> Tuple[List[Market], int]:
    mkts = []
    for i in range(n_new):
        p = float(RNG.uniform(p_low, p_high))
        m = float(np.clip(RNG.normal(loc=p, scale=misprice_sigma), 0.01, 0.99))
        T = int(RNG.integers(min_T, max_T + 1))
        q = None
        if allow_incoherent_q:
            q = float(np.clip((1.0 - p) + RNG.normal(0.0, 0.05), 0.0, 1.0))
        mkts.append(Market(id=base_id + i, m=m, p_yes=p, d=day + T, p_no=q))
    return mkts, base_id + n_new

def realize_outcome_from_ptrue(p_subjective: float) -> int:
    p_true = float(np.clip(p_subjective * (1.0 + float(RNG.uniform(-0.5, 0.5))), 0.0, 1.0))
    return int(RNG.uniform() < p_true)

# ------------------ 带日志的完整仿真 ------------------
def simulate_verbose(
    T_days: int, M0: float, k: float, theta: Dict,
    mean_new_markets: float = 6.0, misprice_sigma: float = 0.06,
    allow_incoherent_q: bool = False, seed: Optional[int] = None
):
    if seed is not None:
        np.random.seed(seed); random.seed(seed)
        global RNG; RNG = np.random.default_rng(seed)

    day = 0
    cash = float(M0)
    positions = []  # 未结算
    next_id = 0

    wealth_curve = []
    daily_rows = []
    decision_rows = []
    settle_rows = []

    for day in range(T_days):
        # 结算
        realized_pnl_today = 0.0
        kept = []
        for pos in positions:
            if pos["settle_day"] <= day:
                outcome_yes = realize_outcome_from_ptrue(pos["p_used"])
                if pos["side"] == "YES":
                    payoff = pos["shares"] * (1.0 if outcome_yes == 1 else 0.0)
                    is_win = int(outcome_yes == 1)
                else:
                    payoff = pos["shares"] * (1.0 if outcome_yes == 0 else 0.0)
                    is_win = int(outcome_yes == 0)
                cash += payoff
                pnl = payoff - pos["invest"]
                realized_pnl_today += pnl
                settle_rows.append({
                    "day_settle": day, "id": pos["id"], "side": pos["side"],
                    "invest": pos["invest"], "payoff": payoff, "pnl": pnl, "is_win": is_win,
                    "day_enter": pos["day_enter"], "T": pos["T"]
                })
            else:
                kept.append(pos)
        positions = kept

        locked_value = sum(p["invest"] for p in positions)
        wealth_start = cash + locked_value

        # 新市场
        n_new = max(0, int(RNG.poisson(mean_new_markets)))
        mkts, next_id = gen_markets_for_day(day, next_id, n_new, misprice_sigma=misprice_sigma,
                                            allow_incoherent_q=allow_incoherent_q)

        # 分配
        allocs = allocate(
            mkts, wealth=wealth_start, locked_value_now=locked_value,
            now_day=day, k=k, theta=theta
        )

        invested_today = 0.0
        for al in allocs:
            if al["invest"] <= 0.0 or al["invest"] > cash: 
                continue
            cash -= al["invest"]; invested_today += al["invest"]
            positions.append({
                "id": al["id"], "side": al["side"], "price": al["price"], "shares": al["shares"],
                "invest": al["invest"], "settle_day": al["settle_day"], "p_used": al["p"],
                "day_enter": day, "T": al["T"]
            })
            decision_rows.append({
                "day": day, "id": al["id"], "side": al["side"], "price": al["price"],
                "p_used": al["p"], "invest": al["invest"], "shares": al["shares"],
                "settle_day": al["settle_day"], "T": al["T"], "f": al["f"], "w": al["w"]
            })

        locked_value = sum(p["invest"] for p in positions)
        wealth_end = cash + locked_value
        wealth_curve.append(wealth_end)

        daily_rows.append({
            "day": day, "wealth_start": wealth_start, "wealth_end": wealth_end,
            "daily_profit": wealth_end - wealth_start,
            "invested_today": invested_today,
            "realized_pnl_today": realized_pnl_today,
            "n_new_markets": n_new,
            "open_positions": len(positions),
            "cash_end": cash,
            "locked_end": locked_value
        })

    # 生成 DataFrame 与指标
    daily_df = pd.DataFrame(daily_rows)
    if len(daily_df) > 0:
        daily_df["equity_peak"] = daily_df["wealth_end"].cummax()
        daily_df["drawdown"] = daily_df["wealth_end"]/daily_df["equity_peak"] - 1.0

    decisions_df = pd.DataFrame(decision_rows)
    settled_df = pd.DataFrame(settle_rows)

    final_wealth = wealth_curve[-1] if wealth_curve else M0
    return wealth_curve, final_wealth, daily_df, decisions_df, settled_df

def summarize_metrics(daily_df: pd.DataFrame, settled_df: pd.DataFrame, M0: float):
    metrics = {}
    if len(daily_df) > 0:
        W0 = M0
        WT = float(daily_df["wealth_end"].iloc[-1])
        T = len(daily_df)
        metrics["final_wealth"] = WT
        metrics["log_growth_per_day"] = math.log(max(1e-9, WT/W0))/T
        metrics["max_drawdown"] = float(daily_df["drawdown"].min()) if "drawdown" in daily_df else float("nan")
        metrics["avg_daily_profit"] = float(daily_df["daily_profit"].mean())
        metrics["median_daily_profit"] = float(daily_df["daily_profit"].median())
    if len(settled_df) > 0:
        metrics["bets_settled"] = int(len(settled_df))
        metrics["hit_rate"] = float(settled_df["is_win"].mean())
        metrics["avg_roi_per_bet"] = float((settled_df["payoff"].sum() - settled_df["invest"].sum())/max(1e-9, settled_df["invest"].sum()))
        metrics["avg_T_days"] = float(settled_df["T"].mean())
    return metrics

# ------------------ 绘图 ------------------
def plot_equity(wealth_curve):
    plt.figure(figsize=(9,4.5))
    plt.plot(range(len(wealth_curve)), wealth_curve)
    plt.title("Equity Curve")
    plt.xlabel("Day")
    plt.ylabel("Wealth (equity)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def plot_daily_profit(daily_df: pd.DataFrame):
    if len(daily_df)==0: return
    plt.figure(figsize=(9,4.0))
    plt.bar(daily_df["day"].values, daily_df["daily_profit"].values)
    plt.title("Daily Profit")
    plt.xlabel("Day")
    plt.ylabel("Profit")
    plt.tight_layout()
    plt.show()

# ------------------ 仪表盘（若支持小部件） ------------------
def run_and_show(M0, k, T_days, lambda_time, c_fraction, mean_new_markets, misprice_sigma, seed):
    theta = {"lambda_time": float(lambda_time), "c_fraction": float(c_fraction), "f_cap": 0.95}
    wealth_curve, Wf, daily_df, decisions_df, settled_df = simulate_verbose(
        T_days=T_days, M0=M0, k=k, theta=theta,
        mean_new_markets=mean_new_markets, misprice_sigma=misprice_sigma, seed=seed
    )
    metrics = summarize_metrics(daily_df, settled_df, M0)
    # 友好摘要
    print("=== Strategy Parameters ===")
    print(theta)
    print("=== Key Metrics ===")
    for k_, v_ in metrics.items():
        if isinstance(v_, float):
            print(f"{k_:>22s}: {v_:,.6g}")
        else:
            print(f"{k_:>22s}: {v_}")
    # 图表
    plot_equity(wealth_curve)
    plot_daily_profit(daily_df)
    # 交互表：每日摘要 & 决策清单
    try:
        display_dataframe_to_user("Daily Summary", daily_df)
        display_dataframe_to_user("Decisions (Allocations)", decisions_df)
        if len(settled_df)>0:
            display_dataframe_to_user("Settlements", settled_df)
    except Exception as e:
        print("DataFrame interactive viewer not available:", e)
        print("Daily head:\n", daily_df.head())
        print("Decisions head:\n", decisions_df.head())
    # 导出 CSV
    daily_csv = "/mnt/data/daily_summary.csv"
    dec_csv = "/mnt/data/decisions_log.csv"
    stl_csv = "/mnt/data/settlements.csv"
    daily_df.to_csv(daily_csv, index=False)
    decisions_df.to_csv(dec_csv, index=False)
    settled_df.to_csv(stl_csv, index=False)
    print(f"[Download Daily Summary]({daily_csv})")
    print(f"[Download Decisions Log]({dec_csv})")
    print(f"[Download Settlements]({stl_csv})")

def launch_dashboard():
    default = dict(
        M0=10000.0, k=0.6, T_days=180,
        lambda_time=0.05, c_fraction=0.4,
        mean_new_markets=6.0, misprice_sigma=0.06, seed=1234
    )
    if HAS_WIDGETS:
        # 控件
        M0 = widgets.FloatLogSlider(description="Initial Wealth", base=10, min=3, max=6, step=0.1, value=default["M0"])
        k  = widgets.FloatSlider(description="Lock-up k", min=0.1, max=0.95, step=0.01, value=default["k"])
        T_days = widgets.IntSlider(description="Days", min=60, max=365, step=5, value=default["T_days"])
        lambda_time = widgets.FloatSlider(description="λ (time decay)", min=0.0, max=0.1, step=0.002, value=default["lambda_time"])
        c_fraction = widgets.FloatSlider(description="Fractional Kelly c", min=0.1, max=1.0, step=0.02, value=default["c_fraction"])
        mean_new_markets = widgets.FloatSlider(description="New mkts/day", min=1.0, max=20.0, step=0.5, value=default["mean_new_markets"])
        misprice_sigma = widgets.FloatSlider(description="Misprice σ", min=0.01, max=0.20, step=0.005, value=default["misprice_sigma"])
        seed = widgets.IntText(description="Seed", value=default["seed"])
        btn = widgets.Button(description="Run Simulation", button_style="primary")
        out = widgets.Output()

        def _click(_):
            with out:
                clear_output(wait=True)
                run_and_show(M0.value, k.value, T_days.value, lambda_time.value, c_fraction.value,
                             mean_new_markets.value, misprice_sigma.value, int(seed.value))

        btn.on_click(_click)
        ui = widgets.VBox([
            widgets.HTML("<h3>Polymarket Kelly Water-filling Simulator</h3>"),
            widgets.HBox([M0, k, T_days]),
            widgets.HBox([lambda_time, c_fraction]),
            widgets.HBox([mean_new_markets, misprice_sigma, seed]),
            btn, widgets.HTML("<hr>"), out
        ])
        display(ui)
        # 初次运行
        _click(None)
    else:
        print("ipywidgets 不可用，使用默认参数直接运行。")
        run_and_show(**default)

# 启动
launch_dashboard()
