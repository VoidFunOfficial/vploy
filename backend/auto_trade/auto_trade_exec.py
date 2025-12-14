"""
自动交易执行模块

提供智能交易执行功能，包括:
- 订单簿扫描：分析订单簿深度，计算最优执行价格
- 限价单下单：根据扫单结果下限价单
- 完整的日志记录和异常处理

主要功能:
- trade(): 核心交易函数，传入side、cost、token_id，自动扫单并下单
"""

from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger

# 导入 Orderbook API
from ..polymarket_api.orderbook_api import PolymarketOrderbookClient

# 导入 CLOB API
from ..polymarket_api.clob_api import (
    create_limit_order,
    create_market_order,
    post_order,
    BUY,
    SELL,
    get_client,
    OrderType
)


def scan_orderbook(
    token_id: str,
    side: str,
    target_shares: float,
    max_cost: float,
    orderbook_client: Optional[PolymarketOrderbookClient] = None
) -> Dict[str, Any]:
    """
    扫描订单簿，计算达到目标shares所需的价格和成本，确保不超过最大成本

    参数:
        token_id (str): 代币 ID
        side (str): 交易方向，BUY 或 SELL
        target_shares (float): 目标购买数量（shares）
        max_cost (float): 最大允许成本（美元）
        orderbook_client (PolymarketOrderbookClient): 订单簿客户端，可选

    返回:
        dict: 扫单结果，包含以下字段：
            - success (bool): 是否成功
            - total_cost (float): 实际总成本
            - total_size (float): 总数量
            - avg_price (float): 平均价格
            - limit_price (float): 建议的限价单价格
            - levels (list): 扫描的订单簿层级详情
            - message (str): 结果说明

    异常:
        ValueError: 如果参数无效
        Exception: 如果扫单失败
    """
    # 参数验证
    if not token_id:
        raise ValueError("token_id 不能为空")

    if side not in [BUY, SELL]:
        raise ValueError(f"side 必须是 BUY 或 SELL，当前值: {side}")

    if target_shares <= 0:
        raise ValueError(f"target_shares 必须大于 0，当前值: {target_shares}")

    if max_cost <= 0:
        raise ValueError(f"max_cost 必须大于 0，当前值: {max_cost}")

    # 创建或使用提供的客户端
    should_close = False
    if orderbook_client is None:
        orderbook_client = PolymarketOrderbookClient()
        should_close = True

    try:
        vlogger.info("TRADE.SCAN.START", msg="开始扫描订单簿", extra={
            "token_id": token_id,
            "side": side,
            "target_shares": target_shares,
            "max_cost": max_cost
        })

        # 获取订单簿数据
        orderbook = orderbook_client.get_orderbook(token_id)

        # 根据交易方向选择订单簿一侧
        # BUY: 我们要买入，所以看卖单(asks)
        # SELL: 我们要卖出，所以看买单(bids)
        if side == BUY:
            orders = orderbook.get('asks', [])
            order_side_name = "asks"
        else:
            orders = orderbook.get('bids', [])
            order_side_name = "bids"

        if not orders:
            raise ValueError(f"订单簿 {order_side_name} 为空，无法执行交易")

        vlogger.info("TRADE.SCAN.ORDERBOOK", msg=f"获取订单簿成功", extra={
            "token_id": token_id,
            "side": side,
            "order_count": len(orders)
        })

        # 逐层扫单，累计成本和数量，目标是达到target_shares且不超过max_cost
        # 约束：最少消耗价格必须>1美元
        MIN_COST = 1.0
        accumulated_cost = 0.0
        accumulated_size = 0.0
        scanned_levels = []

        for level in orders:
            price = float(level['price'])
            size = float(level['size'])

            # 计算还需要多少shares
            remaining_shares = target_shares - accumulated_size

            if remaining_shares <= 0:
                # 已经达到目标shares
                break

            # 计算这一层可以吃掉多少数量
            level_size = min(size, remaining_shares)
            level_cost = price * level_size

            # 检查是否会超过最大成本
            if accumulated_cost + level_cost > max_cost:
                # 计算在成本约束下能买多少
                remaining_budget = max_cost - accumulated_cost
                affordable_size = remaining_budget / price if price > 0 else 0

                if affordable_size > 0:
                    scanned_levels.append({
                        'price': price,
                        'size': affordable_size,
                        'cost': remaining_budget,
                        'partial': True
                    })
                    accumulated_cost += remaining_budget
                    accumulated_size += affordable_size

                # 成本已达上限，停止扫描
                vlogger.warn("TRADE.SCAN.COST_LIMIT", msg="达到成本上限，无法完全满足目标shares", extra={
                    "target_shares": target_shares,
                    "accumulated_size": accumulated_size,
                    "max_cost": max_cost,
                    "accumulated_cost": accumulated_cost
                })
                break

            # 正常吃掉这一层（部分或全部）
            scanned_levels.append({
                'price': price,
                'size': level_size,
                'cost': level_cost,
                'partial': (level_size < size)
            })

            accumulated_cost += level_cost
            accumulated_size += level_size

        # 检查最少消耗约束
        if accumulated_cost < MIN_COST:
            vlogger.warn("TRADE.SCAN.MIN_COST", msg="总成本低于最小值1美元，调整为最小成本", extra={
                "original_cost": accumulated_cost,
                "min_cost": MIN_COST,
                "target_shares": target_shares
            })

            # 如果成本不足1美元，需要增加购买量
            # 重新扫描，确保至少花费1美元
            accumulated_cost = 0.0
            accumulated_size = 0.0
            scanned_levels = []

            for level in orders:
                price = float(level['price'])
                size = float(level['size'])

                # 计算这一层的成本
                level_cost = price * size

                # 如果加上这一层会超过最大成本
                if accumulated_cost + level_cost > max_cost:
                    # 计算还能花多少
                    remaining_budget = max_cost - accumulated_cost
                    affordable_size = remaining_budget / price if price > 0 else 0

                    if affordable_size > 0:
                        scanned_levels.append({
                            'price': price,
                            'size': affordable_size,
                            'cost': remaining_budget,
                            'partial': True
                        })
                        accumulated_cost += remaining_budget
                        accumulated_size += affordable_size
                    break

                # 完全吃掉这一层
                scanned_levels.append({
                    'price': price,
                    'size': size,
                    'cost': level_cost,
                    'partial': False
                })

                accumulated_cost += level_cost
                accumulated_size += size

                # 如果已经达到最小成本要求
                if accumulated_cost >= MIN_COST:
                    break

        # 检查是否达到目标
        if accumulated_size < target_shares:
            shortage = target_shares - accumulated_size
            vlogger.warn("TRADE.SCAN.INSUFFICIENT", msg="订单簿深度不足或成本超限", extra={
                "target_shares": target_shares,
                "accumulated_size": accumulated_size,
                "shortage": shortage,
                "max_cost": max_cost,
                "accumulated_cost": accumulated_cost
            })

        # 最终验证：确保成本至少为1美元
        if accumulated_cost < MIN_COST:
            vlogger.error("TRADE.SCAN.FINAL_CHECK_FAILED", msg="无法满足最小成本要求", error_code="E-TRADE-003", extra={
                "accumulated_cost": accumulated_cost,
                "min_cost": MIN_COST,
                "max_cost": max_cost
            })
            raise ValueError(f"无法满足最小成本要求：实际成本 ${accumulated_cost:.2f} < 最小成本 ${MIN_COST:.2f}")

        # 计算平均价格
        avg_price = accumulated_cost / accumulated_size if accumulated_size > 0 else 0

        # 建议的限价单价格：使用最后一层的价格
        limit_price = scanned_levels[-1]['price'] if scanned_levels else 0

        result = {
            'success': True,
            'total_cost': accumulated_cost,
            'total_size': accumulated_size,
            'avg_price': avg_price,
            'limit_price': limit_price,
            'levels': scanned_levels,
            'target_met': (accumulated_size >= target_shares),
            'min_cost_met': (accumulated_cost >= MIN_COST),
            'message': f"扫描完成，共 {len(scanned_levels)} 层，总成本 ${accumulated_cost:.2f}，总数量 {accumulated_size:.2f}"
        }

        vlogger.info("TRADE.SCAN.SUCCESS", msg="订单簿扫描成功", extra={
            "token_id": token_id,
            "side": side,
            "target_shares": target_shares,
            "total_cost": accumulated_cost,
            "total_size": accumulated_size,
            "avg_price": avg_price,
            "limit_price": limit_price,
            "target_met": result['target_met'],
            "min_cost_met": result['min_cost_met'],
            "levels_count": len(scanned_levels)
        })

        return result

    except Exception as e:
        error_msg = f"扫描订单簿失败: {str(e)}"
        vlogger.error("TRADE.SCAN.ERROR", msg=error_msg, error_code="E-TRADE-001", extra={
            "token_id": token_id,
            "side": side,
            "target_shares": target_shares,
            "max_cost": max_cost,
            "error": str(e)
        })
        raise

    finally:
        if should_close:
            orderbook_client.session.close()


