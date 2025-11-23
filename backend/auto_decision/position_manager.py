from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
import math
from datetime import datetime
import json

# 导入 Polymarket API 客户端
from ..polymarket_api import get_client, get_collateral_balance, AssetType

# 1e6整数
def get_available_balance():
    return get_client().get_collateral_balance(AssetType.COLLATERAL).get('balance', 0)

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger

# 导入 Polymarket API 数据结构
try:
    from ..polymarket_api.gamma_markets import Market as GammaMarket
    GAMMA_MARKET_AVAILABLE = True
except ImportError:
    GAMMA_MARKET_AVAILABLE = False

# VLogger 事件和错误码已在全局事件注册文件中统一管理

TICK = 0.01
EPS  = 1e-12

# 精度常量：用于整数计算
CENTS_PRECISION = 100  # 1美元 = 100美分
PRICE_PRECISION = 10000  # 价格精度：0.0001 = 1个单位

# ---------- 数据类型 ----------
@dataclass
class Market:
    m: float                 # YES 市价 (0.01~0.99)
    p: float                 # 我们对 YES 的概率预测
    t: float                 # 到期天数 (>=1)
    a: float                 # 风险因子 (>=0, 越大越保守)
    market_id: str           # 市场 ID

@dataclass
class Allocation:
    index: int
    name: str
    side: str                # 'BUY_YES' | 'BUY_NO' | 'NO_TRADE'
    kelly_f: float           # 相对基准财富 B 的最终分配比例（已含分数 Kelly）
    alloc_cents: int         # 本事件投入的美分
    entry_price: float       # 入场价（买 YES 用 m；买 NO 用 1-m）
    shares: float            # 份额（按对应方向）
    EV_cents_if_hold: int    # 持有到结算的期望收益（美分，基于 p'）
    p_adj: float             # 风险收缩后的主观 YES 概率
    t_days: int            # 到期天数

# ---------- 工具 ----------
def clamp01(x: float, lo: float = 0.01, hi: float = 0.99) -> float:
    return float(min(max(x, lo), hi))

def gprime(success_prob: float, entry_price: float, f: float) -> float:
    """
    g(f) = s*ln(1+f*b) + (1-s)*ln(1-f),  b = 1/r - 1
    g'(f) = s*b/(1+f*b) - (1-s)/(1-f)
    """
    b = (1.0 / entry_price) - 1.0
    return (success_prob * b) / (1.0 + f * b) - (1.0 - success_prob) / (1.0 - f)

def kelly_unconstrained(s: float, r: float) -> float:
    """
    不带预算约束的 Kelly 比例（相对‘基准财富’的下注占比）。
    对价格 r、成功概率 s 的 0/1 资产：f* = (s - r) / (1 - r) 若 s>r，否则 0。
    """
    if s <= r + EPS:
        return 0.0
    return max(0.0, min((s - r) / (1.0 - r), 0.999999))

def pick_side_and_params(m: float, p_adj: float) -> Tuple[str, float, float]:
    """
    决定方向与（该方向下的）成功概率 s、入场价 r。
    BUY_YES : s=p_adj, r=m
    BUY_NO  : s=1-p_adj, r=1-m
    """
    m = clamp01(m)
    if p_adj > m + 1e-9:
        return "BUY_YES", p_adj, m
    elif p_adj < m - 1e-9:
        return "BUY_NO", 1.0 - p_adj, 1.0 - m
    else:
        return "NO_TRADE", 0.0, 0.0

def optimize_allocation_timeweighted(
    sides: List[str],
    s_vec: List[float],
    r_vec: List[float],
    D_vec: List[float],
    kappa_frac: float
) -> List[float]:
    """
    水位法：最大化 sum_i g_i(f_i)/D_i，约束 sum f_i <= kappa_frac，0<=f_i<=Kelly_unconstrained
    返回 f_i（相对“基准财富 B”的占比）
    """
    n = len(s_vec)
    tradable = [1 if sides[i] != "NO_TRADE" else 0 for i in range(n)]
    D = [max(1.0, float(t)) for t in D_vec]
    f_cap = [kelly_unconstrained(s_vec[i], r_vec[i]) if tradable[i] else 0.0 for i in range(n)]

    if sum(f_cap) <= kappa_frac + 1e-12:
        return f_cap

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

    f_opt = [f_i_lambda(i, lam_lo) for i in range(n)]
    return f_opt

