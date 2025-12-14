"""
仓位监听模块

实现Polymarket仓位的实时监听和价格更新功能。
使用gamma_markets.py中的Market和Event数据结构。
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..vlogger import get_logger, TraceContext
from .database import get_db
from ..polymarket_api import GammaMarketsAPI
from ..polymarket_api.gamma_markets import Market


# 初始化日志记录器
logger = get_logger("position_monitor")


def get_market_data(market_id: str) -> Optional[Market]:
    """获取市场数据对象"""
    try:
        with GammaMarketsAPI() as api:
            return api.get_market_by_id(market_id)
    except Exception as e:
        logger.error("POSITION_MONITOR.GET_MARKET_ERROR", msg=f"获取市场失败: {market_id}",
                    error_code="E-PM-001", extra={"market_id": market_id, "error": str(e)})
        return None


def get_market_current_price(market: Market, side: str) -> Optional[float]:
    """从Market对象获取当前价格"""
    if not market.outcome_prices:
        return None

    # outcome_prices 可能是 JSON 数组字符串 '["0.625", "0.375"]' 或逗号分隔 "0.625,0.375"
    try:
        if market.outcome_prices.startswith('['):
            prices = json.loads(market.outcome_prices)
        else:
            prices = market.outcome_prices.split(',')

        if side == "YES":
            return float(prices[0])
        elif side == "NO":
            return float(prices[1])
        return None
    except:
        return None


def check_market_status(market: Market) -> bool:
    """检查市场是否已结束"""
    return not market.active if market.active is not None else False


def check_threshold_trigger(
    buy_price: float,
    current_price: float,
    threshold_config: Optional[str]
) -> Dict[str, Any]:
    """
    检查价格变动是否触发阈值
    
    参数:
        buy_price: 买入价格
        current_price: 当前价格
        threshold_config: 阈值配置JSON字符串
    
    返回:
        dict: 包含触发信息的字典
            - triggered: bool, 是否触发
            - change_percent: float, 价格变动百分比
            - change_absolute: float, 价格绝对变动
            - trigger_type: str, 触发类型 (percent/absolute/none)
    """
    result = {
        "triggered": False,
        "change_percent": 0.0,
        "change_absolute": 0.0,
        "trigger_type": "none"
    }
    
    # 计算价格变动
    change_absolute = current_price - buy_price
    change_percent = (change_absolute / buy_price) if buy_price > 0 else 0.0
    
    result["change_percent"] = change_percent
    result["change_absolute"] = change_absolute
    
    # 如果没有配置阈值，不触发
    if not threshold_config:
        return result
    
    try:
        config = json.loads(threshold_config)
        
        # 检查百分比阈值
        if "percent" in config:
            threshold_percent = float(config["percent"])
            if abs(change_percent) >= threshold_percent:
                result["triggered"] = True
                result["trigger_type"] = "percent"
                return result
        
        # 检查绝对值阈值
        if "absolute" in config:
            threshold_absolute = float(config["absolute"])
            if abs(change_absolute) >= threshold_absolute:
                result["triggered"] = True
                result["trigger_type"] = "absolute"
                return result
                
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warn(
            "POSITION_MONITOR.INVALID_THRESHOLD_CONFIG",
            msg=f"阈值配置解析失败: {threshold_config}",
            extra={"threshold_config": threshold_config, "error": str(e)}
        )
    
    return result


def update_position_data(position: Dict[str, Any]) -> bool:
    """
    更新单个仓位的价格和状态数据
    使用Market对象获取市场数据

    参数:
        position: 仓位数据字典

    返回:
        bool: 是否更新成功
    """
    position_id = position['id']
    market_id = position['market_id']
    buy_side = position['buy_side']
    buy_price = position['buy_price']
    threshold_config = position.get('threshold_config')

    with TraceContext() as trace_id:
        logger.info(
            "POSITION_MONITOR.UPDATE_START",
            msg=f"开始更新仓位数据: {position_id}",
            extra={"position_id": position_id, "market_id": market_id},
            trace_id=trace_id
        )

        try:
            # 获取Market对象
            market = get_market_data(market_id)

            if not market:
                logger.error(
                    "POSITION_MONITOR.MARKET_DATA_ERROR",
                    msg=f"无法获取市场数据: {market_id}",
                    error_code="E-PM-005",
                    extra={"position_id": position_id, "market_id": market_id},
                    trace_id=trace_id
                )
                return False

            # 从Market对象获取当前价格
            current_price = get_market_current_price(market, buy_side)

            # 从Market对象检查市场状态
            market_closed = check_market_status(market)

            # 获取数据库实例
            db = get_db()

            # 更新数据库
            success = db.update_position(
                position_id=position_id,
                current_price=current_price,
                market_closed=market_closed
            )

            if not success:
                logger.error(
                    "POSITION_MONITOR.UPDATE_FAILED",
                    msg=f"更新仓位数据失败: {position_id}",
                    error_code="E-PM-006",
                    extra={"position_id": position_id, "market_id": market_id},
                    trace_id=trace_id
                )
                return False

            # 检查阈值触发
            if current_price is not None:
                threshold_result = check_threshold_trigger(
                    buy_price=buy_price,
                    current_price=current_price,
                    threshold_config=threshold_config
                )

                if threshold_result["triggered"]:
                    logger.info(
                        "POSITION_MONITOR.THRESHOLD_TRIGGERED",
                        msg=f"仓位价格变动触发阈值: {position_id}",
                        extra={
                            "position_id": position_id,
                            "market_id": market_id,
                            "market_question": market.question,
                            "buy_price": buy_price,
                            "current_price": current_price,
                            "change_percent": threshold_result["change_percent"],
                            "change_absolute": threshold_result["change_absolute"],
                            "trigger_type": threshold_result["trigger_type"]
                        },
                        trace_id=trace_id
                    )

            logger.info(
                "POSITION_MONITOR.UPDATE_SUCCESS",
                msg=f"仓位数据更新成功: {position_id}",
                extra={
                    "position_id": position_id,
                    "market_id": market_id,
                    "market_question": market.question,
                    "current_price": current_price,
                    "market_closed": market_closed,
                    "market_volume": market.volume,
                    "market_liquidity": market.liquidity
                },
                trace_id=trace_id
            )

            return True

        except Exception as e:
            logger.error(
                "POSITION_MONITOR.UPDATE_ERROR",
                msg=f"更新仓位数据异常: {position_id}",
                error_code="E-PM-007",
                extra={"position_id": position_id, "market_id": market_id, "error": str(e)},
                trace_id=trace_id
            )
            return False


def get_position_market_info(position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    获取仓位关联的市场详细信息

    参数:
        position: 仓位数据字典

    返回:
        dict: 市场详细信息，包含Market对象的所有属性
    """
    market_id = position.get('market_id')
    if not market_id:
        return None

    market = get_market_data(market_id)
    if not market:
        return None

    return {
        "id": market.id,
        "question": market.question,
        "slug": market.slug,
        "outcomes": market.outcomes,
        "outcome_prices": market.outcome_prices,
        "active": market.active,
        "volume": market.volume,
        "liquidity": market.liquidity,
        "end_date": market.end_date,
        "tau": market.tau,
        "tags": market.tags,
        "marks": list(market.marks) if market.marks else [],
        "negRisk": market.negRisk,
        "clobTokenIds": market.clobTokenIds
    }


