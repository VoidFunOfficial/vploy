"""
自动止盈系统

集成多因子决策算法，实现智能止盈。
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from .surplus_cal import decide_hold_or_sell
from .easy_info import prepare_decision_data, get_market_realtime_data
from ..position_listener.database import PositionDatabase
from ..position_listener.models import Position
from ..polymarket_api import place_limit_sell_order, SELL
from ..sys_configs.global_event_reg import vlogger


def determine_strategy_tag(
    entry_price: float,
    tau_days: Optional[float] = None
) -> str:
    """
    根据入场价格和预期持有时长确定策略标签

    参数:
        entry_price: 入场价格
        tau_days: 预期持有天数

    返回:
        策略标签: "short-term", "long-term", "speculation", "consensus"
    """
    # 1. 根据tau判断短期/长期
    if tau_days is not None:
        if tau_days < 7:
            return "short-term"
        elif tau_days > 10:
            return "long-term"

    # 2. 根据entry_price判断speculation/consensus
    if entry_price < 0.3:
        return "speculation"
    elif entry_price > 0.7:
        return "consensus"

    # 3. 默认根据价格区间
    if entry_price < 0.5:
        return "speculation"
    else:
        return "consensus"


def execute_sell_order(
    token_id: str,
    position: Position,
    sell_fraction: float,
    reason: str
) -> Dict[str, Any]:
    """
    执行卖出操作

    参数:
        token_id: Token ID
        position: 持仓对象
        sell_fraction: 卖出比例 (0-1)
        reason: 卖出原因

    返回:
        执行结果
    """
    try:
        # 计算卖出数量
        sell_size = position.shares * sell_fraction

        if sell_size < 0.01:
            vlogger.warn(
                "SURPLUS.SELL.SIZE_TOO_SMALL",
                msg="卖出数量过小，跳过",
                extra={
                    "position_id": position.id,
                    "sell_size": sell_size
                }
            )
            return {
                "success": False,
                "message": "卖出数量过小"
            }

        # 获取当前价格
        realtime = get_market_realtime_data(token_id)
        sell_price = realtime['current_price']

        # 下限价卖单（略低于当前价格以确保成交）
        #spread = 
        adjusted_price = sell_price 

        vlogger.info(
            "SURPLUS.SELL.ORDER",
            msg="准备下卖单",
            extra={
                "position_id": position.id,
                "token_id": token_id,
                "sell_size": sell_size,
                "sell_price": adjusted_price,
                "sell_fraction": sell_fraction,
                "reason": reason
            }
        )

        # 下单
        order_response = place_limit_sell_order(
            token_id=token_id,
            price=adjusted_price,
            size=sell_size
        )

        vlogger.info(
            "SURPLUS.SELL.SUCCESS",
            msg="卖单提交成功",
            extra={
                "position_id": position.id,
                "order_id": order_response.get('orderID'),
                "sell_size": sell_size,
                "sell_price": adjusted_price
            }
        )

        return {
            "success": True,
            "order_id": order_response.get('orderID'),
            "sell_size": sell_size,
            "sell_price": adjusted_price,
            "reason": reason
        }

    except Exception as e:
        vlogger.error(
            "SURPLUS.SELL.ERROR",
            msg="执行卖单失败",
            error_code="E-SURPLUS-004",
            extra={
                "position_id": position.id,
                "error": str(e)
            }
        )
        return {
            "success": False,
            "message": f"执行卖单失败: {str(e)}"
        }


def auto_surplus_decision(
    position_id: int,
    token_id: str,
    tag: Optional[str] = None,
    execute: bool = False
) -> Dict[str, Any]:
    """
    自动止盈决策（单个持仓）

    参数:
        position_id: 持仓ID
        token_id: Token ID
        tag: 策略标签（可选，自动推断）
        execute: 是否执行卖出操作

    返回:
        决策结果
    """
    try:
        # 获取持仓信息
        db = PositionDatabase()
        position = db.get_position(position_id)

        if not position:
            return {
                "success": False,
                "message": f"持仓不存在: {position_id}"
            }

        # 计算tau（预期持有天数）
        tau_days = None
        if position.settle_day > 0:
            # settle_day是天数索引，计算距离现在的天数
            tau_days = position.settle_day

        # 确定策略标签
        if not tag:
            tag = determine_strategy_tag(position.entry_price, tau_days)

        vlogger.info(
            "SURPLUS.DECISION.START",
            msg="开始止盈决策",
            extra={
                "position_id": position_id,
                "token_id": token_id,
                "tag": tag,
                "entry_price": position.entry_price,
                "tau_days": tau_days
            }
        )

        # 准备决策数据
        data = prepare_decision_data(
            token_id=token_id,
            entry_time=position.create_time,
            lookback_hours=168  # 7天
        )

        # 调用决策算法
        decision = decide_hold_or_sell(
            tag=tag,
            entry_price=position.entry_price,
            entry_index=data['entry_index'],
            prices=data['prices'],
            volumes=data['volumes'],
            spreads=data['spreads'],
            current_price=data['current_price'],
            current_volume=data['volumes'][-1] if data['volumes'] else 1.0,
            current_spread=data['current_spread'],
            tau=tau_days
        )

        vlogger.info(
            "SURPLUS.DECISION.RESULT",
            msg="止盈决策完成",
            extra={
                "position_id": position_id,
                "action": decision['action'],
                "score": decision['score'],
                "threshold": decision['threshold'],
                "sell_fraction": decision['suggested_sell_fraction'],
                "reason": decision['reason']
            }
        )

        # 如果决策是SELL且execute=True，执行卖出
        result = {
            "success": True,
            "position_id": position_id,
            "tag": tag,
            "decision": decision,
            "executed": False
        }

        if decision['action'] == 'SELL' and execute:
            sell_result = execute_sell_order(
                token_id=token_id,
                position=position,
                sell_fraction=decision['suggested_sell_fraction'],
                reason=decision['reason']
            )
            result['executed'] = sell_result['success']
            result['sell_result'] = sell_result

        return result

    except Exception as e:
        vlogger.error(
            "SURPLUS.DECISION.ERROR",
            msg="止盈决策失败",
            error_code="E-SURPLUS-005",
            extra={
                "position_id": position_id,
                "error": str(e)
            }
        )
        return {
            "success": False,
            "message": f"止盈决策失败: {str(e)}"
        }


def auto_surplus_all_positions(execute: bool = False) -> Dict[str, Any]:
    """
    对所有持仓执行自动止盈检查

    参数:
        execute: 是否执行卖出操作

    返回:
        汇总结果
    """
    try:
        db = PositionDatabase()
        open_positions = db.get_open_positions()

        vlogger.info(
            "SURPLUS.ALL.START",
            msg="开始批量止盈检查",
            extra={
                "total_positions": len(open_positions),
                "execute": execute
            }
        )

        results = []
        sell_count = 0

        for position in open_positions:
            # 获取token_id（从metadata中）
            token_id = position.metadata.get('token_id')
            if not token_id:
                vlogger.warn(
                    "SURPLUS.ALL.NO_TOKEN_ID",
                    msg="持仓缺少token_id",
                    extra={"position_id": position.id}
                )
                continue

            # 执行决策
            result = auto_surplus_decision(
                position_id=position.id,
                token_id=token_id,
                execute=execute
            )

            results.append(result)

            if result.get('decision', {}).get('action') == 'SELL':
                sell_count += 1

        vlogger.info(
            "SURPLUS.ALL.COMPLETE",
            msg="批量止盈检查完成",
            extra={
                "total_positions": len(open_positions),
                "checked": len(results),
                "sell_signals": sell_count
            }
        )

        return {
            "success": True,
            "total_positions": len(open_positions),
            "checked": len(results),
            "sell_signals": sell_count,
            "results": results
        }

    except Exception as e:
        vlogger.error(
            "SURPLUS.ALL.ERROR",
            msg="批量止盈检查失败",
            error_code="E-SURPLUS-006",
            extra={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"批量止盈检查失败: {str(e)}"
        }