# ---------- 主函数 ----------
def allocate_optimal_positions(
    events: List[Market],
    M_cents: int,
    kappa: float,
    locked_cents: int = 0,
    xi: float = 0.5,
    shrink_with_a: bool = True
) -> Dict[str, Any]:
    """
    给定一批独立事件（不做止盈、持有到结算），在全局锁定上限 kappa 下，
    最大化“单位时间”对数增长，返回本次的最佳方向与投入金额。

    参数
    ----
    events : List[Event]   每个事件包含 (m,p,t,a[,name])
    M_cents: int           当前现金（可立即部署）
    kappa  : float         全局锁定上限（含既有锁定，0..1）
    locked_cents: int      现有未结算头寸的名义成本（美分）
    xi     : float         分数 Kelly 系数（0..1），默认 0.5
    shrink_with_a: bool    是否用 a 对 p 做风险收缩，默认 True

    约束解释
    --------
    基准财富 B = M_cents + locked_cents
    全局允许新增锁定 = max(0, kappa * B - locked_cents)
    本次可部署预算（美分） = min(M_cents, 全局允许新增锁定)

    返回
    ----
    dict:
      - meta: {'B_cents','budget_cents','kappa','xi','used_cents'}
      - allocations: List[Allocation]
    """
    assert 0.0 <= kappa <= 1.0, "kappa 应在 [0,1]"
    assert 0.0 <= xi <= 1.0, "xi 应在 [0,1]"

    B_cents = int(M_cents + locked_cents)
    allow_new = int(max(0, round(kappa * B_cents - locked_cents)))
    budget_cents = int(min(M_cents, allow_new))

    # 若预算为 0，直接返回空计划
    if budget_cents <= 0 or len(events) == 0:
        return {
            "meta": {"B_cents": B_cents, "budget_cents": budget_cents, "kappa": kappa, "xi": xi, "used_cents": 0},
            "allocations": []
        }

    sides: List[str] = []
    s_vec: List[float] = []
    r_vec: List[float] = []
    D_vec: List[float] = []
    p_adj_vec: List[float] = []

    for ev in events:
        m = clamp01(ev.m); p = clamp01(ev.p); a = max(0.0, float(ev.a)); D = max(1.0, float(ev.t))
        p_adj = m + (p - m) / (1.0 + a) if shrink_with_a else p
        side, s, r = pick_side_and_params(m, p_adj)
        sides.append(side); s_vec.append(s); r_vec.append(max(TICK, r)); D_vec.append(D); p_adj_vec.append(p_adj)

    # 预算换算为“相对 B 的比例”
    kappa_frac_for_solver = min((budget_cents / max(1, B_cents)) / max(xi, 1e-9), 1.0)

    # 先解不含 xi 的 f，再乘 xi
    f_star = optimize_allocation_timeweighted(sides, s_vec, r_vec, D_vec, kappa_frac_for_solver)
    f_use  = [xi * f if sides[i] != "NO_TRADE" else 0.0 for i, f in enumerate(f_star)]

    # 初步金额（美分），并拦截总额不超过 budget_cents
    cents = [int(round(B_cents * f)) for f in f_use]
    total = sum(cents)
    if total > budget_cents and total > 0:
        scale = budget_cents / total
        cents = [int(math.floor(c * scale)) for c in cents]

    # 将余下的“零头美分”按 f_use 大小依次补齐，直至用完 budget
    residual = budget_cents - sum(cents)
    if residual > 0:
        order = sorted(range(len(events)), key=lambda i: f_use[i], reverse=True)
        k = 0
        while residual > 0 and order:
            j = order[k % len(order)]
            cents[j] += 1
            residual -= 1
            k += 1

    allocs: List[Allocation] = []
    used_cents = 0
    for i, ev in enumerate(events):
        name = getattr(ev, "market_id", f"ev_{i}")
        if sides[i] == "NO_TRADE" or cents[i] <= 0:
            allocs.append(Allocation(
                index=i, name=name, side="NO_TRADE", kelly_f=0.0, alloc_cents=0,
                entry_price=0.0, shares=0.0, EV_cents_if_hold=0, p_adj=p_adj_vec[i], t_days=D_vec[i]
            ))
            continue

        entry_r = r_vec[i]
        shares  = cents[i] / (entry_r * 100.0)

        # 期望收益（若持有到结算）：每 1 美元投资的期望回报 = s/r - 1
        EV_cents = int(round(cents[i] * (s_vec[i] / entry_r - 1.0)))

        allocs.append(Allocation(
            index=i, name=name, side=sides[i], kelly_f=float(f_use[i]),
            alloc_cents=int(cents[i]), entry_price=float(entry_r),
            shares=float(shares), EV_cents_if_hold=int(EV_cents),
            p_adj=float(p_adj_vec[i]), t_days=int(D_vec[i])
        ))
        used_cents += int(cents[i])

    return {
        "meta": {"B_cents": B_cents, "budget_cents": budget_cents, "kappa": kappa, "xi": xi, "used_cents": used_cents},
        "allocations": allocs
    }

