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
    post_order,
    BUY,
    SELL,
    get_client
)


def scan_orderbook(
    token_id: str,
    side: str,
    target_cost: float,
    orderbook_client: Optional[PolymarketOrderbookClient] = None
) -> Dict[str, Any]:
    """
    扫描订单簿，计算达到目标成本所需的价格和数量

    参数:
        token_id (str): 代币 ID
        side (str): 交易方向，BUY 或 SELL
        target_cost (float): 目标成本（美元）
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

    if target_cost <= 0:
        raise ValueError(f"target_cost 必须大于 0，当前值: {target_cost}")

    # 创建或使用提供的客户端
    should_close = False
    if orderbook_client is None:
        orderbook_client = PolymarketOrderbookClient()
        should_close = True

    try:
        vlogger.info("TRADE.SCAN.START", msg="开始扫描订单簿", extra={
            "token_id": token_id,
            "side": side,
            "target_cost": target_cost
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

        # 逐层扫单，累计成本和数量
        accumulated_cost = 0.0
        accumulated_size = 0.0
        scanned_levels = []

        for level in orders:
            price = float(level['price'])
            size = float(level['size'])

            # 计算这一层的成本
            level_cost = price * size

            # 如果加上这一层会超过目标成本
            if accumulated_cost + level_cost >= target_cost:
                # 计算还需要多少成本
                remaining_cost = target_cost - accumulated_cost
                # 计算这一层需要吃掉多少数量
                partial_size = remaining_cost / price if price > 0 else 0

                scanned_levels.append({
                    'price': price,
                    'size': partial_size,
                    'cost': remaining_cost,
                    'partial': True
                })

                accumulated_cost += remaining_cost
                accumulated_size += partial_size
                break
            else:
                # 完全吃掉这一层
                scanned_levels.append({
                    'price': price,
                    'size': size,
                    'cost': level_cost,
                    'partial': False
                })

                accumulated_cost += level_cost
                accumulated_size += size

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
            'message': f"扫描完成，共 {len(scanned_levels)} 层，总成本 ${accumulated_cost:.2f}，总数量 {accumulated_size:.2f}"
        }

        vlogger.info("TRADE.SCAN.SUCCESS", msg="订单簿扫描成功", extra={
            "token_id": token_id,
            "side": side,
            "total_cost": accumulated_cost,
            "total_size": accumulated_size,
            "avg_price": avg_price,
            "limit_price": limit_price,
            "levels_count": len(scanned_levels)
        })

        return result

    except Exception as e:
        error_msg = f"扫描订单簿失败: {str(e)}"
        vlogger.error("TRADE.SCAN.ERROR", msg=error_msg, error_code="E-TRADE-001", extra={
            "token_id": token_id,
            "side": side,
            "target_cost": target_cost,
            "error": str(e)
        })
        raise

    finally:
        if should_close:
            orderbook_client.session.close()


def trade(
    side: str,
    cost: float,
    clobtoken: str,
    neg_risk: Optional[bool] = None,
    orderbook_client: Optional[PolymarketOrderbookClient] = None,
    clob_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    执行交易：扫描订单簿并下限价单

    参数:
        side (str): 交易方向，BUY 或 SELL
        cost (float): 目标成本（美元）
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
        "cost": cost,
        "clobtoken": clobtoken,
        "neg_risk": neg_risk
    })

    try:
        # 步骤1: 扫描订单簿
        scan_result = scan_orderbook(
            token_id=clobtoken,
            side=side,
            target_cost=cost,
            orderbook_client=orderbook_client
        )

        if not scan_result['success']:
            raise ValueError(f"订单簿扫描失败: {scan_result.get('message', '未知错误')}")

        # 步骤2: 创建限价单
        limit_price = scan_result['limit_price']
        total_size = scan_result['total_size']

        vlogger.info("TRADE.ORDER.CREATE", msg="创建限价单", extra={
            "token_id": clobtoken,
            "side": side,
            "price": limit_price,
            "size": total_size,
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

        # 步骤3: 提交订单
        order_response = post_order(
            signed_order=signed_order,
            client=clob_client
        )

        result = {
            'success': True,
            'scan_result': scan_result,
            'order_response': order_response,
            'message': f"交易执行成功，订单已提交"
        }

        vlogger.info("TRADE.EXECUTE.SUCCESS", msg="交易执行成功", extra={
            "side": side,
            "cost": cost,
            "clobtoken": clobtoken,
            "limit_price": limit_price,
            "total_size": total_size,
            "order_response": order_response
        })

        return result

    except Exception as e:
        error_msg = f"交易执行失败: {str(e)}"
        vlogger.error("TRADE.EXECUTE.ERROR", msg=error_msg, error_code="E-TRADE-002", extra={
            "side": side,
            "cost": cost,
            "clobtoken": clobtoken,
            "error": str(e)
        })
        raise


# ==================== 模块导出 ====================

__all__ = [
    "scan_orderbook",
    "trade",
]
