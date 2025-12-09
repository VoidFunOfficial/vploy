# -*- coding: utf-8 -*-
"""
仓位管理模块 - 基于Kelly公式 + 水位法 + 时间贴现的多市场自动仓位分配

核心算法来自 pm_2.py，集成 purse 模块进行资金管理。

主要功能:
- 使用水位法(water-filling)进行多市场资金分配
- 支持时间贴现(time discount)，优先分配短期市场
- 集成purse模块获取实时资金状态
- 完整的VLogger日志记录
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger

# 导入 purse 模块
from ..purse import get_purse

# 导入 Polymarket API 数据结构
try:
    from ..polymarket_api.gamma_markets import Market as GammaMarket
    GAMMA_MARKET_AVAILABLE = True
except ImportError:
    GAMMA_MARKET_AVAILABLE = False
    vlogger.warn(
        "POSITION.IMPORT.GAMMA_UNAVAILABLE",
        msg="GammaMarket导入失败，部分功能可能不可用"
    )


# ========== 数据结构 ==========

@dataclass
class Market:
    """市场数据结构（用于仓位分配算法）"""
    id: Any                      # 市场ID（字符串或整数）
    m: float                     # YES价格（市场报价）
    p_yes: float                 # 主观YES概率（AI预测）
    d: int                       # 结算日期（天数索引，相对于now_day）
    p_no: Optional[float] = None # 主观NO概率（可选，默认为1-p_yes）


# ========== 工具函数 ==========

def clip01(x: float, eps: float = 1e-9) -> float:
    """将数值裁剪到(eps, 1-eps)区间，避免数值问题"""
    return float(min(1 - eps, max(eps, x)))


def choose_side(m: float, p_yes: float, p_no: Optional[float], weight: float) -> Optional[Dict]:
    """
    根据边际对数效用在f=0的导数，选择YES或NO方向（只选其一）

    参数:
        m: YES价格
        p_yes: 主观YES概率
        p_no: 主观NO概率（可选）
        weight: 时间权重（时间贴现因子）

    返回:
        dict: {'side', 'price', 'p', 'b', 'deriv0'} 或 None（不交易）
    """
    m = clip01(m)
    p_yes = clip01(p_yes)
    if p_no is None:
        p_no = 1.0 - p_yes
    else:
        p_no = clip01(p_no)

    # 边际在f=0的导数（乘以时间权重）
    # YES: w*(p/m - 1); NO: w*(q/(1-m) - 1)
    deriv_yes = weight * (p_yes / m - 1.0)
    deriv_no = weight * (p_no / (1.0 - m) - 1.0)

    if max(deriv_yes, deriv_no) <= 0.0:
        return None  # 两个方向边际都<=0，不交易

    if deriv_yes >= deriv_no:
        side = "YES"
        price = m
        p = p_yes
        b = 1.0 / m - 1.0  # 赔率
    else:
        side = "NO"
        price = 1.0 - m
        p = p_no
        b = 1.0 / (1.0 - m) - 1.0

    return {
        "side": side,
        "price": price,
        "p": p,
        "b": b,
        "deriv0": max(deriv_yes, deriv_no)
    }


def f_from_mu(p: float, b: float, w: float, mu: float, f_cap: float = 0.95, iters: int = 40) -> float:
    """
    给定水位μ，求解单市场最优仓位f

    解方程: w * [p*b/(1+f*b) - (1-p)/(1-f)] = mu
    使用二分法在区间[0, f_cap]上求解

    参数:
        p: 赢面概率
        b: 赔率
        w: 时间权重
        mu: 水位（拉格朗日乘子）
        f_cap: 单市场仓位上限
        iters: 二分迭代次数

    返回:
        float: 最优仓位比例f
    """
    p = clip01(p)
    b = max(1e-9, b)
    w = max(1e-12, w)
    f_cap = min(0.999999, max(1e-6, f_cap))

    # 若边际在0处已经 <= mu，则f=0
    deriv0 = w * (p * b - (1.0 - p))
    if deriv0 <= mu + 1e-12:
        return 0.0

    # 无约束（mu=0）的Kelly最优上界，用于二分右端点
    f_kelly = (p * b - (1.0 - p)) / b
    f_kelly = max(0.0, min(f_cap, f_kelly))

    lo, hi = 0.0, f_kelly
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        val = w * (p * b / (1.0 + mid * b) - (1.0 - p) / (1.0 - mid))
        if val > mu:
            lo = mid  # 需要更大f来降低边际
        else:
            hi = mid
    return hi


# ========== 核心分配函数 ==========

def allocate(
    markets_today: List[Market],
    wealth: Optional[float] = None,
    locked_value_now: Optional[float] = None,
    now_day: int = 0,
    k: float = 0.6,
    theta: Optional[Dict] = None
) -> List[Dict]:
    """
    基于凯利 + 水位法 + 时间贴现的多市场自动仓位分配

    参数:
        markets_today: 今天新到的若干Market
        wealth: 当前总权益（现金 + 未结算仓位成本），None则从purse获取
        locked_value_now: 目前已锁仓成本金额，None则从purse获取
        now_day: 当前天索引（整数）
        k: 最大锁仓占比（0~1）
        theta: 策略参数dict，包含:
            * 'lambda_time': 久期指数贴现系数 λ >= 0
            * 'c_fraction': 分数凯利系数 c ∈ (0,1]
            * 'f_cap': 单市场上限（默认0.95）

    返回:
        allocations: 列表，每个元素包含:
            {'id', 'side', 'price', 'p', 'b', 'f', 'invest', 'shares', 'settle_day'}

    备注:
        - 只在"今天"上新市场中做选择，不动已有仓位（持有到期）
        - 保证新增锁仓占比不超过 k_rem = k - locked_value_now/wealth
    """
    # 从purse获取资金状态（如果未提供）
    purse = get_purse()
    if wealth is None:
        wealth = purse.get_total_fund()
        vlogger.debug(
            "POSITION.ALLOCATE.WEALTH_FROM_PURSE",
            msg="从purse获取总资金",
            extra={"wealth": wealth}
        )

    if locked_value_now is None:
        locked_value_now = purse.get_locked_fund()
        vlogger.debug(
            "POSITION.ALLOCATE.LOCKED_FROM_PURSE",
            msg="从purse获取锁定资金",
            extra={"locked_value_now": locked_value_now}
        )

    # 默认策略参数
    if theta is None:
        theta = {}
    lam = float(theta.get("lambda_time", 0.0))
    c_frac = float(theta.get("c_fraction", 1.0))
    f_cap = float(theta.get("f_cap", 0.95))

    vlogger.info(
        "POSITION.ALLOCATE.START",
        msg="开始仓位分配",
        extra={
            "markets_count": len(markets_today),
            "wealth": wealth,
            "locked_value_now": locked_value_now,
            "now_day": now_day,
            "k": k,
            "lambda_time": lam,
            "c_fraction": c_frac,
            "f_cap": f_cap
        }
    )

    wealth = max(1e-9, wealth)
    locked_frac = locked_value_now / wealth
    k_rem = max(0.0, k - locked_frac)

    if k_rem <= 1e-12:
        vlogger.warn(
            "POSITION.ALLOCATE.NO_BUDGET",
            msg="剩余锁仓预算不足",
            extra={"k_rem": k_rem, "locked_frac": locked_frac}
        )
        return []

    # 组装候选（择优只选YES or NO一边）
    candidates = []
    for mk in markets_today:
        T = max(1, mk.d - now_day)  # 至少1天
        w = math.exp(-lam * T)      # 时间贴现权重
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
        vlogger.info(
            "POSITION.ALLOCATE.NO_CANDIDATES",
            msg="没有符合条件的候选市场"
        )
        return []

    # 若mu=0的总和就不超过预算，直接用各自Kelly，再乘分数系数c
    import numpy as np
    f_kelly = np.array([(c["p"] * c["b"] - (1.0 - c["p"])) / c["b"] for c in candidates], dtype=float)
    f_kelly = np.clip(f_kelly, 0.0, f_cap)
    sum_kelly = float(f_kelly.sum())

    if sum_kelly <= k_rem + 1e-12:
        # 预算充足，直接使用Kelly分配
        f_use = f_kelly * max(1e-9, min(1.0, c_frac))
        vlogger.info(
            "POSITION.ALLOCATE.KELLY_DIRECT",
            msg="预算充足，直接使用Kelly分配",
            extra={"sum_kelly": sum_kelly, "k_rem": k_rem}
        )
    else:
        # 水位二分：找到μ使得sum f(μ) = k_rem
        def sum_f(mu: float) -> float:
            s = 0.0
            for c in candidates:
                s += f_from_mu(c["p"], c["b"], c["w"], mu, f_cap=f_cap)
            return s

        lo, hi = 0.0, 1.0
        # 扩大hi直到sum_f(hi) <= k_rem
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
        # 额外分数Kelly（更保守）：整体缩放
        f_use *= max(1e-9, min(1.0, c_frac))

        vlogger.info(
            "POSITION.ALLOCATE.WATER_FILLING",
            msg="使用水位法分配",
            extra={"mu_star": mu_star, "sum_kelly": sum_kelly, "k_rem": k_rem}
        )

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

    vlogger.info(
        "POSITION.ALLOCATE.SUCCESS",
        msg="仓位分配完成",
        extra={
            "allocations_count": len(allocations),
            "total_invest": sum(a["invest"] for a in allocations)
        }
    )

    return allocations


# ========== 辅助转换函数 ==========

def convert_gamma_market_to_market(
    gamma_market: 'GammaMarket',
    p_yes: float,
    now_day: int = 0,
    p_no: Optional[float] = None
) -> Market:
    """
    将GammaMarket对象转换为Market对象

    参数:
        gamma_market: GammaMarket对象
        p_yes: AI预测的YES概率
        now_day: 当前天索引
        p_no: AI预测的NO概率（可选）

    返回:
        Market对象
    """
    # 计算结算日期（天数索引）
    # 假设gamma_market有end_date_iso字段
    try:
        from datetime import datetime
        if hasattr(gamma_market, 'end_date_iso') and gamma_market.end_date_iso:
            end_date = datetime.fromisoformat(gamma_market.end_date_iso.replace('Z', '+00:00'))
            now = datetime.now()
            days_to_settle = max(1, (end_date - now).days)
            d = now_day + days_to_settle
        else:
            d = now_day + 30  # 默认30天后结算
    except Exception as e:
        vlogger.warn(
            "POSITION.CONVERT.DATE_ERROR",
            msg="解析结算日期失败，使用默认值",
            extra={"error": str(e)}
        )
        d = now_day + 30

    # 获取YES价格
    m = gamma_market.outcome_prices[0] if gamma_market.outcome_prices else 0.5

    return Market(
        id=gamma_market.id,
        m=m,
        p_yes=p_yes,
        d=d,
        p_no=p_no
    )