# ==================== Pro 版本：整数精度优化 + 数据结构整合 ====================

@dataclass
class TradeInstruction:
    """
    交易指令数据结构

    属性:
        market_id: 市场 ID
        market_question: 市场问题描述
        side: 交易方向 ('BUY_YES' | 'BUY_NO' | 'NO_TRADE')
        alloc_cents: 投入金额（美分，整数）
        entry_price_cents: 入场价格（美分，整数，范围 1-99）
        shares_units: 购买份额（单位：0.0001份，整数）
        expected_profit_cents: 预期收益（美分，整数）
        kelly_fraction: Kelly 分配比例
        confidence_p: AI 预测的 YES 概率
        risk_factor_a: 风险因子
        days_to_expiry: 到期天数
        metadata: 额外元数据
    """
    market_id: str
    market_question: str
    side: str
    alloc_cents: int
    entry_price_cents: int
    shares_units: int
    expected_profit_cents: int
    kelly_fraction: float
    confidence_p: float
    risk_factor_a: float
    days_to_expiry: int
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "market_id": self.market_id,
            "market_question": self.market_question,
            "side": self.side,
            "alloc_cents": self.alloc_cents,
            "alloc_dollars": self.alloc_cents / 100.0,
            "entry_price": self.entry_price_cents / 100.0,
            "shares": self.shares_units / 10000.0,
            "expected_profit_cents": self.expected_profit_cents,
            "expected_profit_dollars": self.expected_profit_cents / 100.0,
            "kelly_fraction": self.kelly_fraction,
            "confidence_p": self.confidence_p,
            "risk_factor_a": self.risk_factor_a,
            "days_to_expiry": self.days_to_expiry,
            "metadata": self.metadata or {}
        }


def _parse_outcome_prices(outcome_prices_str: Optional[str]) -> List[float]:
    """
    解析市场价格字符串

    参数:
        outcome_prices_str: 价格字符串，可能是 JSON 数组格式

    返回:
        List[float]: 价格列表
    """
    if not outcome_prices_str:
        return []

    try:
        # 尝试解析 JSON 字符串
        if isinstance(outcome_prices_str, str):
            prices = json.loads(outcome_prices_str)
        else:
            prices = outcome_prices_str

        # 转换为浮点数列表
        return [float(p) for p in prices]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def _calculate_days_to_expiry(end_date_str: Optional[str]) -> int:
    """
    计算到期天数

    参数:
        end_date_str: 结束日期字符串（ISO 格式）

    返回:
        int: 到期天数（至少为1）
    """
    if not end_date_str:
        return 30  # 默认30天

    try:
        # 解析日期字符串
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        now = datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now()

        # 计算天数差
        days = (end_date - now).days

        # 至少返回1天
        return max(1, days)
    except (ValueError, AttributeError):
        return 30  # 解析失败，返回默认值


