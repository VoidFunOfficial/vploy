"""
持仓监听模块

提供持仓监听功能，将持仓信息写入数据库监听列表。
"""

import json
from typing import Optional, Dict, Any, List
from ..sys_configs.global_event_reg import vlogger
from ..polymarket_api import GammaMarketsAPI, Market, Event
from ..polymarket_api.orderbook_api import PolymarketOrderbookClient
from ..sys_configs import add_position_listen, get_position_listen_list
from ..polymarket_api.orderbook_api import PolymarketOrderbookClient

def add_position_to_listen(
    market_id: str,
    buy_price: float,
    buy_side: str,
    marks: Optional[str] = None,
    shares: Optional[float] = None
) -> bool:
    """
    添加持仓到监听列表

    参数:
        market_id: 市场ID (字符串类型)
        buy_price: 买入价格 (浮点数, 范围0-1)
        buy_side: 买入方向 (YES/NO)
        marks: 标记/备注信息 (可选)
        shares: 持仓份额 (可选)

    返回:
        bool: 是否添加成功

    示例:
        >>> add_position_to_listen(
        ...     market_id="0x1234567890abcdef",
        ...     buy_price=0.65,
        ...     buy_side="YES",
        ...     marks="AI预测概率0.75, Kelly建议投入$500",
        ...     shares=100.0
        ... )
        True
    """
    try:
        # 参数验证
        if not market_id:
            vlogger.error(
                "POSITION.LISTEN.INVALID_PARAM",
                msg="market_id不能为空",
                error_code="E-POSITION-001"
            )
            return False

        if buy_side not in ['YES', 'NO']:
            vlogger.error(
                "POSITION.LISTEN.INVALID_PARAM",
                msg=f"buy_side必须是'YES'或'NO', 当前值: {buy_side}",
                error_code="E-POSITION-002",
                extra={"buy_side": buy_side}
            )
            return False

        if not (0.0 < buy_price < 1.0):
            vlogger.error(
                "POSITION.LISTEN.INVALID_PARAM",
                msg=f"buy_price必须在0到1之间, 当前值: {buy_price}",
                error_code="E-POSITION-003",
                extra={"buy_price": buy_price}
            )
            return False

        if shares is not None and shares < 0:
            vlogger.error(
                "POSITION.LISTEN.INVALID_PARAM",
                msg=f"shares必须大于等于0, 当前值: {shares}",
                error_code="E-POSITION-009",
                extra={"shares": shares}
            )
            return False

        # 记录日志
        vlogger.info(
            "POSITION.LISTEN.ADD_START",
            msg="开始添加持仓监听",
            extra={
                "market_id": market_id,
                "buy_price": buy_price,
                "buy_side": buy_side,
                "marks": marks,
                "shares": shares
            }
        )

        # 调用数据库操作
        success = add_position_listen(
            market_id=market_id,
            buy_price=buy_price,
            buy_side=buy_side,
            marks=marks,
            shares=shares
        )

        if success:
            vlogger.info(
                "POSITION.LISTEN.ADD_SUCCESS",
                msg="持仓监听添加成功",
                extra={
                    "market_id": market_id,
                    "buy_price": buy_price,
                    "buy_side": buy_side
                }
            )
        else:
            vlogger.error(
                "POSITION.LISTEN.ADD_FAILED",
                msg="持仓监听添加失败",
                error_code="E-POSITION-004",
                extra={
                    "market_id": market_id,
                    "buy_price": buy_price,
                    "buy_side": buy_side
                }
            )

        return success

    except Exception as e:
        vlogger.error(
            "POSITION.LISTEN.ADD_ERROR",
            msg="添加持仓监听时发生异常",
            error_code="E-POSITION-005",
            extra={
                "market_id": market_id,
                "error": str(e)
            }
        )
        return False


