from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math
import numpy as np

# ---------- helpers ----------
def sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)

def logit(p: float, eps: float = 1e-6) -> float:
    p = min(max(float(p), eps), 1.0 - eps)
    return math.log(p / (1.0 - p))

def zscore_last(arr: np.ndarray, window: int) -> float:
    if arr.size < 2:
        return 0.0
    w = max(2, min(int(window), arr.size))
    tail = arr[-w:]
    m = float(np.mean(tail))
    s = float(np.std(tail, ddof=0))
    if s < 1e-12:
        return 0.0
    return float((arr[-1] - m) / s)

def compute_rsi(series: np.ndarray, period: int = 14) -> float:
    if series.size < period + 1:
        return float("nan")
    window = series[-(period + 1):]
    deltas = np.diff(window)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss < 1e-12:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, float(v)) for v in w.values())
    if s <= 1e-12:
        return {k: 0.0 for k in w}
    return {k: float(v) / s for k, v in w.items()}

# ---------- params ----------
@dataclass
class Params:
    fast_window: int
    slow_window: int
    accel_k: int
    rsi_period: int
    threshold: float
    hard_exit_price: float
    min_profit_abs: float
    min_profit_mult_entry: float
    dd_trigger: float
    weights: Dict[str, float]

def get_params(tag: str, entry_price: float) -> Params:
    tag = (tag or "").lower().strip()
    if tag == "short-term":
        return Params(10, 40, 3, 9, 0.72, 0.97, 0.03, 0.0, 0.015,
                      {"over":0.14,"vol":0.20,"exh":0.18,"rsi":0.08,"para":0.12,
                       "book":0.12,"spread":0.06,"sat":0.04,"time":0.02,"dd":0.04})
    if tag == "long-term":
        return Params(20, 120, 5, 14, 0.78, 0.98, 0.05, 0.0, 0.030,
                      {"over":0.18,"vol":0.08,"exh":0.10,"rsi":0.08,"para":0.05,
                       "book":0.08,"spread":0.04,"sat":0.22,"time":0.12,"dd":0.05})
    if tag == "speculation":
        return Params(15, 60, 4, 12, 0.70, 0.97, 0.06, 2.0, 0.025,
                      {"over":0.16,"vol":0.18,"exh":0.16,"rsi":0.08,"para":0.14,
                       "book":0.08,"spread":0.04,"sat":0.08,"time":0.04,"dd":0.04})
    if tag == "consensus":
        return Params(12, 60, 3, 14, 0.65, 0.96, 0.02, 0.0, 0.015,
                      {"over":0.10,"vol":0.08,"exh":0.14,"rsi":0.05,"para":0.05,
                       "book":0.12,"spread":0.06,"sat":0.30,"time":0.06,"dd":0.04})
    # uncertain default
    return Params(12, 50, 3, 10, 0.68, 0.97, 0.04, 0.0, 0.020,
                  {"over":0.10,"vol":0.14,"exh":0.14,"rsi":0.06,"para":0.08,
                   "book":0.16,"spread":0.12,"sat":0.10,"time":0.06,"dd":0.04})

