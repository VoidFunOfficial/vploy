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
from ..record import RecordManager
from ..purse import get_purse


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
        self.record_manager = RecordManager()

        vlogger.info(
            "MARKET_MONITOR.INIT",
            msg="市场监控器初始化完成"
        )

    def _get_market_end_date(self, market_id: str) -> Optional[str]:
        """
        获取市场的结算日期

        参数:
            market_id: 市场ID

        返回:
            str: 结算日期 (yyyy-mm-dd)，如果获取失败返回None
        """
        try:
            with GammaMarketsAPI() as api:
                market = api.get_market(market_id)
                if market and market.end_date:
                    # 将ISO格式转换为 yyyy-mm-dd
                    end_date = datetime.fromisoformat(market.end_date.replace('Z', '+00:00'))
                    return end_date.strftime('%Y-%m-%d')
                else:
                    vlogger.warn(
                        "MARKET_MONITOR.END_DATE.NOT_FOUND",
                        msg="市场没有结算日期",
                        extra={"market_id": market_id}
                    )
                    return None
        except Exception as e:
            vlogger.error(
                "MARKET_MONITOR.END_DATE.ERROR",
                msg="获取市场结算日期失败",
                error_code="E-POSITION-035",
                extra={"market_id": market_id, "error": str(e)}
            )
            return None

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
                    "MARKET_MONITOR.SETTLE.START",
                    msg="检测到市场已结算",
                    extra={
                        "position_id": position_id,
                        "market_id": position.market_id
                    }
                )

                # 获取结算结果
                # 获取Yes方向价格是否为1,否则则为No
                if market.outcome_prices[0] == 1:
                    outcome = "YES"
                    final_price = 1.0
                else:
                    outcome = "NO"
                    final_price = 1.0

                # 计算结算收益
                if position.side == outcome:
                    # 赢了: 获得全部份额价值
                    settlement_payout = position.shares
                else:
                    # 输了: 损失投入成本
                    settlement_payout = - position.shares * position.entry_price

                # 1. 更新 position_listener 的持仓状态
                self.recorder.settle_position(position_id, outcome, settlement_payout)

                # 2. 记录到 record 模块
                try:
                    end_date = datatime.fromisoformat(market.end_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    if end_date:
                        self.record_manager.update_info(
                            market_id=position.market_id,
                            side=position.side,
                            end_date=end_date,
                            operation='SETTLE',
                            price=final_price,
                            amount=position.shares,
                            tips=f"市场结算 (position_id: {position_id}, outcome: {outcome})"
                        )
                        vlogger.info(
                            "MARKET_MONITOR.SETTLE.RECORD_SUCCESS",
                            msg="成功记录到record模块",
                            extra={
                                "position_id": position_id,
                                "market_id": position.market_id,
                                "outcome": outcome
                            }
                        )
                    else:
                        vlogger.warn(
                            "MARKET_MONITOR.SETTLE.NO_END_DATE",
                            msg="无法获取结算日期，跳过记录到record模块",
                            extra={"market_id": position.market_id}
                        )
                except Exception as e:
                    vlogger.error(
                        "MARKET_MONITOR.SETTLE.RECORD_ERROR",
                        msg="记录到record模块失败",
                        error_code="E-POSITION-036",
                        extra={
                            "position_id": position_id,
                            "error": str(e)
                        }
                    )

                # 3. 使用 purse 结算资金
                try:
                    purse = get_purse()

                    if settlement_payout > 0:
                        # 盈利: 解锁本金并记录盈利
                        profit = settlement_payout - position.invest_amount
                        purse.record_profit(
                            amount=profit,
                            unlock_amount=position.invest_amount
                        )
                        vlogger.info(
                            "MARKET_MONITOR.SETTLE.PROFIT",
                            msg="记录盈利并解锁资金",
                            extra={
                                "position_id": position_id,
                                "profit": profit,
                                "unlock_amount": position.invest_amount
                            }
                        )
                    else:
                        # 亏损: 记录亏损并解锁剩余资金
                        loss = abs(settlement_payout)
                        remaining = position.invest_amount - loss
                        purse.record_loss(
                            amount=loss,
                            unlock_amount=remaining
                        )
                        vlogger.info(
                            "MARKET_MONITOR.SETTLE.LOSS",
                            msg="记录亏损并解锁资金",
                            extra={
                                "position_id": position_id,
                                "loss": loss,
                                "unlock_amount": remaining
                            }
                        )
                except Exception as e:
                    vlogger.error(
                        "MARKET_MONITOR.SETTLE.PURSE_ERROR",
                        msg="purse资金结算失败",
                        error_code="E-POSITION-037",
                        extra={
                            "position_id": position_id,
                            "error": str(e)
                        }
                    )

                vlogger.trade(
                    "MARKET_MONITOR.SETTLED",
                    msg="市场结算完成",
                    extra={
                        "position_id": position_id,
                        "market_id": position.market_id,
                        "outcome": outcome,
                        "settlement_payout": settlement_payout,
                        "pnl": settlement_payout - position.invest_amount
                    }
                )

                return {
                    "success": True,
                    "status": "settled",
                    "market_active": False,
                    "outcome": outcome,
                    "settlement_payout": settlement_payout
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