def check_position(market_id: Optional[str] = None) -> Dict[str, Any]:
    """
    检查和更新持仓监听列表中的市场价格信息

    参数:
        market_id: 市场ID (可选)。如果提供则只检查该市场，否则检查所有激活的监听记录

    返回:
        dict: 处理结果，包含以下字段：
            - success: 是否成功
            - total: 总处理数量
            - processed: 成功处理数量
            - failed: 失败数量
            - results: 每个市场的处理结果列表

    示例:
        >>> # 检查所有激活的监听记录
        >>> result = check_position()
        >>> print(f"处理了 {result['processed']} 个市场")

        >>> # 检查特定市场
        >>> result = check_position(market_id="0x1234567890abcdef")
    """
    try:
        vlogger.info(
            "POSITION.CHECK.START",
            msg="开始检查持仓监听列表",
            extra={"market_id": market_id}
        )

        # 步骤1: 获取监听记录
        if market_id:
            # 查询特定市场的激活记录
            listen_records = get_position_listen_list(market_id=market_id, is_active=True)
        else:
            # 查询所有激活的记录
            listen_records = get_position_listen_list(is_active=True)

        if not listen_records:
            vlogger.info(
                "POSITION.CHECK.NO_RECORDS",
                msg="没有找到激活的监听记录",
                extra={"market_id": market_id}
            )
            return {
                "success": True,
                "total": 0,
                "processed": 0,
                "failed": 0,
                "results": []
            }

        vlogger.info(
            "POSITION.CHECK.RECORDS_FOUND",
            msg=f"找到 {len(listen_records)} 条监听记录",
            extra={"count": len(listen_records)}
        )

        # 初始化结果统计
        results = []
        processed_count = 0
        failed_count = 0

        # 创建API客户端
        with GammaMarketsAPI() as gamma_api:
            with PolymarketOrderbookClient() as orderbook_client:

                # 遍历每条监听记录
                for record in listen_records:
                    record_market_id = record['market_id']
                    buy_price = record['buy_price']
                    buy_side = record['buy_side']
                    marks = record['marks']
                    shares = record.get('shares')

                    try:
                        vlogger.info(
                            "POSITION.CHECK.PROCESS_RECORD",
                            msg="处理监听记录",
                            extra={
                                "record_id": record['id'],
                                "market_id": record_market_id,
                                "buy_side": buy_side
                            }
                        )

                        # 步骤1.1: 获取市场数据
                        market = gamma_api.get_market_by_id(record_market_id)

                        if not market:
                            vlogger.warn(
                                "POSITION.CHECK.MARKET_NOT_FOUND",
                                msg="未找到市场数据",
                                extra={"market_id": record_market_id}
                            )
                            failed_count += 1
                            results.append({
                                "market_id": record_market_id,
                                "success": False,
                                "error": "市场不存在"
                            })
                            continue

                        # 步骤1.2: 获取当前价格
                        now_price = None

                        # 检查是否有clobTokenIds
                        if not market.clobTokenIds or len(market.clobTokenIds) < 2:
                            vlogger.warn(
                                "POSITION.CHECK.NO_TOKEN_IDS",
                                msg="市场缺少clobTokenIds",
                                extra={"market_id": record_market_id}
                            )
                            failed_count += 1
                            results.append({
                                "market_id": record_market_id,
                                "success": False,
                                "error": "市场缺少token信息"
                            })
                            continue

                        # 根据buy_side确定使用哪个token_id
                        if buy_side == "YES":
                            token_id = market.clobTokenIds[0]  # YES token
                        elif buy_side == "NO":
                            token_id = market.clobTokenIds[1]  # NO token
                        else:
                            vlogger.error(
                                "POSITION.CHECK.INVALID_SIDE",
                                msg="无效的buy_side",
                                error_code="E-POSITION-002",
                                extra={"buy_side": buy_side, "market_id": record_market_id}
                            )
                            failed_count += 1
                            results.append({
                                "market_id": record_market_id,
                                "success": False,
                                "error": f"无效的buy_side: {buy_side}"
                            })
                            continue

                        # 使用Orderbook API获取当前价格
                        try:
                            now_price = orderbook_client.get_midpoint(token_id)

                            vlogger.info(
                                "POSITION.CHECK.PRICE_FETCHED",
                                msg="获取当前价格成功",
                                extra={
                                    "market_id": record_market_id,
                                    "token_id": token_id,
                                    "buy_side": buy_side,
                                    "now_price": now_price
                                }
                            )
                        except Exception as e:
                            vlogger.error(
                                "POSITION.CHECK.PRICE_ERROR",
                                msg="获取价格失败",
                                error_code="E-POSITION-006",
                                extra={
                                    "market_id": record_market_id,
                                    "token_id": token_id,
                                    "error": str(e)
                                }
                            )
                            failed_count += 1
                            results.append({
                                "market_id": record_market_id,
                                "success": False,
                                "error": f"获取价格失败: {str(e)}"
                            })
                            continue

                        # 步骤3: 调用process_position函数
                        process_result = process_position(
                            buy_price=buy_price,
                            now_price=now_price,
                            buy_side=buy_side,
                            marks=marks,
                            shares=shares
                        )

                        processed_count += 1
                        results.append({
                            "market_id": record_market_id,
                            "success": True,
                            "buy_price": buy_price,
                            "now_price": now_price,
                            "buy_side": buy_side,
                            "marks": marks,
                            "shares": shares,
                            "process_result": process_result
                        })

                        vlogger.info(
                            "POSITION.CHECK.RECORD_SUCCESS",
                            msg="监听记录处理成功",
                            extra={
                                "market_id": record_market_id,
                                "buy_price": buy_price,
                                "now_price": now_price,
                                "price_change": now_price - buy_price
                            }
                        )

                    except Exception as e:
                        vlogger.error(
                            "POSITION.CHECK.RECORD_ERROR",
                            msg="处理监听记录时发生异常",
                            error_code="E-POSITION-007",
                            extra={
                                "market_id": record_market_id,
                                "error": str(e)
                            }
                        )
                        failed_count += 1
                        results.append({
                            "market_id": record_market_id,
                            "success": False,
                            "error": str(e)
                        })

        # 返回汇总结果
        result = {
            "success": True,
            "total": len(listen_records),
            "processed": processed_count,
            "failed": failed_count,
            "results": results
        }

        vlogger.info(
            "POSITION.CHECK.COMPLETE",
            msg="持仓检查完成",
            extra={
                "total": result['total'],
                "processed": result['processed'],
                "failed": result['failed']
            }
        )

        return result

    except Exception as e:
        vlogger.error(
            "POSITION.CHECK.ERROR",
            msg="检查持仓监听列表时发生异常",
            error_code="E-POSITION-008",
            extra={"error": str(e)}
        )
        return {
            "success": False,
            "total": 0,
            "processed": 0,
            "failed": 0,
            "results": [],
            "error": str(e)
        }