# ---------- factor & decision ----------
def compute_factors(
    prices: np.ndarray,
    volumes: np.ndarray,
    bid_depth: Optional[np.ndarray],
    ask_depth: Optional[np.ndarray],
    spreads: Optional[np.ndarray],
    entry_index: int,
    entry_price: float,
    tau: Optional[float],
    params: Params
) -> Tuple[Dict[str, float], Dict[str, float]]:
    eps = 1e-9
    entry_index = max(0, min(int(entry_index), prices.size - 1))

    p = prices[entry_index:]
    v = volumes[entry_index:]

    # allow missing orderbook/spread
    if bid_depth is None: bid_depth = np.full_like(prices, np.nan, dtype=float)
    if ask_depth is None: ask_depth = np.full_like(prices, np.nan, dtype=float)
    if spreads is None:   spreads   = np.full_like(prices, np.nan, dtype=float)

    bd = bid_depth[entry_index:]
    ad = ask_depth[entry_index:]
    sp = spreads[entry_index:]

    x = np.array([logit(pi) for pi in p], dtype=float)

    fw = max(3, params.fast_window)
    sw = max(fw + 1, params.slow_window)
    k  = max(2, params.accel_k)

    z_over = zscore_last(x, min(sw, x.size))
    f_over = sigmoid(z_over)

    logv = np.log(np.maximum(v, 0.0) + 1.0)
    z_vol = zscore_last(logv, min(sw, logv.size))
    f_vol = sigmoid(z_vol)

    if x.size >= 2 * k + 1:
        slope_fast = (x[-1] - x[-1 - k]) / k
        slope_prev = (x[-1 - k] - x[-1 - 2*k]) / k
        accel = slope_fast - slope_prev
    else:
        slope_fast, accel = 0.0, 0.0

    std_fast = float(np.std(x[-min(fw, x.size):], ddof=0))
    std_fast = max(std_fast, 1e-6)

    slope_z = slope_fast / std_fast
    accel_z = accel / std_fast
    exh_z = (-accel_z) if slope_z > 0 else (-slope_z)
    f_exh = sigmoid(exh_z)

    rsi = compute_rsi(x, period=max(5, params.rsi_period))
    f_rsi = 0.5 if math.isnan(rsi) else sigmoid((rsi - 70.0) / 5.0)

    if x.size >= sw + 1:
        slope_slow = (x[-1] - x[-1 - sw]) / sw
    else:
        look = min(x.size - 1, max(fw, 5))
        slope_slow = (x[-1] - x[-1 - look]) / max(1, look)
    ratio = abs(slope_fast) / (abs(slope_slow) + 1e-9)
    f_para = sigmoid((ratio - 2.0) / 0.5)

    last_bd = float(bd[-1]) if bd.size and not math.isnan(float(bd[-1])) else float("nan")
    last_ad = float(ad[-1]) if ad.size and not math.isnan(float(ad[-1])) else float("nan")
    if math.isnan(last_bd) or math.isnan(last_ad) or (last_bd + last_ad) < eps:
        obi = float("nan")
        f_book = 0.5
    else:
        obi = (last_bd - last_ad) / (last_bd + last_ad + eps)
        f_book = sigmoid((-obi) / 0.3)

    if sp.size and not math.isnan(float(sp[-1])):
        z_spread = zscore_last(sp.astype(float), min(sw, sp.size))
        f_spread = sigmoid(z_spread)
        last_sp = float(sp[-1])
    else:
        z_spread, f_spread, last_sp = 0.0, 0.5, float("nan")

    last_p = float(p[-1])
    profit = last_p - float(entry_price)
    remaining = max(1.0 - last_p, 0.0)
    sat_raw = profit / (remaining + 1e-6)
    f_sat = sigmoid(sat_raw - 1.0)

    if tau is None or not (float(tau) > 0):
        elapsed_ratio = float("nan")
        f_time = 0.5
    else:
        elapsed = float(p.size - 1)
        elapsed_ratio = elapsed / float(tau)
        f_time = sigmoid((elapsed_ratio - 0.6) / 0.1)

    recent = p[-min(fw, p.size):]
    recent_high = float(np.nanmax(recent))
    dd = (recent_high - last_p) / max(recent_high, 1e-6)
    f_dd = sigmoid((dd - params.dd_trigger) / max(params.dd_trigger, 1e-6))

    factors = {"over":f_over,"vol":f_vol,"exh":f_exh,"rsi":f_rsi,"para":f_para,
               "book":f_book,"spread":f_spread,"sat":f_sat,"time":f_time,"dd":f_dd}

    raw = {"profit":profit,"remaining_upside":remaining,"sat_raw":sat_raw,
           "obi":obi,"spread":last_sp,"rsi":rsi,"parabolic_ratio":ratio,
           "z_over":z_over,"z_vol":z_vol,"z_spread":z_spread,"dd":dd,"elapsed_ratio":elapsed_ratio}
    return factors, raw

def compute_score(factors: Dict[str, float], params: Params) -> float:
    w = normalize_weights(params.weights)
    s = sum(w[k] * float(factors.get(k, 0.5)) for k in w)
    return max(0.0, min(1.0, s))