def convert_gamma_market_to_input(
    gamma_market: 'GammaMarket',
    ai_analysis: Dict[str, Any],
) -> Optional[Market]:
    """
    将 Gamma Market 和 AI 分析结果转换为仓位分配输入格式

    参数:
        gamma_market: Gamma API 返回的 Market 对象
        ai_analysis: AI 分析结果字典（AI 自动从 event_summary 中解析出的 market_id）
            格式: {
                "68095": {"p": 0.6, "a": 0.3, "reasons_p": [...], "reasons_n": [...]},
                "68096": {"p": 0.7, "a": 0.2, "reasons_p": [...], "reasons_n": [...]}
            }
            注意：键是 AI 自动解析出的 market_id 字符串

    返回:
        Optional[Market]: 转换后的 Market 对象，如果数据不完整或未找到匹配的分析结果则返回 None
    """
    try:
        # 解析价格
        prices = _parse_outcome_prices(gamma_market.outcome_prices)
        if not prices or len(prices) < 1:
            return None

        # 获取 YES 的市场价格（通常是第一个价格）
        m = prices[0]

        # 从 AI 分析结果中获取 p 和 a（使用 market_id 作为键）
        # AI 会自动从 event_summary 中解析出 market_id
        market_id = str(gamma_market.id)
        if market_id not in ai_analysis:
            vlogger.warn("POSITION.CONVERT.NO_ANALYSIS", msg="未找到对应的 AI 分析结果", extra={
                "market_id": market_id,
                "available_keys": list(ai_analysis.keys())[:5]  # 只显示前5个键
            })
            return None

        analysis = ai_analysis[market_id]
        p = analysis.get('p', 0.5)
        a = analysis.get('a', 0.5)

        # 计算到期天数（使用 closedTime 字段）
        end_date = getattr(gamma_market, 'closedTime', None) or getattr(gamma_market, 'end_date', None)
        t = _calculate_days_to_expiry(end_date)

        # 创建 Market 对象
        return Market(
            m=float(m),
            p=float(p),
            t=float(t),
            a=float(a),
            market_id=gamma_market.id
        )

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        vlogger.warn("POSITION.CONVERT.FAILED", msg="市场数据转换失败", extra={
            "market_id": getattr(gamma_market, 'id', 'unknown'),
            "error": str(e),
            "error_type": type(e).__name__
        })
        return None


# ==================== 精度优化的核心计算函数（整数版本） ====================

def _price_to_cents(price: float) -> int:
    """
    将价格（0-1范围）转换为美分表示（1-99）

    参数:
        price: 价格（0.01-0.99）

    返回:
        int: 美分表示的价格（1-99）
    """
    return max(1, min(99, int(round(price * 100))))


def _cents_to_price(cents: int) -> float:
    """
    将美分表示的价格转换为浮点数（0-1范围）

    参数:
        cents: 美分表示的价格（1-99）

    返回:
        float: 价格（0.01-0.99）
    """
    return cents / 100.0


def _calculate_shares_units(alloc_cents: int, price_cents: int) -> int:
    """
    计算购买份额（整数单位：0.0001份）

    参数:
        alloc_cents: 投入金额（美分）
        price_cents: 入场价格（美分，1-99）

    返回:
        int: 份额单位数（1单位 = 0.0001份）
    """
    if price_cents <= 0:
        return 0

    # shares = alloc_cents / (price_cents / 100)
    # shares_units = shares * 10000
    # 简化：shares_units = alloc_cents * 10000 / price_cents
    return (alloc_cents * 10000) // price_cents


def _calculate_expected_profit_cents(
    alloc_cents: int,
    success_prob_cents: int,
    entry_price_cents: int
) -> int:
    """
    计算预期收益（美分，整数）

    参数:
        alloc_cents: 投入金额（美分）
        success_prob_cents: 成功概率（美分表示，0-100）
        entry_price_cents: 入场价格（美分，1-99）

    返回:
        int: 预期收益（美分）
    """
    if entry_price_cents <= 0:
        return 0

    # EV = alloc * (success_prob / entry_price - 1)
    # 使用整数运算避免浮点数精度损失
    # EV_cents = alloc_cents * success_prob_cents / entry_price_cents - alloc_cents
    return (alloc_cents * success_prob_cents) // entry_price_cents - alloc_cents


