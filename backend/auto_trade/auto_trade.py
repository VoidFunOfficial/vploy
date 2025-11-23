"""
自动交易模块

该模块实现自动交易功能，包括：
1. 从 auto_decision 模块获取交易决策指令
2. 获取订单簿数据并分析流动性
3. 计算滑点并调整限价单价格
4. 执行限价单下单操作
5. 完整的错误处理和日志记录

主要功能：
- 滑点控制：分析订单簿深度，计算预期滑点
- 智能定价：根据流动性调整限价单价格
- 风险管理：避免过大滑点，确保交易安全
- 日志记录：使用 VLogger 记录所有关键操作
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import time
from decimal import Decimal, ROUND_HALF_UP

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger
from ..sys_configs.auto_trade_config import get_auto_trade_config

# 导入交易决策模块
from ..auto_decision.position_manager import (
    TradeInstruction,
    allocate_optimal_positions_pro
)

# 导入 Polymarket API 模块
from ..polymarket_api.orderbook_api import PolymarketOrderbookClient
from ..polymarket_api.clob_api import (
    place_limit_buy_order,
    place_limit_sell_order,
    get_client,
    BUY,
    SELL
)

# 导入 Gamma Markets API
from ..polymarket_api.gamma_markets import GammaMarketsAPI


# ==================== 数据结构 ====================

@dataclass
class OrderBookAnalysis:
    """
    订单簿分析结果

    属性:
        token_id: 代币 ID
        best_bid: 最优买价
        best_ask: 最优卖价
        bid_depth: 买盘深度（按价格层级）
        ask_depth: 卖盘深度（按价格层级）
        total_bid_volume: 总买盘量
        total_ask_volume: 总卖盘量
        spread: 买卖价差
        spread_percent: 价差百分比
        liquidity_score: 流动性评分（0-100）
    """
    token_id: str
    best_bid: float
    best_ask: float
    bid_depth: List[Tuple[float, float]]  # [(price, size), ...]
    ask_depth: List[Tuple[float, float]]  # [(price, size), ...]
    total_bid_volume: float
    total_ask_volume: float
    spread: float
    spread_percent: float
    liquidity_score: float


@dataclass
class SlippageAnalysis:
    """
    滑点分析结果

    属性:
        expected_slippage: 预期滑点（百分比）
        impact_price: 冲击价格
        recommended_price: 推荐限价单价格
        max_safe_size: 最大安全交易量
        risk_level: 风险等级（LOW/MEDIUM/HIGH）
    """
    expected_slippage: float
    impact_price: float
    recommended_price: float
    max_safe_size: float
    risk_level: str


@dataclass
class TradeExecution:
    """
    交易执行结果

    属性:
        instruction: 原始交易指令
        orderbook_analysis: 订单簿分析
        slippage_analysis: 滑点分析
        final_price: 最终执行价格
        final_size: 最终执行数量
        order_response: 订单响应
        execution_time: 执行时间戳
        success: 是否成功
        error_message: 错误信息（如果失败）
    """
    instruction: TradeInstruction
    orderbook_analysis: Optional[OrderBookAnalysis]
    slippage_analysis: Optional[SlippageAnalysis]
    final_price: Optional[float]
    final_size: Optional[float]
    order_response: Optional[Dict[str, Any]]
    execution_time: float
    success: bool
    error_message: Optional[str] = None


# ==================== 配置常量（已迁移到数据库） ====================

# 获取配置对象（缓存机制）
def _get_config():
    """获取配置对象（带缓存）"""
    if not hasattr(_get_config, '_cached_config'):
        _get_config._cached_config = get_auto_trade_config()
    return _get_config._cached_config

def _refresh_config():
    """刷新配置缓存"""
    if hasattr(_get_config, '_cached_config'):
        delattr(_get_config, '_cached_config')

# 为了向后兼容，提供常量形式（在模块加载时初始化）
_config = get_auto_trade_config()
MAX_SLIPPAGE_PERCENT = _config.max_slippage_percent
LIQUIDITY_THRESHOLD = _config.liquidity_threshold
MIN_ORDER_SIZE = _config.min_order_size
MAX_ORDER_SIZE = _config.max_order_size
PRICE_IMPROVEMENT_FACTOR = _config.price_improvement_factor
SAFETY_MARGIN = _config.safety_margin
MAX_RETRIES = _config.max_retries
RETRY_DELAY = _config.retry_delay


# ==================== 核心类 ====================

class AutoTrader:
    """
    自动交易器

    负责执行完整的自动交易流程：
    1. 获取交易指令
    2. 分析订单簿
    3. 计算滑点
    4. 执行交易
    """

    def __init__(self):
        """初始化自动交易器"""
        self.orderbook_client = None
        self.clob_client = None
        self.config = None  # 配置对象，延迟加载

        vlogger.info("AUTO_TRADE.INIT", msg="自动交易器初始化")

    def _get_config(self):
        """获取配置对象（延迟加载）"""
        if self.config is None:
            self.config = get_auto_trade_config()
        return self.config

    def refresh_config(self):
        """刷新配置（重新从数据库加载）"""
        self.config = None
        _refresh_config()  # 刷新全局缓存
        vlogger.info("AUTO_TRADE.CONFIG.REFRESHED", msg="配置已刷新")

    def __enter__(self):
        """上下文管理器入口"""
        self.orderbook_client = PolymarketOrderbookClient()
        self.orderbook_client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.orderbook_client:
            self.orderbook_client.__exit__(exc_type, exc_val, exc_tb)

    def get_trade_instructions(
        self,
        gamma_markets: List[Any],
        ai_analysis: Dict[str, Any],
        **kwargs
    ) -> List[TradeInstruction]:
        """
        获取交易决策指令

        参数:
            gamma_markets: Gamma Markets 数据
            ai_analysis: AI 分析结果
            **kwargs: 其他参数传递给 allocate_optimal_positions_pro

        返回:
            List[TradeInstruction]: 交易指令列表
        """
        vlogger.info("AUTO_TRADE.GET_INSTRUCTIONS", msg="获取交易决策指令", extra={
            "market_count": len(gamma_markets)
        })

        try:
            # 调用仓位分配算法
            result = allocate_optimal_positions_pro(
                gamma_markets=gamma_markets,
                ai_analysis_result=ai_analysis,
                **kwargs
            )

            if not result["success"]:
                vlogger.error("AUTO_TRADE.GET_INSTRUCTIONS_ERROR",
                            msg="获取交易指令失败",
                            error_code="E-AT-001",
                            extra={"error": result.get("error")})
                return []

            instructions = result["instructions"]
            vlogger.info("AUTO_TRADE.GET_INSTRUCTIONS_SUCCESS",
                        msg="获取交易指令成功",
                        extra={"instruction_count": len(instructions)})

            return instructions

        except Exception as e:
            vlogger.error("AUTO_TRADE.GET_INSTRUCTIONS_EXCEPTION",
                        msg="获取交易指令异常",
                        error_code="E-AT-002",
                        extra={"exception": str(e)})
            return []

    def analyze_orderbook(self, token_id: str) -> Optional[OrderBookAnalysis]:
        """
        分析订单簿数据

        参数:
            token_id: 代币 ID

        返回:
            Optional[OrderBookAnalysis]: 订单簿分析结果
        """
        vlogger.info("AUTO_TRADE.ANALYZE_ORDERBOOK", msg="分析订单簿", extra={
            "token_id": token_id
        })

        try:
            # 获取订单簿数据
            orderbook = self.orderbook_client.get_orderbook(token_id)

            if not orderbook:
                vlogger.warn("AUTO_TRADE.ORDERBOOK_EMPTY", msg="订单簿为空", extra={
                    "token_id": token_id
                })
                return None

            # 解析买卖盘数据
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                vlogger.warn("AUTO_TRADE.ORDERBOOK_INCOMPLETE", msg="订单簿数据不完整", extra={
                    "token_id": token_id,
                    "bids_count": len(bids),
                    "asks_count": len(asks)
                })
                return None

            # 转换数据格式
            bid_depth = [(float(bid["price"]), float(bid["size"])) for bid in bids]
            ask_depth = [(float(ask["price"]), float(ask["size"])) for ask in asks]

            # 计算基本指标
            best_bid = bid_depth[0][0] if bid_depth else 0.0
            best_ask = ask_depth[0][0] if ask_depth else 0.0

            total_bid_volume = sum(size for _, size in bid_depth)
            total_ask_volume = sum(size for _, size in ask_depth)

            spread = best_ask - best_bid if best_bid > 0 and best_ask > 0 else 0.0
            spread_percent = (spread / best_bid * 100) if best_bid > 0 else 0.0

            # 计算流动性评分
            liquidity_score = self._calculate_liquidity_score(
                total_bid_volume, total_ask_volume, spread_percent
            )

            analysis = OrderBookAnalysis(
                token_id=token_id,
                best_bid=best_bid,
                best_ask=best_ask,
                bid_depth=bid_depth,
                ask_depth=ask_depth,
                total_bid_volume=total_bid_volume,
                total_ask_volume=total_ask_volume,
                spread=spread,
                spread_percent=spread_percent,
                liquidity_score=liquidity_score
            )

            vlogger.info("AUTO_TRADE.ANALYZE_ORDERBOOK_SUCCESS", msg="订单簿分析完成", extra={
                "token_id": token_id,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread_percent": f"{spread_percent:.2f}%",
                "liquidity_score": f"{liquidity_score:.1f}"
            })

            return analysis

        except Exception as e:
            vlogger.error("AUTO_TRADE.ANALYZE_ORDERBOOK_ERROR",
                        msg="订单簿分析失败",
                        error_code="E-AT-003",
                        extra={"token_id": token_id, "error": str(e)})
            return None

    def calculate_slippage(
        self,
        orderbook_analysis: OrderBookAnalysis,
        instruction: TradeInstruction
    ) -> Optional[SlippageAnalysis]:
        """
        计算滑点并生成推荐价格

        参数:
            orderbook_analysis: 订单簿分析结果
            instruction: 交易指令

        返回:
            Optional[SlippageAnalysis]: 滑点分析结果
        """
        vlogger.info("AUTO_TRADE.CALCULATE_SLIPPAGE", msg="计算滑点", extra={
            "token_id": orderbook_analysis.token_id,
            "side": instruction.side,
            "alloc_dollars": instruction.alloc_cents / 100.0
        })

        try:
            # 确定交易方向和相关数据
            is_buy = instruction.side == "BUY_YES"
            target_volume = instruction.alloc_cents / 100.0  # 转换为美元

            if is_buy:
                # 买单：分析卖盘深度
                depth = orderbook_analysis.ask_depth
                best_price = orderbook_analysis.best_ask
            else:
                # 卖单：分析买盘深度
                depth = orderbook_analysis.bid_depth
                best_price = orderbook_analysis.best_bid

            if not depth or best_price <= 0:
                vlogger.warn("AUTO_TRADE.SLIPPAGE_NO_DEPTH", msg="无法获取订单簿深度", extra={
                    "token_id": orderbook_analysis.token_id,
                    "side": instruction.side
                })
                return None

            # 计算冲击价格和滑点
            impact_price, consumed_volume = self._calculate_impact_price(depth, target_volume, is_buy)

            if impact_price <= 0:
                vlogger.warn("AUTO_TRADE.SLIPPAGE_CALC_FAILED", msg="滑点计算失败", extra={
                    "token_id": orderbook_analysis.token_id,
                    "target_volume": target_volume
                })
                return None

            # 计算滑点百分比
            expected_slippage = abs(impact_price - best_price) / best_price * 100

            # 生成推荐价格（考虑价格改善）
            if is_buy:
                # 买单：在冲击价格基础上稍微提高，确保成交
                config = self._get_config()
                recommended_price = impact_price * (1 + config.price_improvement_factor)
                recommended_price = min(recommended_price, 0.99)  # 限制最高价格
            else:
                # 卖单：在冲击价格基础上稍微降低，确保成交
                recommended_price = impact_price * (1 - config.price_improvement_factor)
                recommended_price = max(recommended_price, 0.01)  # 限制最低价格

            # 计算最大安全交易量
            config = self._get_config()
            max_safe_size = self._calculate_max_safe_size(depth, config.max_slippage_percent, is_buy)

            # 确定风险等级
            risk_level = self._determine_risk_level(expected_slippage, orderbook_analysis.liquidity_score)

            analysis = SlippageAnalysis(
                expected_slippage=expected_slippage,
                impact_price=impact_price,
                recommended_price=recommended_price,
                max_safe_size=max_safe_size,
                risk_level=risk_level
            )

            vlogger.info("AUTO_TRADE.CALCULATE_SLIPPAGE_SUCCESS", msg="滑点计算完成", extra={
                "token_id": orderbook_analysis.token_id,
                "expected_slippage": f"{expected_slippage:.2f}%",
                "impact_price": impact_price,
                "recommended_price": recommended_price,
                "risk_level": risk_level
            })

            return analysis

        except Exception as e:
            vlogger.error("AUTO_TRADE.CALCULATE_SLIPPAGE_ERROR",
                        msg="滑点计算异常",
                        error_code="E-AT-004",
                        extra={"token_id": orderbook_analysis.token_id, "error": str(e)})
            return None

    def execute_trade(self, instruction: TradeInstruction, gamma_market: Optional[Any] = None) -> TradeExecution:
        """
        执行单个交易指令

        参数:
            instruction: 交易指令
            gamma_market: Gamma Market 对象（可选，用于获取 token_id）

        返回:
            TradeExecution: 交易执行结果
        """
        execution_start = time.time()

        vlogger.info("AUTO_TRADE.EXECUTE_TRADE", msg="开始执行交易", extra={
            "market_id": instruction.market_id,
            "side": instruction.side,
            "alloc_dollars": instruction.alloc_cents / 100.0
        })

        # 初始化执行结果
        execution = TradeExecution(
            instruction=instruction,
            orderbook_analysis=None,
            slippage_analysis=None,
            final_price=None,
            final_size=None,
            order_response=None,
            execution_time=execution_start,
            success=False
        )

        try:
            # 步骤1：获取token_id
            if gamma_market:
                # 从 gamma_market 对象获取 token_id
                token_id = self._get_token_id_from_market(gamma_market, instruction.side)
            else:
                # 如果没有提供 gamma_market，尝试使用 market_id（向后兼容）
                vlogger.warn("AUTO_TRADE.NO_GAMMA_MARKET",
                           msg="未提供 gamma_market 对象，无法获取 token_id",
                           extra={"market_id": instruction.market_id})
                token_id = None

            if not token_id:
                execution.error_message = f"无法获取市场 {instruction.market_id} 的 token_id"
                vlogger.error("AUTO_TRADE.TOKEN_ID_ERROR",
                            msg=execution.error_message,
                            error_code="E-AT-005")
                return execution

            # 步骤2：分析订单簿
            orderbook_analysis = self.analyze_orderbook(token_id)
            execution.orderbook_analysis = orderbook_analysis

            if not orderbook_analysis:
                execution.error_message = "订单簿分析失败"
                return execution

            # 步骤3：计算滑点
            slippage_analysis = self.calculate_slippage(orderbook_analysis, instruction)
            execution.slippage_analysis = slippage_analysis

            if not slippage_analysis:
                execution.error_message = "滑点计算失败"
                return execution

            # 步骤4：风险检查
            if not self._validate_trade_risk(slippage_analysis, instruction):
                execution.error_message = f"交易风险过高：滑点 {slippage_analysis.expected_slippage:.2f}%"
                vlogger.warn("AUTO_TRADE.RISK_TOO_HIGH", msg=execution.error_message, extra={
                    "market_id": instruction.market_id,
                    "expected_slippage": slippage_analysis.expected_slippage,
                    "risk_level": slippage_analysis.risk_level
                })
                return execution

            # 步骤5：执行下单
            final_price = slippage_analysis.recommended_price
            final_size = instruction.alloc_cents / 100.0 / final_price  # 计算份额

            # 调整订单大小以符合限制
            final_size = max(MIN_ORDER_SIZE / final_price, min(final_size, MAX_ORDER_SIZE / final_price))

            execution.final_price = final_price
            execution.final_size = final_size

            # 获取全局 CLOB 客户端
            if not self.clob_client:
                self.clob_client = get_client()

            # 获取 negRisk 参数
            neg_risk = gamma_market.negRisk if gamma_market and hasattr(gamma_market, 'negRisk') else False

            # 执行限价单
            if instruction.side == "BUY_YES":
                order_response = place_limit_buy_order(
                    token_id=token_id,
                    price=final_price,
                    size=final_size,
                    neg_risk=neg_risk,
                    client=self.clob_client
                )
            else:  # BUY_NO 对应卖出 YES
                order_response = place_limit_sell_order(
                    token_id=token_id,
                    price=final_price,
                    size=final_size,
                    neg_risk=neg_risk,
                    client=self.clob_client
                )

            execution.order_response = order_response
            execution.success = True

            vlogger.info("AUTO_TRADE.EXECUTE_TRADE_SUCCESS", msg="交易执行成功", extra={
                "market_id": instruction.market_id,
                "token_id": token_id,
                "side": instruction.side,
                "final_price": final_price,
                "final_size": final_size,
                "order_response": order_response
            })

        except Exception as e:
            execution.error_message = f"交易执行异常: {str(e)}"
            vlogger.error("AUTO_TRADE.EXECUTE_TRADE_ERROR",
                        msg=execution.error_message,
                        error_code="E-AT-006",
                        extra={"market_id": instruction.market_id, "error": str(e)})

        execution.execution_time = time.time() - execution_start
        return execution

    def execute_batch_trades(
        self,
        instructions: List[TradeInstruction],
        gamma_markets: Optional[List[Any]] = None
    ) -> List[TradeExecution]:
        """
        批量执行交易指令

        参数:
            instructions: 交易指令列表
            gamma_markets: Gamma Market 对象列表（可选，用于获取 token_id）

        返回:
            List[TradeExecution]: 交易执行结果列表
        """
        vlogger.info("AUTO_TRADE.EXECUTE_BATCH", msg="开始批量执行交易", extra={
            "instruction_count": len(instructions)
        })

        # 创建 market_id 到 gamma_market 的映射
        market_map = {}
        if gamma_markets:
            for market in gamma_markets:
                if hasattr(market, 'id'):
                    market_map[str(market.id)] = market

        executions = []
        successful_count = 0

        for i, instruction in enumerate(instructions):
            vlogger.info("AUTO_TRADE.EXECUTE_BATCH_ITEM", msg=f"执行第 {i+1}/{len(instructions)} 个交易", extra={
                "market_id": instruction.market_id,
                "side": instruction.side
            })

            # 从映射中获取对应的 gamma_market
            gamma_market = market_map.get(instruction.market_id)

            execution = self.execute_trade(instruction, gamma_market)
            executions.append(execution)

            if execution.success:
                successful_count += 1

            # 在交易之间添加延迟，避免过于频繁的请求
            if i < len(instructions) - 1:
                time.sleep(RETRY_DELAY)

        vlogger.info("AUTO_TRADE.EXECUTE_BATCH_COMPLETE", msg="批量交易执行完成", extra={
            "total_count": len(instructions),
            "successful_count": successful_count,
            "failed_count": len(instructions) - successful_count
        })

        return executions

    # ==================== 辅助方法 ====================

    def _calculate_liquidity_score(
        self,
        bid_volume: float,
        ask_volume: float,
        spread_percent: float
    ) -> float:
        """
        计算流动性评分

        参数:
            bid_volume: 买盘总量
            ask_volume: 卖盘总量
            spread_percent: 价差百分比

        返回:
            float: 流动性评分（0-100）
        """
        # 基础流动性评分（基于交易量）
        total_volume = bid_volume + ask_volume
        config = self._get_config()
        volume_score = min(total_volume / config.liquidity_threshold * 50, 50)

        # 价差评分（价差越小评分越高）
        spread_score = max(0, 50 - spread_percent * 10)

        return min(100, volume_score + spread_score)

    def _calculate_impact_price(
        self,
        depth: List[Tuple[float, float]],
        target_volume: float,
        is_buy: bool
    ) -> Tuple[float, float]:
        """
        计算市场冲击价格

        参数:
            depth: 订单簿深度 [(price, size), ...]
            target_volume: 目标交易量（美元）
            is_buy: 是否为买单

        返回:
            Tuple[float, float]: (冲击价格, 消耗的交易量)
        """
        consumed_volume = 0.0
        weighted_price_sum = 0.0

        for price, size in depth:
            # 计算这一层级可以消耗的美元量
            layer_volume = price * size

            if consumed_volume + layer_volume >= target_volume:
                # 这一层级足够完成剩余交易
                remaining_volume = target_volume - consumed_volume
                remaining_size = remaining_volume / price

                weighted_price_sum += price * remaining_size
                consumed_volume = target_volume
                break
            else:
                # 消耗整个层级
                weighted_price_sum += price * size
                consumed_volume += layer_volume

        if consumed_volume == 0:
            return 0.0, 0.0

        # 计算加权平均价格
        total_size = weighted_price_sum / (consumed_volume / target_volume) if target_volume > 0 else 0
        impact_price = weighted_price_sum / total_size if total_size > 0 else 0.0

        return impact_price, consumed_volume

    def _calculate_max_safe_size(
        self,
        depth: List[Tuple[float, float]],
        max_slippage_percent: float,
        is_buy: bool
    ) -> float:
        """
        计算最大安全交易量

        参数:
            depth: 订单簿深度
            max_slippage_percent: 最大允许滑点百分比
            is_buy: 是否为买单

        返回:
            float: 最大安全交易量（美元）
        """
        if not depth:
            return 0.0

        best_price = depth[0][0]
        max_allowed_price = best_price * (1 + max_slippage_percent / 100) if is_buy else best_price * (1 - max_slippage_percent / 100)

        safe_volume = 0.0
        for price, size in depth:
            if (is_buy and price <= max_allowed_price) or (not is_buy and price >= max_allowed_price):
                safe_volume += price * size
            else:
                break

        return safe_volume

    def _determine_risk_level(self, slippage_percent: float, liquidity_score: float) -> str:
        """
        确定风险等级

        参数:
            slippage_percent: 滑点百分比
            liquidity_score: 流动性评分

        返回:
            str: 风险等级（LOW/MEDIUM/HIGH）
        """
        config = self._get_config()
        if slippage_percent > config.high_risk_slippage_threshold or liquidity_score < config.high_risk_liquidity_threshold:
            return "HIGH"
        elif slippage_percent > config.low_risk_slippage_threshold or liquidity_score < config.low_risk_liquidity_threshold:
            return "MEDIUM"
        else:
            return "LOW"

    def _validate_trade_risk(self, slippage_analysis: SlippageAnalysis, instruction: TradeInstruction) -> bool:
        """
        验证交易风险是否可接受

        参数:
            slippage_analysis: 滑点分析结果
            instruction: 交易指令

        返回:
            bool: 是否可接受
        """
        # 检查滑点是否超过限制
        config = self._get_config()
        if not config.enable_slippage_protection:
            return True  # 如果禁用滑点保护，跳过检查

        if slippage_analysis.expected_slippage > config.max_slippage_percent:
            return False

        # 检查流动性
        if config.enable_liquidity_check:
            if slippage_analysis.max_safe_size < config.liquidity_threshold:
                return False

        # 检查交易量是否超过安全限制
        target_volume = instruction.alloc_cents / 100.0
        if target_volume > slippage_analysis.max_safe_size:
            return False

        # 检查订单大小限制
        if config.enable_size_validation:
            if target_volume < config.min_order_size or target_volume > config.max_order_size:
                return False

        # 检查风险等级
        if slippage_analysis.risk_level == "HIGH":
            return False

        return True

    def _get_token_id_from_market(self, gamma_market: Any, side: str) -> Optional[str]:
        """
        从 Gamma Market 对象和交易方向获取 token_id

        参数:
            gamma_market: Gamma Market 对象（包含 clobTokenIds）
            side: 交易方向（BUY_YES/BUY_NO）

        返回:
            Optional[str]: token_id，如果获取失败返回None
        """
        try:
            # 从 gamma_market 获取 clobTokenIds
            if not hasattr(gamma_market, 'clobTokenIds') or not gamma_market.clobTokenIds:
                vlogger.error("AUTO_TRADE.GET_TOKEN_ID_ERROR",
                             msg="Market 对象缺少 clobTokenIds",
                             error_code="E-AT-007",
                             extra={"market_id": getattr(gamma_market, 'id', 'unknown')})
                return None

            clob_token_ids = gamma_market.clobTokenIds

            # clobTokenIds 是一个列表，通常：
            # [0] = YES token_id
            # [1] = NO token_id
            if side == "BUY_YES":
                token_id = clob_token_ids[0] if len(clob_token_ids) > 0 else None
            elif side == "BUY_NO":
                token_id = clob_token_ids[1] if len(clob_token_ids) > 1 else None
            else:
                vlogger.error("AUTO_TRADE.GET_TOKEN_ID_ERROR",
                             msg="无效的交易方向",
                             error_code="E-AT-007",
                             extra={"side": side})
                return None

            if not token_id:
                vlogger.error("AUTO_TRADE.GET_TOKEN_ID_ERROR",
                             msg="无法从 clobTokenIds 获取 token_id",
                             error_code="E-AT-007",
                             extra={
                                 "market_id": getattr(gamma_market, 'id', 'unknown'),
                                 "side": side,
                                 "clob_token_ids": clob_token_ids
                             })
                return None

            return token_id

        except Exception as e:
            vlogger.error("AUTO_TRADE.GET_TOKEN_ID_ERROR",
                         msg="获取 token_id 异常",
                         error_code="E-AT-007",
                         extra={
                             "market_id": getattr(gamma_market, 'id', 'unknown'),
                             "side": side,
                             "error": str(e)
                         })
            return None


# ==================== 便捷函数 ====================

def execute_auto_trading(
    gamma_markets: List[Any],
    ai_analysis: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    执行自动交易的便捷函数

    参数:
        gamma_markets: Gamma Markets 数据
        ai_analysis: AI 分析结果
        **kwargs: 其他参数

    返回:
        Dict[str, Any]: 执行结果
    """
    vlogger.info("AUTO_TRADE.EXECUTE_AUTO_TRADING", msg="开始自动交易流程", extra={
        "market_count": len(gamma_markets)
    })

    try:
        with AutoTrader() as trader:
            # 获取交易指令
            instructions = trader.get_trade_instructions(gamma_markets, ai_analysis, **kwargs)

            if not instructions:
                return {
                    "success": False,
                    "error": "没有获取到交易指令",
                    "instructions": [],
                    "executions": []
                }

            # 执行交易（传递 gamma_markets 以获取 token_id）
            executions = trader.execute_batch_trades(instructions, gamma_markets)

            # 统计结果
            successful_count = sum(1 for ex in executions if ex.success)
            total_allocated = sum(inst.alloc_cents for inst in instructions) / 100.0
            total_executed = sum(
                ex.final_price * ex.final_size
                for ex in executions
                if ex.success and ex.final_price and ex.final_size
            )

            result = {
                "success": True,
                "instructions": instructions,
                "executions": executions,
                "summary": {
                    "total_instructions": len(instructions),
                    "successful_executions": successful_count,
                    "failed_executions": len(executions) - successful_count,
                    "total_allocated_dollars": total_allocated,
                    "total_executed_dollars": total_executed,
                    "execution_rate": successful_count / len(instructions) * 100 if instructions else 0
                }
            }

            vlogger.info("AUTO_TRADE.EXECUTE_AUTO_TRADING_SUCCESS", msg="自动交易流程完成", extra={
                "successful_executions": successful_count,
                "total_instructions": len(instructions),
                "execution_rate": f"{result['summary']['execution_rate']:.1f}%"
            })

            return result

    except Exception as e:
        error_msg = f"自动交易流程异常: {str(e)}"
        vlogger.error("AUTO_TRADE.EXECUTE_AUTO_TRADING_ERROR",
                    msg=error_msg,
                    error_code="E-AT-008",
                    extra={"error": str(e)})

        return {
            "success": False,
            "error": error_msg,
            "instructions": [],
            "executions": []
        }