def decide_hold_or_sell(
    tag: str,
    entry_price: float,
    entry_index: int,
    prices: List[float],
    volumes: List[float],
    bid_depth: Optional[List[float]] = None,
    ask_depth: Optional[List[float]] = None,
    spreads: Optional[List[float]] = None,
    # 可选：把当前 tick 直接传进来（会自动 append）
    current_price: Optional[float] = None,
    current_volume: Optional[float] = None,
    current_bid_depth: Optional[float] = None,
    current_ask_depth: Optional[float] = None,
    current_spread: Optional[float] = None,
    tau: Optional[float] = None,
) -> Dict:
    """
    Return dict:
      - action: "HOLD" or "SELL"
      - score: 0..1
      - threshold
      - suggested_sell_fraction: 0..1
      - reason
      - factors: {name:0..1}
      - raw: useful raw diagnostics
    """
    # copy & append tick
    p = list(prices)
    v = list(volumes)
    bd = list(bid_depth) if bid_depth is not None else None
    ad = list(ask_depth) if ask_depth is not None else None
    sp = list(spreads) if spreads is not None else None

    if current_price is not None and current_volume is not None:
        p.append(float(current_price))
        v.append(max(0.0, float(current_volume)))
        if bd is not None: bd.append(float("nan") if current_bid_depth is None else float(current_bid_depth))
        if ad is not None: ad.append(float("nan") if current_ask_depth is None else float(current_ask_depth))
        if sp is not None: sp.append(float("nan") if current_spread is None else float(current_spread))

    if len(p) < 3 or len(v) < 3:
        return {"action":"HOLD","score":0.0,"threshold":None,"suggested_sell_fraction":0.0,
                "reason":"数据不足（至少 3 个点）","factors":{}, "raw":{}}

    prices_np = np.array(p, dtype=float)
    vols_np   = np.array(v, dtype=float)
    bd_np     = np.array(bd, dtype=float) if bd is not None else None
    ad_np     = np.array(ad, dtype=float) if ad is not None else None
    sp_np     = np.array(sp, dtype=float) if sp is not None else None

    params = get_params(tag, entry_price)
    factors, raw = compute_factors(prices_np, vols_np, bd_np, ad_np, sp_np,
                                   entry_index=entry_index, entry_price=entry_price,
                                   tau=tau, params=params)
    score = compute_score(factors, params)

    last_p = float(prices_np[-1])
    profit = float(raw.get("profit", last_p - entry_price))

    # 只止盈
    if profit <= 0:
        return {"action":"HOLD","score":score,"threshold":params.threshold,"suggested_sell_fraction":0.0,
                "reason":f"未盈利（profit={profit:.4f}），只止盈→HOLD",
                "factors":factors,"raw":raw}

    # 启动门槛（避免小波动频繁出）
    min_profit = max(params.min_profit_abs, entry_price * params.min_profit_mult_entry)
    if profit < min_profit:
        return {"action":"HOLD","score":score,"threshold":params.threshold,"suggested_sell_fraction":0.0,
                "reason":f"已盈利但未达到止盈启动门槛 profit={profit:.4f} < {min_profit:.4f} → HOLD",
                "factors":factors,"raw":raw}

    # 硬退出：接近 1
    if last_p >= params.hard_exit_price:
        return {"action":"SELL","score":score,"threshold":params.threshold,"suggested_sell_fraction":1.0,
                "reason":f"价格接近上限 p={last_p:.4f} ≥ {params.hard_exit_price:.2f}，收益饱和→SELL",
                "factors":factors,"raw":raw}

    # 顶峰脆弱区：超涨+放量+疲劳+盘口/流动性转弱
    fw = max(3, params.fast_window)
    recent_high = float(np.nanmax(prices_np[-min(fw, prices_np.size):]))
    near_high = (recent_high - last_p) <= 0.002  # 很接近局部高点即可
    peak_candidate = (
        near_high
        and factors["over"] > 0.80
        and factors["vol"] > 0.75
        and factors["exh"] > 0.55
        and (factors["book"] > 0.60 or factors["spread"] > 0.70)
    )
    if peak_candidate:
        frac = max(0.3, min(1.0, (score - params.threshold) / max(1e-6, (1.0 - params.threshold))))
        frac = 1.0 if score >= params.threshold else max(0.5, frac)  # 顶峰区更激进
        return {"action":"SELL","score":score,"threshold":params.threshold,"suggested_sell_fraction":frac,
                "reason":"顶峰脆弱区：超涨+放量+疲劳+盘口/点差转弱 → SELL",
                "factors":factors,"raw":raw}

    # 评分触发
    if score >= params.threshold:
        frac = max(0.3, min(1.0, (score - params.threshold) / max(1e-6, (1.0 - params.threshold))))
        return {"action":"SELL","score":score,"threshold":params.threshold,"suggested_sell_fraction":frac,
                "reason":f"Score={score:.3f} ≥ {params.threshold:.2f} → SELL",
                "factors":factors,"raw":raw}

    return {"action":"HOLD","score":score,"threshold":params.threshold,"suggested_sell_fraction":0.0,
            "reason":f"Score={score:.3f} < {params.threshold:.2f} 且无顶峰脆弱信号 → HOLD",
            "factors":factors,"raw":raw}