def _allocate_residual_cents(
    cents_list: List[int],
    budget_cents: int,
    priority_indices: List[int]
) -> List[int]:
    """
    分配剩余的美分（按优先级）

    参数:
        cents_list: 当前分配的美分列表
        budget_cents: 总预算（美分）
        priority_indices: 优先级索引列表（从高到低）

    返回:
        List[int]: 调整后的美分列表
    """
    result = cents_list.copy()
    total = sum(result)
    residual = budget_cents - total

    if residual <= 0:
        return result

    # 按优先级分配剩余美分
    idx = 0
    while residual > 0 and priority_indices:
        i = priority_indices[idx % len(priority_indices)]
        result[i] += 1
        residual -= 1
        idx += 1

    return result


# ==================== Pro 版本主函数 ====================

def allocate_optimal_positions_pro(
    gamma_markets: List['GammaMarket'],
    ai_analysis_result: Dict[str, Any],
    M_cents: Optional[int] = None,
    kappa: float = 0.7,
    locked_cents: int = 0,
    xi: float = 0.5,
    shrink_with_a: bool = True
) -> Dict[str, Any]:
    """
    Pro 版本：整合 Gamma Markets 和 AI 分析结果的仓位分配函数

    特性：
    1. 全程使用整数（cents）进行计算，避免浮点数精度损失
    2. 直接接收 Gamma Markets 和 AI 分析结果
    3. AI 自动从 event_summary 中解析 market_id，无需手动匹配
    4. 返回具体的交易指令（包括买入/卖出方向和金额）
    5. 集成 VLogger 日志系统

    参数:
        gamma_markets: Gamma API 返回的 Market 对象列表
        ai_analysis_result: AI 分析结果字典（AI 自动解析的 market_id），格式：
            {
                "68095": {"p": 0.6, "a": 0.3, "reasons_p": [...], "reasons_n": [...]},
                "68096": {"p": 0.4, "a": 0.5, "reasons_p": [...], "reasons_n": [...]}
            }
            注意：
            - 键是 AI 自动从 event_summary 中解析出的 market_id（字符串格式）
            - 函数会自动匹配 gamma_markets 中的市场 ID 与 AI 分析结果
            - 如果某个市场没有对应的 AI 分析结果，该市场会被跳过
        M_cents: 当前可用现金（美分），如果为 None 则自动获取
        kappa: 全局锁定上限（0-1），默认 0.7
        locked_cents: 现有未结算头寸的名义成本（美分），默认 0
        xi: 分数 Kelly 系数（0-1），默认 0.5
        shrink_with_a: 是否用风险因子 a 对概率 p 做收缩，默认 True

    返回:
        Dict[str, Any]: 包含以下字段：
            - success: bool，是否成功
            - meta: 元数据（预算、使用金额等）
            - instructions: List[TradeInstruction]，交易指令列表
            - summary: 汇总信息
            - error: 错误信息（如果失败）
    """
    # 初始化日志
    vlogger.info("POSITION.ALLOCATE.START", msg="开始仓位分配（Pro版本）", extra={
        "market_count": len(gamma_markets),
        "M_cents": M_cents,
        "kappa": kappa,
        "locked_cents": locked_cents,
        "xi": xi,
        "shrink_with_a": shrink_with_a
    })

    try:
        # 步骤 1: 获取可用余额（如果未提供）
        if M_cents is None:
            M_cents = get_available_balance()

            vlogger.info("POSITION.BALANCE.FETCHED", msg="获取账户余额", extra={
                "M_cents": M_cents
            })

        # 步骤 2: 转换数据格式
        markets: List[Market] = []
        market_metadata: Dict[str, Dict[str, Any]] = {}  # 使用 market_id 作为键

        for gamma_market in gamma_markets:
            market = convert_gamma_market_to_input(gamma_market, ai_analysis_result)
            if market:
                markets.append(market)
                # 使用 market_id 作为键存储元数据
                market_metadata[market.market_id] = {
                    "question": gamma_market.question,
                    "slug": gamma_market.slug,
                    "volume": gamma_market.volume,
                    "liquidity": gamma_market.liquidity
                }

        if not markets:
            error_msg = "没有有效的市场数据"

            vlogger.error("POSITION.ALLOCATE.NO_MARKETS", msg=error_msg, error_code="E-POS-001")
            return {
                "success": False,
                "error": error_msg,
                "meta": {},
                "instructions": [],
                "summary": {}
            }


        vlogger.info("POSITION.MARKETS.CONVERTED", msg="市场数据转换完成", extra={
            "valid_markets": len(markets),
            "total_markets": len(gamma_markets)
        })

        # 步骤 3: 调用原有的分配算法
        allocation_result = allocate_optimal_positions(
            events=markets,
            M_cents=M_cents,
            kappa=kappa,
            locked_cents=locked_cents,
            xi=xi,
            shrink_with_a=shrink_with_a
        )

        # 步骤 4: 转换为交易指令
        instructions: List[TradeInstruction] = []
        total_alloc_cents = 0
        total_expected_profit_cents = 0

        for alloc in allocation_result["allocations"]:
            if alloc.side == "NO_TRADE" or alloc.alloc_cents <= 0:
                continue

            # 获取市场元数据（使用 market_id）
            market_id = alloc.name  # alloc.name 存储的是 market_id
            metadata = market_metadata.get(market_id, {})

            # 转换价格和份额为整数
            entry_price_cents = _price_to_cents(alloc.entry_price)
            shares_units = _calculate_shares_units(alloc.alloc_cents, entry_price_cents)

            # 计算成功概率（美分表示）
            if alloc.side == "BUY_YES":
                success_prob_cents = _price_to_cents(alloc.p_adj)
            else:  # BUY_NO
                success_prob_cents = _price_to_cents(1.0 - alloc.p_adj)

            # 重新计算预期收益（使用整数运算）
            expected_profit_cents = _calculate_expected_profit_cents(
                alloc.alloc_cents,
                success_prob_cents,
                entry_price_cents
            )

            # 获取风险因子（从 markets 列表中查找）
            risk_factor_a = 0.0
            for market in markets:
                if market.market_id == market_id:
                    risk_factor_a = market.a
                    break

            # 创建交易指令
            instruction = TradeInstruction(
                market_id=market_id,
                market_question=metadata.get("question", ""),
                side=alloc.side,
                alloc_cents=alloc.alloc_cents,
                entry_price_cents=entry_price_cents,
                shares_units=shares_units,
                expected_profit_cents=expected_profit_cents,
                kelly_fraction=alloc.kelly_f,
                confidence_p=alloc.p_adj,
                risk_factor_a=risk_factor_a,
                days_to_expiry=alloc.t_days,
                metadata=metadata
            )

            instructions.append(instruction)
            total_alloc_cents += alloc.alloc_cents
            total_expected_profit_cents += expected_profit_cents

        # 步骤 5: 生成汇总信息
        summary = {
            "total_markets": len(gamma_markets),
            "valid_markets": len(markets),
            "tradable_markets": len(instructions),
            "total_alloc_cents": total_alloc_cents,
            "total_alloc_dollars": total_alloc_cents / 100.0,
            "total_expected_profit_cents": total_expected_profit_cents,
            "total_expected_profit_dollars": total_expected_profit_cents / 100.0,
            "expected_roi": (total_expected_profit_cents / total_alloc_cents * 100.0) if total_alloc_cents > 0 else 0.0,
            "budget_utilization": (total_alloc_cents / allocation_result["meta"]["budget_cents"] * 100.0) if allocation_result["meta"]["budget_cents"] > 0 else 0.0
        }

        # 步骤 6: 记录成功日志

        vlogger.info("POSITION.ALLOCATE.SUCCESS", msg="仓位分配完成", extra={
            "tradable_markets": len(instructions),
            "total_alloc_cents": total_alloc_cents,
            "expected_profit_cents": total_expected_profit_cents,
            "expected_roi": f"{summary['expected_roi']:.2f}%"
        })

        return {
            "success": True,
            "meta": allocation_result["meta"],
            "instructions": instructions,
            "summary": summary,
            "error": None
        }

    except Exception as e:
        error_msg = f"仓位分配异常: {str(e)}"

        vlogger.error("POSITION.ALLOCATE.EXCEPTION", msg=error_msg, error_code="E-POS-002", extra={
            "exception": str(e),
            "exception_type": type(e).__name__
        })

        return {
            "success": False,
            "error": error_msg,
            "meta": {},
            "instructions": [],
            "summary": {}
        }


