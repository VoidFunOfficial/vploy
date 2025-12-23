# -*- coding: utf-8 -*-
"""
市场监控模块

实时监控已交易市场的价格变化和结算状态。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from huey import crontab

from ..task_manager.tasks import huey
from .database import PositionDatabase
from .trade_recorder import TradeRecorder
from .models import Position
from ..polymarket_api import GammaMarketsAPI, PolymarketOrderbookClient
from ..vlogger import TraceContext
from ..sys_configs.global_event_reg import vlogger


class MarketMonitor:
    """
    市场监控器

    监控已交易市场的价格变化和结算状态。
    """

    # 价格涨幅阈值（10%）
    PRICE_SURGE_THRESHOLD = 0.10

    def __init__(
        self,
        db: Optional[PositionDatabase] = None,
        recorder: Optional[TradeRecorder] = None
    ):
        """
        初始化市场监控器

        参数:
            db: PositionDatabase实例
            recorder: TradeRecorder实例
        """
        self.db = db or PositionDatabase()
        self.recorder = recorder or TradeRecorder(self.db)

        vlogger.info(
            "MARKET_MONITOR.INIT",
            msg="市场监控器初始化完成"
        )

    def _handle_price_surge(self, position: Position, price_change_pct: float):
        """
        处理价格涨幅超过阈值的情况

        参数:
            position: Position对象
            price_change_pct: 价格涨跌幅百分比（例如 0.15 表示 15%）

        TODO: 实现具体的价格涨幅处理逻辑，例如：
        - 发送价格预警通知
        - 触发自动止盈/止损策略
        - 记录到专门的价格异动表
        - 调整持仓风险等级
        """
        vlogger.info(
            "MARKET_MONITOR.PRICE_SURGE",
            msg="检测到价格涨幅超过阈值",
            extra={
                "position_id": position.id,
                "market_id": position.market_id,
                "side": position.side,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "price_change_pct": price_change_pct,
                "threshold": self.PRICE_SURGE_THRESHOLD,
                "pnl": position.pnl
            }
        )
    
    def monitor_position(self, position_id: int) -> Dict[str, Any]:
        """
        监控单个持仓的市场状态
        
        参数:
            position_id: 持仓ID
            
        返回:
            Dict[str, Any]: 监控结果
        """
        try:
            position = self.db.get_position(position_id)
            if not position:
                return {
                    "success": False,
                    "message": f"持仓不存在: {position_id}"
                }
            
            # 获取市场信息
            with GammaMarketsAPI() as api:
                try:
                    market = api.get_market_by_id(position.market_id)
                except Exception as e:
                    vlogger.warn(
                        "MARKET_MONITOR.API.ERROR",
                        msg="获取市场信息失败",
                        error_code="E-POSITION-013",
                        extra={
                            "position_id": position_id,
                            "market_id": position.market_id,
                            "error": str(e)
                        }
                    )
                    return {
                        "success": False,
                        "message": f"获取市场信息失败: {str(e)}"
                    }
            
            # 检查市场是否已结算
            if not market.close:
                vlogger.info(
                    "MARKET_MONITOR.SETTLED",
                    msg="市场已结算",
                    extra={
                        "position_id": position_id,
                        "market_id": position.market_id
                    }
                )
                
                # TODO: 获取结算结果并更新持仓
                # 获取Yes方向价格是否为1,否则则为No
                if market.outcome_prices[0] == 1:
                    outcome = "YES"
                else:
                    outcome = "NO"
                if position.side == outcome:
                    settlement_payout = position.shares
                else:
                    settlement_payout = - position.shares * position.entry_price
                self.recorder.settle_position(position_id, outcome, settlement_payout)
                vlogger.info(
                    "MARKET_MONITOR.SETTLED",
                    msg="市场已结算",
                    extra={
                        "position_id": position_id,
                        "market_id": position.market_id,
                        "outcome": outcome,
                        "settlement_payout": settlement_payout
                    }
                )
                
                return {
                    "success": True,
                    "status": "settled",
                    "market_active": False
                }
            
            # 获取当前价格
            try:
                # 解析outcome_prices获取当前价格
                if market.outcome_prices:
                    prices = eval(market.outcome_prices)  # 格式: "['0.52', '0.48']"
                    
                    # 根据side确定使用哪个价格
                    if position.side == "YES":
                        current_price = float(prices[0]) if len(prices) > 0 else position.entry_price
                    else:  # NO
                        current_price = float(prices[1]) if len(prices) > 1 else position.entry_price
                    
                    # 更新持仓价格
                    self.recorder.update_position_price(position_id, current_price)

                    # 计算价格涨跌幅百分比
                    price_change_pct = 0.0
                    if position.entry_price > 0:
                        price_change_pct = (current_price - position.entry_price) / position.entry_price

                    # 检测价格涨幅是否超过阈值
                    if abs(price_change_pct) > self.PRICE_SURGE_THRESHOLD:
                        # 获取更新后的持仓信息
                        updated_position = self.db.get_position(position_id)
                        if updated_position:
                            self._handle_price_surge(updated_position, price_change_pct)

                    vlogger.info(
                        "MARKET_MONITOR.PRICE_UPDATE",
                        msg="更新持仓价格",
                        extra={
                            "position_id": position_id,
                            "market_id": position.market_id,
                            "old_price": position.current_price,
                            "new_price": current_price,
                            "price_change_pct": price_change_pct,
                            "pnl": (current_price - position.entry_price) * position.shares
                        }
                    )

                    return {
                        "success": True,
                        "status": "monitoring",
                        "market_active": True,
                        "current_price": current_price,
                        "price_change": current_price - position.entry_price,
                        "price_change_pct": price_change_pct,
                        "pnl": (current_price - position.entry_price) * position.shares
                    }
                    
            except Exception as e:
                vlogger.error(
                    "MARKET_MONITOR.PRICE.ERROR",
                    msg="更新价格失败",
                    error_code="E-POSITION-014",
                    extra={
                        "position_id": position_id,
                        "error": str(e)
                    }
                )
                return {
                    "success": False,
                    "message": f"更新价格失败: {str(e)}"
                }
            
            return {
                "success": True,
                "status": "monitoring",
                "market_active": True
            }
            
        except Exception as e:
            vlogger.error(
                "MARKET_MONITOR.ERROR",
                msg="监控持仓失败",
                error_code="E-POSITION-015",
                extra={
                    "position_id": position_id,
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "message": f"监控失败: {str(e)}"
            }
    
    def monitor_all_open_positions(self) -> Dict[str, Any]:
        """
        监控所有未平仓的持仓
        
        返回:
            Dict[str, Any]: 监控结果汇总
        """
        try:
            open_positions = self.db.get_open_positions()
            
            results = []
            for position in open_positions:
                result = self.monitor_position(position.id)
                results.append({
                    "position_id": position.id,
                    "market_id": position.market_id,
                    "result": result
                })
            
            vlogger.info(
                "MARKET_MONITOR.ALL",
                msg="监控所有持仓完成",
                extra={
                    "total_positions": len(open_positions),
                    "monitored": len(results)
                }
            )
            
            return {
                "success": True,
                "total_positions": len(open_positions),
                "results": results
            }
            
        except Exception as e:
            vlogger.error(
                "MARKET_MONITOR.ALL.ERROR",
                msg="监控所有持仓失败",
                error_code="E-POSITION-016",
                extra={"error": str(e)}
            )
            return {
                "success": False,
                "message": f"监控失败: {str(e)}"
            }


# ==================== Huey定时任务 ====================

@huey.periodic_task(crontab(minute='*/5'))
def monitor_markets_task():
    """
    定时监控市场任务
    
    每5分钟执行一次，监控所有未平仓持仓的市场状态。
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "MARKET_MONITOR.TASK.START",
            msg="开始定时监控市场",
            trace_id=trace_id
        )
        
        try:
            monitor = MarketMonitor()
            result = monitor.monitor_all_open_positions()
            
            vlogger.info(
                "MARKET_MONITOR.TASK.SUCCESS",
                msg="定时监控市场完成",
                extra=result,
                trace_id=trace_id
            )
            
        except Exception as e:
            vlogger.error(
                "MARKET_MONITOR.TASK.ERROR",
                msg="定时监控市场失败",
                error_code="E-POSITION-017",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.task()
def monitor_position_task(position_id: int):
    """
    监控单个持仓的Huey任务
    
    参数:
        position_id: 持仓ID
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "MARKET_MONITOR.POSITION_TASK.START",
            msg=f"开始监控持仓: {position_id}",
            extra={"position_id": position_id},
            trace_id=trace_id
        )
        
        try:
            monitor = MarketMonitor()
            result = monitor.monitor_position(position_id)
            
            vlogger.info(
                "MARKET_MONITOR.POSITION_TASK.SUCCESS",
                msg=f"监控持仓完成: {position_id}",
                extra={"position_id": position_id, "result": result},
                trace_id=trace_id
            )
            
            return result
            
        except Exception as e:
            vlogger.error(
                "MARKET_MONITOR.POSITION_TASK.ERROR",
                msg=f"监控持仓失败: {position_id}",
                error_code="E-POSITION-018",
                extra={"position_id": position_id, "error": str(e)},
                trace_id=trace_id
            )
            raise