def get_execution_summary(executions: List[TradeExecution]) -> str:
    """
    生成交易执行结果的可读摘要

    参数:
        executions: 交易执行结果列表

    返回:
        str: 可读的摘要文本
    """
    if not executions:
        return "无交易执行记录"

    lines = []
    lines.append("=" * 80)
    lines.append(f"交易执行摘要（共 {len(executions)} 条）")
    lines.append("=" * 80)

    successful_count = 0
    total_volume = 0.0

    for idx, execution in enumerate(executions, start=1):
        lines.append(f"\n执行 #{idx}:")
        lines.append(f"  市场ID: {execution.instruction.market_id}")
        lines.append(f"  方向: {execution.instruction.side}")
        lines.append(f"  状态: {'成功' if execution.success else '失败'}")

        if execution.success:
            successful_count += 1
            if execution.final_price and execution.final_size:
                volume = execution.final_price * execution.final_size
                total_volume += volume
                lines.append(f"  执行价格: ${execution.final_price:.4f}")
                lines.append(f"  执行数量: {execution.final_size:.2f}")
                lines.append(f"  执行金额: ${volume:.2f}")
        else:
            lines.append(f"  错误信息: {execution.error_message}")

        if execution.slippage_analysis:
            lines.append(f"  预期滑点: {execution.slippage_analysis.expected_slippage:.2f}%")
            lines.append(f"  风险等级: {execution.slippage_analysis.risk_level}")

        lines.append(f"  执行时间: {execution.execution_time:.2f}秒")

    lines.append(f"\n总计:")
    lines.append(f"  成功执行: {successful_count}/{len(executions)}")
    lines.append(f"  成功率: {successful_count/len(executions)*100:.1f}%")
    lines.append(f"  总执行金额: ${total_volume:.2f}")
    lines.append("=" * 80)

    return "\n".join(lines)


# ==================== 模块导出 ====================

__all__ = [
    # 数据结构
    "OrderBookAnalysis",
    "SlippageAnalysis",
    "TradeExecution",

    # 核心类
    "AutoTrader",

    # 便捷函数
    "execute_auto_trading",
    "get_execution_summary",

    # 配置常量
    "MAX_SLIPPAGE_PERCENT",
    "LIQUIDITY_THRESHOLD",
    "MIN_ORDER_SIZE",
    "MAX_ORDER_SIZE",
]