# ==================== 便捷函数 ====================

def get_trade_instructions_summary(instructions: List[TradeInstruction]) -> str:
    """
    生成交易指令的可读摘要

    参数:
        instructions: 交易指令列表

    返回:
        str: 可读的摘要文本
    """
    if not instructions:
        return "无交易指令"

    lines = []
    lines.append("=" * 80)
    lines.append(f"交易指令摘要（共 {len(instructions)} 条）")
    lines.append("=" * 80)

    for idx, inst in enumerate(instructions, start=1):
        lines.append(f"\n指令 #{idx}:")
        lines.append(f"  市场: {inst.market_question}")
        lines.append(f"  市场ID: {inst.market_id}")
        lines.append(f"  方向: {inst.side}")
        lines.append(f"  投入金额: ${inst.alloc_cents / 100.0:.2f} ({inst.alloc_cents} 美分)")
        lines.append(f"  入场价格: ${inst.entry_price_cents / 100.0:.2f}")
        lines.append(f"  购买份额: {inst.shares_units / 10000.0:.4f}")
        lines.append(f"  预期收益: ${inst.expected_profit_cents / 100.0:.2f} ({inst.expected_profit_cents} 美分)")
        lines.append(f"  Kelly 比例: {inst.kelly_fraction:.4f}")
        lines.append(f"  AI 预测概率: {inst.confidence_p:.2%}")
        lines.append(f"  风险因子: {inst.risk_factor_a:.2f}")
        lines.append(f"  到期天数: {inst.days_to_expiry} 天")

    lines.append("=" * 80)

    return "\n".join(lines)