def get_aggressive_price(
    token_id: str,
    side: str,
    orderbook_client: Optional[PolymarketOrderbookClient] = None
) -> Optional[float]:
    """
    获取贪婪压价策略的挂单价格

    策略：采用bid的最低价格 - 一个spread，贪婪地压低价格，不激进追求成交

    参数:
        token_id (str): 代币 ID
        side (str): 交易方向，BUY 或 SELL
        orderbook_client (PolymarketOrderbookClient): 订单簿客户端，可选

    返回:
        float: 贪婪压价后的挂单价格，如果订单簿深度不足则返回None
    """
    should_close = False
    if orderbook_client is None:
        orderbook_client = PolymarketOrderbookClient()
        should_close = True

    try:
        orderbook = orderbook_client.get_orderbook(token_id)

        # 获取spread信息
        spread_info = orderbook_client.get_spread(token_id)
        spread = float(spread_info.get('spread', 0))

        # BUY: 我们要买入，看bids（买单），取最低价格（最后一层）- spread
        # SELL: 我们要卖出，看asks（卖单），取最高价格（最后一层）+ spread
        if side == BUY:
            bids = orderbook.get('bids', [])
            if not bids:
                vlogger.warn("TRADE.AGGRESSIVE_PRICE.NO_BIDS", msg="订单簿bids为空", extra={
                    "token_id": token_id,
                    "side": side
                })
                return None

            # 取bids的最低价格（最后一层）
            lowest_bid = float(bids[-1]['price'])
            # 贪婪压价：最低bid - spread
            aggressive_price = max(0.01, lowest_bid - spread)  # 确保价格不低于0.01

            vlogger.info("TRADE.AGGRESSIVE_PRICE.SUCCESS", msg="计算贪婪压价（BUY）", extra={
                "token_id": token_id,
                "side": side,
                "lowest_bid": lowest_bid,
                "spread": spread,
                "aggressive_price": aggressive_price,
                "bids_depth": len(bids)
            })

        else:  # SELL
            asks = orderbook.get('asks', [])
            if not asks:
                vlogger.warn("TRADE.AGGRESSIVE_PRICE.NO_ASKS", msg="订单簿asks为空", extra={
                    "token_id": token_id,
                    "side": side
                })
                return None

            # 取asks的最高价格（最后一层）
            highest_ask = float(asks[-1]['price'])
            # 贪婪压价：最高ask + spread
            aggressive_price = min(0.99, highest_ask + spread)  # 确保价格不超过0.99

            vlogger.info("TRADE.AGGRESSIVE_PRICE.SUCCESS", msg="计算贪婪压价（SELL）", extra={
                "token_id": token_id,
                "side": side,
                "highest_ask": highest_ask,
                "spread": spread,
                "aggressive_price": aggressive_price,
                "asks_depth": len(asks)
            })

        return aggressive_price

    finally:
        if should_close:
            orderbook_client.session.close()