def process_position(
    buy_price: float,
    now_price: float,
    buy_side: str,
    marks: Optional[str] = None,
    shares: Optional[float] = None
) -> Dict[str, Any]:
    """
    处理持仓信息（占位函数，待实现具体逻辑）

    参数:
        buy_price: 买入价格
        now_price: 当前市场价格
        buy_side: 买入方向 (YES/NO)
        marks: 备注信息
        shares: 持仓份额

    返回:
        dict: 处理结果
    """
    # TODO: 实现具体的持仓处理逻辑
    # 这里只是一个占位实现

    price_change = now_price - buy_price
    price_change_pct = (price_change / buy_price * 100) if buy_price > 0 else 0

    # 计算盈亏
    profit_loss = None
    profit_loss_pct = None
    if shares is not None:
        profit_loss = price_change * shares
        profit_loss_pct = price_change_pct

    vlogger.info(
        "POSITION.PROCESS",
        msg="处理持仓信息",
        extra={
            "buy_price": buy_price,
            "now_price": now_price,
            "buy_side": buy_side,
            "marks": marks,
            "shares": shares,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct
        }
    )

    return {
        "buy_price": buy_price,
        "now_price": now_price,
        "buy_side": buy_side,
        "marks": marks,
        "shares": shares,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "profit_loss": profit_loss,
        "profit_loss_pct": profit_loss_pct
    }
