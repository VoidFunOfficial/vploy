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
    执行交易：扫描订单簿并下限价单

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
    vlogger.info("TRADE.EXECUTE.START", msg="开始执行交易", extra={
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
            vlogger.warn("TRADE.EXECUTE.TARGET_NOT_MET", msg="无法完全满足目标shares", extra={
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
            vlogger.info("TRADE.ORDER.CREATE_MARKET", msg="成本≤2美元，使用市价单", extra={
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
            vlogger.info("TRADE.ORDER.CREATE_LIMIT", msg="成本>2美元，使用限价单", extra={
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
            'message': f"交易执行成功，订单已提交（{order_type_used}）"
        }

        vlogger.info("TRADE.EXECUTE.SUCCESS", msg="交易执行成功", extra={
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
        error_msg = f"交易执行失败: {str(e)}"
        vlogger.error("TRADE.EXECUTE.ERROR", msg=error_msg, error_code="E-TRADE-002", extra={
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
    "trade",
]