def trade(
    side: str,
    target_shares: float,
    max_cost: float,
    clobtoken: str,
    neg_risk: Optional[bool] = None,
    orderbook_client: Optional[PolymarketOrderbookClient] = None,
    clob_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    执行交易：采用贪婪压价策略挂限价单

    新逻辑（贪婪压价）：
    1. 获取bid最低价格 - spread（BUY）或 ask最高价格 + spread（SELL）
    2. 按贪婪价格挂限价单，不激进追求成交
    3. 返回order_id供监听模块追踪
    4. 如果10分钟后仍未成交，监听模块会调用sweep_order进行扫单

    参数:
        side (str): 交易方向，BUY 或 SELL
        target_shares (float): 目标购买数量（shares）
        max_cost (float): 最大允许成本（美元）
        clobtoken (str): 代币 ID (token_id)
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        orderbook_client (PolymarketOrderbookClient): 订单簿客户端，可选
        clob_client: CLOB 客户端，可选

    返回:
        dict: 交易结果，包含以下字段：
            - success (bool): 是否成功
            - order_id (str): 订单ID
            - order_response (dict): 订单提交响应
            - price (float): 挂单价格
            - size (float): 挂单数量
            - message (str): 结果说明

    异常:
        ValueError: 如果参数无效
        Exception: 如果交易失败
    """
    vlogger.info("TRADE.EXECUTE.START", msg="开始执行交易（贪婪压价策略）", extra={
        "side": side,
        "target_shares": target_shares,
        "max_cost": max_cost,
        "clobtoken": clobtoken,
        "neg_risk": neg_risk
    })

    try:
        # 步骤1: 获取贪婪压价价格
        aggressive_price = get_aggressive_price(
            token_id=clobtoken,
            side=side,
            orderbook_client=orderbook_client
        )
        
        if aggressive_price is None:
            raise ValueError("无法获取贪婪压价价格，订单簿深度不足")

        # 步骤2: 计算挂单数量（根据max_cost和aggressive_price）
        # size = max_cost / price
        order_size = max_cost / aggressive_price if aggressive_price > 0 else 0

        # 确保不超过target_shares
        if order_size > target_shares:
            order_size = target_shares

        vlogger.info("TRADE.ORDER.CALCULATE", msg="计算挂单参数", extra={
            "aggressive_price": aggressive_price,
            "max_cost": max_cost,
            "target_shares": target_shares,
            "calculated_size": order_size
        })

        # 步骤3: 创建限价单
        vlogger.info("TRADE.ORDER.CREATE_LIMIT", msg="创建贪婪压价限价单", extra={
            "token_id": clobtoken,
            "side": side,
            "price": aggressive_price,
            "size": order_size,
            "neg_risk": neg_risk
        })

        signed_order = create_limit_order(
            token_id=clobtoken,
            price=aggressive_price,
            size=order_size,
            side=side,
            neg_risk=neg_risk,
            client=clob_client
        )

        order_response = post_order(
            signed_order=signed_order,
            order_type=OrderType.GTC,  # Good Till Cancelled
            client=clob_client
        )

        # 从响应中提取order_id
        order_id = order_response.get('orderID') or order_response.get('order_id')

        if not order_id:
            vlogger.warn("TRADE.ORDER.NO_ORDER_ID", msg="订单响应中未找到order_id", extra={
                "order_response": order_response
            })

        result = {
            'success': True,
            'order_id': order_id,
            'order_response': order_response,
            'price': aggressive_price,
            'size': order_size,
            'order_type': 'LIMIT_AGGRESSIVE',
            'message': f"交易执行成功，已挂贪婪压价限价单（价格: {aggressive_price}, 数量: {order_size}）"
        }

        vlogger.info("TRADE.EXECUTE.SUCCESS", msg="交易执行成功", extra={
            "side": side,
            "target_shares": target_shares,
            "order_size": order_size,
            "max_cost": max_cost,
            "clobtoken": clobtoken,
            "price": aggressive_price,
            "order_id": order_id,
            "order_response": order_response
        })

        return result

    except Exception as e:
        error_msg = f"交易执行失败: {str(e)}"
        vlogger.error("TRADE.EXECUTE.ERROR", msg=error_msg, error_code="E-TRADE-002", extra={
            "side": side,
            "target_shares": target_shares,
            "max_cost": max_cost,
            "clobtoken": clobtoken,
            "error": str(e)
        })
        raise


def sweep_order(
    side: str,
    target_shares: float,
    max_cost: float,
    clobtoken: str,
    neg_risk: Optional[bool] = None,
    orderbook_client: Optional[PolymarketOrderbookClient] = None,
    clob_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    扫单交易：逐层扫描订单簿并下单

    当限价单10分钟后仍未成交时，监听模块会调用此函数进行扫单

    参数:
        side (str): 交易方向，BUY 或 SELL
        target_shares (float): 目标购买数量（shares）
        max_cost (float): 最大允许成本（美元）
        clobtoken (str): 代币 ID (token_id)
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        orderbook_client (PolymarketOrderbookClient): 订单簿客户端，可选
        clob_client: CLOB 客户端，可选

    返回:
        dict: 交易结果，包含以下字段：
            - success (bool): 是否成功
            - scan_result (dict): 扫单结果
            - order_response (dict): 订单提交响应
            - message (str): 结果说明

    异常:
        ValueError: 如果参数无效
        Exception: 如果交易失败
    """
    vlogger.info("TRADE.SWEEP.START", msg="开始扫单交易", extra={
        "side": side,
        "target_shares": target_shares,
        "max_cost": max_cost,
        "clobtoken": clobtoken,
        "neg_risk": neg_risk
    })

    try:
        # 步骤1: 扫描订单簿
        scan_result = scan_orderbook(
            token_id=clobtoken,
            side=side,
            target_shares=target_shares,
            max_cost=max_cost,
            orderbook_client=orderbook_client
        )

        if not scan_result['success']:
            raise ValueError(f"订单簿扫描失败: {scan_result.get('message', '未知错误')}")

        # 检查是否达到目标shares
        if not scan_result.get('target_met', False):
            vlogger.warn("TRADE.SWEEP.TARGET_NOT_MET", msg="无法完全满足目标shares", extra={
                "target_shares": target_shares,
                "actual_shares": scan_result['total_size'],
                "max_cost": max_cost,
                "actual_cost": scan_result['total_cost']
            })

        # 步骤2: 根据成本决定使用市价单还是限价单
        total_cost = scan_result['total_cost']
        total_size = scan_result['total_size']
        limit_price = scan_result['limit_price']

        # 成本阈值：≤2美元使用市价单，>2美元使用限价单
        MARKET_ORDER_THRESHOLD = 2.0

        if total_cost <= MARKET_ORDER_THRESHOLD:
            # 使用市价单
            vlogger.info("TRADE.SWEEP.CREATE_MARKET", msg="成本≤2美元，使用市价单", extra={
                "token_id": clobtoken,
                "side": side,
                "amount": total_cost,
                "total_cost": total_cost,
                "neg_risk": neg_risk
            })

            signed_order = create_market_order(
                token_id=clobtoken,
                amount=total_cost,
                side=side,
                neg_risk=neg_risk,
                client=clob_client
            )

            # 步骤3: 提交市价单（使用FOK订单类型）
            order_response = post_order(
                signed_order=signed_order,
                order_type=OrderType.FOK,
                client=clob_client
            )

            order_type_used = "MARKET"
        else:
            # 使用限价单
            vlogger.info("TRADE.SWEEP.CREATE_LIMIT", msg="成本>2美元，使用限价单", extra={
                "token_id": clobtoken,
                "side": side,
                "price": limit_price,
                "size": total_size,
                "total_cost": total_cost,
                "neg_risk": neg_risk
            })

            signed_order = create_limit_order(
                token_id=clobtoken,
                price=limit_price,
                size=total_size,
                side=side,
                neg_risk=neg_risk,
                client=clob_client
            )

            # 步骤3: 提交限价单
            order_response = post_order(
                signed_order=signed_order,
                client=clob_client
            )

            order_type_used = "LIMIT"

        result = {
            'success': True,
            'scan_result': scan_result,
            'order_response': order_response,
            'order_type': order_type_used,
            'message': f"扫单交易执行成功，订单已提交（{order_type_used}）"
        }

        vlogger.info("TRADE.SWEEP.SUCCESS", msg="扫单交易执行成功", extra={
            "side": side,
            "target_shares": target_shares,
            "actual_shares": total_size,
            "max_cost": max_cost,
            "actual_cost": scan_result['total_cost'],
            "clobtoken": clobtoken,
            "limit_price": limit_price,
            "order_type": order_type_used,
            "order_response": order_response
        })

        return result

    except Exception as e:
        error_msg = f"扫单交易执行失败: {str(e)}"
        vlogger.error("TRADE.SWEEP.ERROR", msg=error_msg, error_code="E-TRADE-004", extra={
            "side": side,
            "target_shares": target_shares,
            "max_cost": max_cost,
            "clobtoken": clobtoken,
            "error": str(e)
        })
        raise


# ==================== 模块导出 ====================

__all__ = [
    "scan_orderbook",
    "get_aggressive_price",
    "trade",
    "sweep_order",
]