def export_instructions_to_json(
    instructions: List[TradeInstruction],
    filepath: str
) -> bool:
    """
    导出交易指令到 JSON 文件

    参数:
        instructions: 交易指令列表
        filepath: 输出文件路径

    返回:
        bool: 是否成功
    """
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "instruction_count": len(instructions),
            "instructions": [inst.to_dict() for inst in instructions]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


        vlogger.info("POSITION.EXPORT.SUCCESS", msg="交易指令导出成功", extra={
            "filepath": filepath,
            "instruction_count": len(instructions)
        })

        return True

    except Exception as e:

        vlogger.error("POSITION.EXPORT.FAILED", msg="交易指令导出失败", error_code="E-POS-003", extra={
            "filepath": filepath,
            "error": str(e)
        })
        return False


# ---------------- 示例 ----------------
if __name__ == "__main__":
    # 构造 6 个事件做演示
    demo_events = [
        Market(m=0.42, p=0.51, t=5,  a=0.4, market_id="A"),
        Market(m=0.63, p=0.55, t=18, a=1.2, market_id="B"),
        Market(m=0.51, p=0.46, t=2,  a=0.2, market_id="C"),
        Market(m=0.22, p=0.35, t=9,  a=0.0, market_id="D"),
        Market(m=0.74, p=0.70, t=3,  a=0.7, market_id="E"),
        Market(m=0.33, p=0.29, t=14, a=0.3, market_id="F"),
        Market(m=0.01, p=0.9, t=7,  a=0.4, market_id="G"),
    ]
    # 当前现金 1000 美元、已锁定 300 美元、全局 kappa=0.7（总锁定不超 70%）
    M_cents = 100_000
    locked  = 30_000
    res = allocate_optimal_positions(demo_events, M_cents, kappa=0.7, locked_cents=locked, xi=0.5, shrink_with_a=True)

    print("Meta:", res["meta"])
    for r in res["allocations"]:
        print(asdict(r))