def batch_get_markets(market_ids: List[str]) -> Dict[str, Market]:
    """
    批量获取市场数据

    参数:
        market_ids: 市场ID列表

    返回:
        dict: market_id -> Market对象的映射
    """
    markets = {}

    with GammaMarketsAPI() as api:
        for market_id in market_ids:
            try:
                market = api.get_market_by_id(market_id)
                if market:
                    markets[market_id] = market
            except Exception as e:
                logger.warn(
                    "POSITION_MONITOR.BATCH_GET_ERROR",
                    msg=f"批量获取市场失败: {market_id}",
                    extra={"market_id": market_id, "error": str(e)}
                )

    logger.info(
        "POSITION_MONITOR.BATCH_GET_COMPLETE",
        msg=f"批量获取市场完成",
        extra={"requested": len(market_ids), "success": len(markets)}
    )

    return markets


def monitor_all_positions() -> Dict[str, Any]:
    """
    监听所有活跃仓位并更新数据
    使用Market对象进行数据更新

    返回:
        dict: 监听结果统计
            - total: 总仓位数
            - success: 成功更新数量
            - failed: 失败数量
            - closed_markets: 已结束市场数量
    """
    with TraceContext() as trace_id:
        logger.info(
            "POSITION_MONITOR.MONITOR_START",
            msg="开始监听所有仓位",
            trace_id=trace_id
        )

        # 获取数据库实例
        db = get_db()

        # 获取所有活跃的仓位
        positions = db.get_positions(is_active=True)

        result = {
            "total": len(positions),
            "success": 0,
            "failed": 0,
            "closed_markets": 0
        }

        logger.info(
            "POSITION_MONITOR.POSITIONS_LOADED",
            msg=f"加载了 {len(positions)} 个活跃仓位",
            extra={"count": len(positions)},
            trace_id=trace_id
        )

        # 遍历更新每个仓位
        for position in positions:
            success = update_position_data(position)

            if success:
                result["success"] += 1

                # 统计已结束的市场
                if position.get('market_closed'):
                    result["closed_markets"] += 1
            else:
                result["failed"] += 1

        logger.info(
            "POSITION_MONITOR.MONITOR_COMPLETE",
            msg="仓位监听完成",
            extra=result,
            trace_id=trace_id
        )

        return result

