"""
止盈监控集成模块

将止盈系统与持仓监听模块集成，实现自动化监控和执行。
"""

from typing import Dict, Any, Optional
from datetime import datetime
from huey import crontab

from ..task_manager.tasks import huey
from ..position_listener.database import PositionDatabase
from ..position_listener.market_monitor import MarketMonitor
from .auto_surplus import auto_surplus_decision, auto_surplus_all_positions
from ..vlogger import TraceContext
from ..sys_configs.global_event_reg import vlogger


class SurplusMonitor:
    """
    止盈监控器
    
    集成市场监控和止盈决策，实现自动化止盈。
    """
    
    def __init__(
        self,
        db: Optional[PositionDatabase] = None,
        market_monitor: Optional[MarketMonitor] = None
    ):
        """
        初始化止盈监控器
        
        参数:
            db: PositionDatabase实例
            market_monitor: MarketMonitor实例
        """
        self.db = db or PositionDatabase()
        self.market_monitor = market_monitor or MarketMonitor(self.db)
        
        vlogger.info(
            "SURPLUS.MONITOR.INIT",
            msg="止盈监控器初始化完成"
        )
    
    def monitor_position_with_surplus(
        self,
        position_id: int,
        execute_sell: bool = False
    ) -> Dict[str, Any]:
        """
        监控单个持仓并执行止盈检查
        
        参数:
            position_id: 持仓ID
            execute_sell: 是否执行卖出操作
            
        返回:
            监控和决策结果
        """
        try:
            # 1. 更新市场价格
            market_result = self.market_monitor.monitor_position(position_id)
            
            if not market_result.get('success'):
                return market_result
            
            # 2. 如果市场已结算，跳过止盈检查
            if market_result.get('status') == 'settled':
                return {
                    "success": True,
                    "status": "settled",
                    "message": "市场已结算，无需止盈检查"
                }
            
            # 3. 获取持仓信息
            position = self.db.get_position(position_id)
            if not position:
                return {
                    "success": False,
                    "message": f"持仓不存在: {position_id}"
                }
            
            # 4. 获取token_id
            token_id = position.metadata.get('token_id')
            if not token_id:
                vlogger.warn(
                    "SURPLUS.MONITOR.NO_TOKEN_ID",
                    msg="持仓缺少token_id，跳过止盈检查",
                    extra={"position_id": position_id}
                )
                return {
                    "success": True,
                    "status": "skipped",
                    "message": "缺少token_id"
                }
            
            # 5. 执行止盈决策
            surplus_result = auto_surplus_decision(
                position_id=position_id,
                token_id=token_id,
                execute=execute_sell
            )
            
            # 6. 合并结果
            return {
                "success": True,
                "position_id": position_id,
                "market_update": market_result,
                "surplus_decision": surplus_result
            }
            
        except Exception as e:
            vlogger.error(
                "SURPLUS.MONITOR.POSITION.ERROR",
                msg="监控持仓失败",
                error_code="E-SURPLUS-007",
                extra={
                    "position_id": position_id,
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "message": f"监控失败: {str(e)}"
            }
    
    def monitor_all_positions_with_surplus(
        self,
        execute_sell: bool = False
    ) -> Dict[str, Any]:
        """
        监控所有持仓并执行止盈检查
        
        参数:
            execute_sell: 是否执行卖出操作
            
        返回:
            汇总结果
        """
        try:
            open_positions = self.db.get_open_positions()
            
            vlogger.info(
                "SURPLUS.MONITOR.ALL.START",
                msg="开始批量监控和止盈检查",
                extra={
                    "total_positions": len(open_positions),
                    "execute_sell": execute_sell
                }
            )
            
            results = []
            sell_count = 0
            
            for position in open_positions:
                result = self.monitor_position_with_surplus(
                    position_id=position.id,
                    execute_sell=execute_sell
                )
                results.append(result)
                
                # 统计卖出信号
                surplus_decision = result.get('surplus_decision', {})
                if surplus_decision.get('decision', {}).get('action') == 'SELL':
                    sell_count += 1

            vlogger.info(
                "SURPLUS.MONITOR.ALL.COMPLETE",
                msg="批量监控和止盈检查完成",
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
                "SURPLUS.MONITOR.ALL.ERROR",
                msg="批量监控和止盈检查失败",
                error_code="E-SURPLUS-008",
                extra={"error": str(e)}
            )
            return {
                "success": False,
                "message": f"批量监控失败: {str(e)}"
            }


# ==================== Huey定时任务 ====================

@huey.periodic_task(crontab(minute='*/10'))
def surplus_monitor_task():
    """
    定时止盈监控任务

    每10分钟执行一次，监控所有持仓并执行止盈检查。
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "SURPLUS.MONITOR.TASK.START",
            msg="开始定时止盈监控",
            trace_id=trace_id
        )

        try:
            monitor = SurplusMonitor()
            result = monitor.monitor_all_positions_with_surplus(
                execute_sell=True  # 自动执行卖出
            )

            vlogger.info(
                "SURPLUS.MONITOR.TASK.SUCCESS",
                msg="定时止盈监控完成",
                extra=result,
                trace_id=trace_id
            )

        except Exception as e:
            vlogger.error(
                "SURPLUS.MONITOR.TASK.ERROR",
                msg="定时止盈监控失败",
                error_code="E-SURPLUS-009",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.task()
def surplus_monitor_position_task(position_id: int, execute_sell: bool = False):
    """
    监控单个持仓的Huey任务

    参数:
        position_id: 持仓ID
        execute_sell: 是否执行卖出操作
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "SURPLUS.MONITOR.POSITION_TASK.START",
            msg=f"开始监控持仓: {position_id}",
            extra={
                "position_id": position_id,
                "execute_sell": execute_sell
            },
            trace_id=trace_id
        )

        try:
            monitor = SurplusMonitor()
            result = monitor.monitor_position_with_surplus(
                position_id=position_id,
                execute_sell=execute_sell
            )

            vlogger.info(
                "SURPLUS.MONITOR.POSITION_TASK.SUCCESS",
                msg=f"监控持仓完成: {position_id}",
                extra={
                    "position_id": position_id,
                    "result": result
                },
                trace_id=trace_id
            )

            return result

        except Exception as e:
            vlogger.error(
                "SURPLUS.MONITOR.POSITION_TASK.ERROR",
                msg=f"监控持仓失败: {position_id}",
                error_code="E-SURPLUS-010",
                extra={
                    "position_id": position_id,
                    "error": str(e)
                },
                trace_id=trace_id
            )
            raise

