# -*- coding: utf-8 -*-
"""
订单状态监控模块

监控订单的成交和撤销状态。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from huey import crontab

from ..task_manager.tasks import huey
from .database import PositionDatabase
from .models import OrderStatus
from ..polymarket_api import get_order, get_orders, GammaMarketsAPI
from ..vlogger import TraceContext
from ..sys_configs.global_event_reg import vlogger
from ..record import RecordManager


class OrderMonitor:
    """
    订单监控器
    
    监控订单的成交和撤销状态。
    """
    
    def __init__(self, db: Optional[PositionDatabase] = None):
        """
        初始化订单监控器

        参数:
            db: PositionDatabase实例
        """
        self.db = db or PositionDatabase()
        self.record_manager = RecordManager()

        vlogger.info(
            "ORDER_MONITOR.INIT",
            msg="订单监控器初始化完成"
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
                if market and market.end_date_iso:
                    # 将ISO格式转换为 yyyy-mm-dd
                    end_date = datetime.fromisoformat(market.end_date_iso.replace('Z', '+00:00'))
                    return end_date.strftime('%Y-%m-%d')
                else:
                    vlogger.warn(
                        "ORDER_MONITOR.END_DATE.NOT_FOUND",
                        msg="市场没有结算日期",
                        extra={"market_id": market_id}
                    )
                    return None
        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.END_DATE.ERROR",
                msg="获取市场结算日期失败",
                error_code="E-POSITION-033",
                extra={"market_id": market_id, "error": str(e)}
            )
            return None

    def _record_trade_to_record_module(
        self,
        position_id: int,
        market_id: str,
        filled_size: float,
        price: float
    ):
        """
        将成交信息记录到 record 模块

        参数:
            position_id: 持仓ID
            market_id: 市场ID
            filled_size: 成交数量
            price: 成交价格
        """
        try:
            # 获取持仓信息
            position = self.db.get_position(position_id)
            if not position:
                vlogger.warn(
                    "ORDER_MONITOR.RECORD.NO_POSITION",
                    msg="持仓不存在，无法记录到record模块",
                    extra={"position_id": position_id}
                )
                return

            # 获取市场结算日期
            end_date = self._get_market_end_date(market_id)
            if not end_date:
                vlogger.warn(
                    "ORDER_MONITOR.RECORD.NO_END_DATE",
                    msg="无法获取市场结算日期，跳过记录到record模块",
                    extra={"market_id": market_id}
                )
                return

            # 记录到 record 模块
            self.record_manager.update_info(
                market_id=market_id,
                side=position.side,
                end_date=end_date,
                operation='BUY',
                price=price,
                amount=filled_size,
                tips=f"订单成交自动记录 (position_id: {position_id})"
            )

            vlogger.info(
                "ORDER_MONITOR.RECORD.SUCCESS",
                msg="成交信息已记录到record模块",
                extra={
                    "position_id": position_id,
                    "market_id": market_id,
                    "side": position.side,
                    "amount": filled_size,
                    "price": price
                }
            )

        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.RECORD.ERROR",
                msg="记录到record模块失败",
                error_code="E-POSITION-034",
                extra={
                    "position_id": position_id,
                    "market_id": market_id,
                    "error": str(e)
                }
            )

    def _handle_order_cancelled(self, order, filled_size: float, original_size: float):
        """
        处理订单取消：解锁资金和更新任务状态

        参数:
            order: Order对象
            filled_size: 已成交数量
            original_size: 原始订单数量
        """
        from ..purse import get_purse
        from ..task_manager.models import TaskDatabase, TaskStage, TaskStatus
        from datetime import datetime

        try:
            # 获取关联的持仓信息
            position = self.db.get_position(order.position_id)
            if not position:
                vlogger.warn(
                    "ORDER_MONITOR.CANCEL.NO_POSITION",
                    msg="订单关联的持仓不存在",
                    extra={
                        "order_id": order.order_id,
                        "position_id": order.position_id
                    }
                )
                return

            # 如果有部分成交，更新持仓份额
            if filled_size > 0:
                previous_filled = order.filled_size or 0.0
                new_filled = filled_size - previous_filled

                if new_filled > 0:
                    self.db.update_position_shares(order.position_id, new_filled)
                    vlogger.info(
                        "ORDER_MONITOR.CANCEL.UPDATE_SHARES",
                        msg="订单取消前部分成交，已更新持仓份额",
                        extra={
                            "order_id": order.order_id,
                            "position_id": order.position_id,
                            "filled_size": filled_size,
                            "new_filled": new_filled
                        }
                    )

            # 计算需要解锁的资金
            if filled_size == 0.0:
                # 完全未成交，解锁全部投资金额
                unlock_amount = position.invest_amount
            else:
                # 部分成交，只解锁未成交部分
                unfilled_ratio = (original_size - filled_size) / original_size if original_size > 0 else 0
                unlock_amount = position.invest_amount * unfilled_ratio

            # 解锁资金
            if unlock_amount > 0:
                purse = get_purse()
                success = purse.unlock_fund(unlock_amount)

                if success:
                    vlogger.trade(
                        "ORDER_MONITOR.CANCEL.UNLOCK_SUCCESS",
                        msg="订单取消，资金解锁成功",
                        extra={
                            "order_id": order.order_id,
                            "position_id": position.id,
                            "market_id": position.market_id,
                            "invest_amount": position.invest_amount,
                            "unlock_amount": unlock_amount,
                            "filled_size": filled_size,
                            "original_size": original_size
                        }
                    )
                else:
                    vlogger.error(
                        "ORDER_MONITOR.CANCEL.UNLOCK_FAILED",
                        msg="订单取消，资金解锁失败",
                        error_code="E-POSITION-024",
                        extra={
                            "order_id": order.order_id,
                            "position_id": position.id,
                            "unlock_amount": unlock_amount
                        }
                    )

            # 更新关联任务状态
            if order.metadata and "task_id" in order.metadata:
                task_id = order.metadata["task_id"]
                task_db = TaskDatabase()
                task = task_db.get_async_task(task_id)

                if task and task.stage == TaskStage.LISTEN and task.status == TaskStatus.PROCESSING:
                    # 在task.result中添加订单取消信息
                    task.result["order_cancelled"] = True
                    task.result["order_cancelled_time"] = datetime.now().isoformat()
                    task.result["filled_size"] = filled_size
                    task.result["original_size"] = original_size
                    task.result["unlock_amount"] = unlock_amount

                    # 更新任务到数据库
                    task_db.update_async_task(task)

                    vlogger.info(
                        "ORDER_MONITOR.CANCEL.TASK_UPDATED",
                        msg="订单取消，任务状态已更新",
                        extra={
                            "order_id": order.order_id,
                            "task_id": task_id,
                            "stage": task.stage.value,
                            "status": task.status.value
                        }
                    )
                elif task:
                    vlogger.info(
                        "ORDER_MONITOR.CANCEL.TASK_SKIP",
                        msg="任务不在LISTEN/PROCESSING阶段，跳过更新",
                        extra={
                            "order_id": order.order_id,
                            "task_id": task_id,
                            "stage": task.stage.value,
                            "status": task.status.value
                        }
                    )
                else:
                    vlogger.warn(
                        "ORDER_MONITOR.CANCEL.TASK_NOT_FOUND",
                        msg="订单关联的任务不存在",
                        extra={
                            "order_id": order.order_id,
                            "task_id": task_id
                        }
                    )

        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.CANCEL.HANDLE_ERROR",
                msg="处理订单取消失败",
                error_code="E-POSITION-025",
                extra={
                    "order_id": order.order_id,
                    "error": str(e)
                }
            )
    
    def monitor_order(self, order_id: str) -> Dict[str, Any]:
        """
        监控单个订单状态
        
        参数:
            order_id: 订单ID
            
        返回:
            Dict[str, Any]: 监控结果
        """
        try:
            # 从数据库获取订单记录
            order = self.db.get_order_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "message": f"订单记录不存在: {order_id}"
                }
            
            # 如果订单已经是终态，不需要再查询
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
                return {
                    "success": True,
                    "status": order.status.value,
                    "message": "订单已处于终态"
                }
            
            # 从CLOB API查询订单状态
            try:
                clob_order = get_order(order_id)
            except Exception as e:
                vlogger.warn(
                    "ORDER_MONITOR.API.ERROR",
                    msg="查询订单状态失败",
                    error_code="E-POSITION-019",
                    extra={
                        "order_id": order_id,
                        "error": str(e)
                    }
                )
                return {
                    "success": False,
                    "message": f"查询订单状态失败: {str(e)}"
                }

            # 检查API返回结果是否有效
            if clob_order is None:
                vlogger.warn(
                    "ORDER_MONITOR.API.NULL_RESPONSE",
                    msg="API返回空结果，订单可能不存在或已被删除",
                    error_code="E-POSITION-028",
                    extra={"order_id": order_id}
                )

                # 自动删除不存在的订单记录
                try:
                    deleted = self.db.delete_order(order_id)
                    if deleted:
                        vlogger.info(
                            "ORDER_MONITOR.AUTO_DELETE",
                            msg="订单不存在，已自动删除订单记录",
                            extra={"order_id": order_id}
                        )
                except Exception as e:
                    vlogger.error(
                        "ORDER_MONITOR.AUTO_DELETE.ERROR",
                        msg="自动删除订单记录失败",
                        error_code="E-POSITION-030",
                        extra={"order_id": order_id, "error": str(e)}
                    )

                return {
                    "success": False,
                    "message": "API返回空结果，订单可能不存在或已被删除",
                    "order_deleted": True
                }

            # 解析订单状态
            clob_status = clob_order.get("status", "").upper()
            original_size = float(clob_order.get("original_size", 0))
            size_matched = float(clob_order.get("size_matched", 0))
            
            # 更新订单状态
            new_status = None
            
            if clob_status == "MATCHED" or size_matched >= original_size:
                # 订单已完全成交
                new_status = OrderStatus.FILLED

                # 计算新增成交量（当前成交量 - 之前已记录的成交量）
                previous_filled = order.filled_size or 0.0
                new_filled = size_matched - previous_filled

                self.db.update_order_status(order_id, new_status, filled_size=size_matched)

                # 如果有新增成交，更新持仓份额并记录到record模块
                if new_filled > 0 and order.position_id:
                    self.db.update_position_shares(order.position_id, new_filled)
                    # 记录到 record 模块
                    self._record_trade_to_record_module(
                        position_id=order.position_id,
                        market_id=order.market_id,
                        filled_size=new_filled,
                        price=order.price
                    )

                vlogger.trade(
                    "ORDER_MONITOR.FILLED",
                    msg="订单已成交",
                    extra={
                        "order_id": order_id,
                        "position_id": order.position_id,
                        "size": original_size,
                        "filled_size": size_matched,
                        "new_filled": new_filled
                    }
                )
                
            elif clob_status == "CANCELLED":
                # 订单已撤销
                new_status = OrderStatus.CANCELLED
                self.db.update_order_status(order_id, new_status, filled_size=size_matched)

                # 处理订单取消：解锁资金和更新任务状态
                self._handle_order_cancelled(order, size_matched, original_size)

                vlogger.info(
                    "ORDER_MONITOR.CANCELLED",
                    msg="订单已撤销",
                    extra={
                        "order_id": order_id,
                        "size": original_size,
                        "filled_size": size_matched
                    }
                )
                
            elif size_matched > 0:
                # 订单部分成交
                # 计算新增成交量（当前成交量 - 之前已记录的成交量）
                previous_filled = order.filled_size or 0.0
                new_filled = size_matched - previous_filled

                self.db.update_order_status(order_id, OrderStatus.PENDING, filled_size=size_matched)

                # 如果有新增成交，更新持仓份额并记录到record模块
                if new_filled > 0 and order.position_id:
                    self.db.update_position_shares(order.position_id, new_filled)
                    # 记录到 record 模块
                    self._record_trade_to_record_module(
                        position_id=order.position_id,
                        market_id=order.market_id,
                        filled_size=new_filled,
                        price=order.price
                    )

                vlogger.info(
                    "ORDER_MONITOR.PARTIAL",
                    msg="订单部分成交",
                    extra={
                        "order_id": order_id,
                        "position_id": order.position_id,
                        "size": original_size,
                        "filled_size": size_matched,
                        "new_filled": new_filled,
                        "fill_rate": size_matched / original_size if original_size > 0 else 0
                    }
                )
            
            return {
                "success": True,
                "status": new_status.value if new_status else order.status.value,
                "clob_status": clob_status,
                "original_size": original_size,
                "filled_size": size_matched,
                "fill_rate": size_matched / original_size if original_size > 0 else 0
            }
            
        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.ERROR",
                msg="监控订单失败",
                error_code="E-POSITION-020",
                extra={
                    "order_id": order_id,
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "message": f"监控失败: {str(e)}"
            }
    
    def monitor_all_pending_orders(self) -> Dict[str, Any]:
        """
        监控所有待成交的订单

        返回:
            Dict[str, Any]: 监控结果汇总
        """
        try:
            pending_orders = self.db.get_pending_orders()

            results = []
            for order in pending_orders:
                result = self.monitor_order(order.order_id)
                results.append({
                    "order_id": order.order_id,
                    "market_id": order.market_id,
                    "result": result
                })

            vlogger.info(
                "ORDER_MONITOR.ALL",
                msg="监控所有待成交订单完成",
                extra={
                    "total_orders": len(pending_orders),
                    "monitored": len(results)
                }
            )

            return {
                "success": True,
                "total_orders": len(pending_orders),
                "results": results
            }

        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.ALL.ERROR",
                msg="监控所有订单失败",
                error_code="E-POSITION-021",
                extra={"error": str(e)}
            )
            return {
                "success": False,
                "message": f"监控失败: {str(e)}"
            }

    def process_monitor_results(self, monitor_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理批量监控结果，更新订单状态、任务状态和purse

        参数:
            monitor_results: 监控结果列表，格式为:
                [
                    {
                        "order_id": "0x...",
                        "market_id": "916391",
                        "result": {
                            "success": True,
                            "status": "pending",
                            "clob_status": "LIVE",
                            "original_size": 34.0,
                            "filled_size": 0.0,
                            "fill_rate": 0.0
                        }
                    },
                    ...
                ]

        返回:
            Dict[str, Any]: 处理结果汇总
        """
        from ..purse import get_purse
        from ..task_manager.models import TaskDatabase, TaskStage, TaskStatus
        from datetime import datetime

        try:
            processed_count = 0
            cancelled_count = 0
            filled_count = 0
            live_count = 0
            error_count = 0
            total_unlocked = 0.0

            purse = get_purse()
            task_db = TaskDatabase()

            for item in monitor_results:
                order_id = item.get("order_id")
                market_id = item.get("market_id")
                result = item.get("result", {})

                if not result.get("success"):
                    error_count += 1
                    vlogger.warn(
                        "ORDER_MONITOR.PROCESS.SKIP",
                        msg="跳过失败的监控结果",
                        extra={"order_id": order_id, "result": result}
                    )
                    continue

                clob_status = result.get("clob_status", "").upper()
                original_size = result.get("original_size", 0.0)
                filled_size = result.get("filled_size", 0.0)
                fill_rate = result.get("fill_rate", 0.0)

                # 获取订单记录
                order = self.db.get_order_by_id(order_id)
                if not order:
                    vlogger.warn(
                        "ORDER_MONITOR.PROCESS.NO_ORDER",
                        msg="订单记录不存在",
                        extra={"order_id": order_id}
                    )
                    error_count += 1
                    continue

                # 处理CANCELLED状态
                if clob_status == "CANCELED" or clob_status == "CANCELLED":
                    # 如果有部分成交，更新持仓份额
                    if filled_size > 0:
                        previous_filled = order.filled_size or 0.0
                        new_filled = filled_size - previous_filled

                        if new_filled > 0 and order.position_id:
                            self.db.update_position_shares(order.position_id, new_filled)

                    # 更新订单状态
                    self.db.update_order_status(order_id, OrderStatus.CANCELLED, filled_size=filled_size)

                    # 获取关联的持仓信息
                    position = self.db.get_position(order.position_id)
                    if position:
                        # 计算需要解锁的资金
                        if filled_size == 0.0:
                            unlock_amount = position.invest_amount
                        else:
                            unfilled_ratio = (original_size - filled_size) / original_size if original_size > 0 else 0
                            unlock_amount = position.invest_amount * unfilled_ratio

                        # 解锁资金
                        if unlock_amount > 0:
                            success = purse.unlock_fund(unlock_amount)
                            if success:
                                total_unlocked += unlock_amount
                                vlogger.trade(
                                    "ORDER_MONITOR.PROCESS.UNLOCK",
                                    msg="订单取消，资金解锁成功",
                                    extra={
                                        "order_id": order_id,
                                        "market_id": market_id,
                                        "unlock_amount": unlock_amount,
                                        "filled_size": filled_size,
                                        "original_size": original_size
                                    }
                                )
                            else:
                                vlogger.error(
                                    "ORDER_MONITOR.PROCESS.UNLOCK_FAILED",
                                    msg="资金解锁失败",
                                    error_code="E-POSITION-026",
                                    extra={"order_id": order_id, "unlock_amount": unlock_amount}
                                )

                        # 更新关联任务状态
                        if order.metadata and "task_id" in order.metadata:
                            task_id = order.metadata["task_id"]
                            task = task_db.get_async_task(task_id)

                            if task and task.stage == TaskStage.LISTEN and task.status == TaskStatus.PROCESSING:
                                task.result["order_cancelled"] = True
                                task.result["order_cancelled_time"] = datetime.now().isoformat()
                                task.result["filled_size"] = filled_size
                                task.result["original_size"] = original_size
                                task.result["unlock_amount"] = unlock_amount
                                task_db.update_async_task(task)

                                vlogger.info(
                                    "ORDER_MONITOR.PROCESS.TASK_UPDATED",
                                    msg="任务状态已更新",
                                    extra={"order_id": order_id, "task_id": task_id}
                                )

                    cancelled_count += 1

                # 处理FILLED/MATCHED状态
                elif clob_status == "MATCHED" or fill_rate >= 1.0:
                    # 计算新增成交量
                    previous_filled = order.filled_size or 0.0
                    new_filled = filled_size - previous_filled

                    self.db.update_order_status(order_id, OrderStatus.FILLED, filled_size=filled_size)

                    # 如果有新增成交，更新持仓份额并记录到record模块
                    if new_filled > 0 and order.position_id:
                        self.db.update_position_shares(order.position_id, new_filled)
                        # 记录到 record 模块
                        self._record_trade_to_record_module(
                            position_id=order.position_id,
                            market_id=market_id,
                            filled_size=new_filled,
                            price=order.price
                        )

                    filled_count += 1

                    vlogger.trade(
                        "ORDER_MONITOR.PROCESS.FILLED",
                        msg="订单已成交",
                        extra={
                            "order_id": order_id,
                            "position_id": order.position_id,
                            "market_id": market_id,
                            "filled_size": filled_size,
                            "new_filled": new_filled,
                            "original_size": original_size
                        }
                    )

                # 处理LIVE/PENDING状态
                elif clob_status == "LIVE":
                    if filled_size > 0:
                        # 计算新增成交量
                        previous_filled = order.filled_size or 0.0
                        new_filled = filled_size - previous_filled

                        self.db.update_order_status(order_id, OrderStatus.PENDING, filled_size=filled_size)

                        # 如果有新增成交，更新持仓份额并记录到record模块
                        if new_filled > 0 and order.position_id:
                            self.db.update_position_shares(order.position_id, new_filled)
                            # 记录到 record 模块
                            self._record_trade_to_record_module(
                                position_id=order.position_id,
                                market_id=market_id,
                                filled_size=new_filled,
                                price=order.price
                            )
                    live_count += 1

                processed_count += 1

            summary = {
                "success": True,
                "total_processed": processed_count,
                "cancelled_count": cancelled_count,
                "filled_count": filled_count,
                "live_count": live_count,
                "error_count": error_count,
                "total_unlocked": total_unlocked
            }

            vlogger.info(
                "ORDER_MONITOR.PROCESS.COMPLETE",
                msg="批量处理监控结果完成",
                extra=summary
            )

            return summary

        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.PROCESS.ERROR",
                msg="处理监控结果失败",
                error_code="E-POSITION-027",
                extra={"error": str(e)}
            )
            return {
                "success": False,
                "message": f"处理失败: {str(e)}"
            }


# ==================== Huey定时任务 ====================

@huey.periodic_task(crontab(minute='*/2'))
def monitor_orders_task():
    """
    定时监控订单任务

    每2分钟执行一次，监控所有待成交订单的状态，并自动处理监控结果。
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "ORDER_MONITOR.TASK.START",
            msg="开始定时监控订单",
            trace_id=trace_id
        )

        try:
            monitor = OrderMonitor()

            # 监控所有待成交订单
            result = monitor.monitor_all_pending_orders()

            vlogger.info(
                "ORDER_MONITOR.TASK.MONITOR_COMPLETE",
                msg="订单监控完成",
                extra=result,
                trace_id=trace_id
            )

            # 自动处理监控结果
            if result.get("success") and result.get("results"):
                process_result = monitor.process_monitor_results(result["results"])

                vlogger.info(
                    "ORDER_MONITOR.TASK.SUCCESS",
                    msg="定时监控订单完成，已自动处理结果",
                    extra={
                        "monitor_result": result,
                        "process_result": process_result
                    },
                    trace_id=trace_id
                )
            else:
                vlogger.info(
                    "ORDER_MONITOR.TASK.SUCCESS",
                    msg="定时监控订单完成，无需处理",
                    extra=result,
                    trace_id=trace_id
                )

        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.TASK.ERROR",
                msg="定时监控订单失败",
                error_code="E-POSITION-022",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.task()
def monitor_order_task(order_id: str):
    """
    监控单个订单的Huey任务
    
    参数:
        order_id: 订单ID
    """
    with TraceContext() as trace_id:
        vlogger.info(
            "ORDER_MONITOR.ORDER_TASK.START",
            msg=f"开始监控订单: {order_id}",
            extra={"order_id": order_id},
            trace_id=trace_id
        )
        
        try:
            monitor = OrderMonitor()
            result = monitor.monitor_order(order_id)
            
            vlogger.info(
                "ORDER_MONITOR.ORDER_TASK.SUCCESS",
                msg=f"监控订单完成: {order_id}",
                extra={"order_id": order_id, "result": result},
                trace_id=trace_id
            )
            
            return result
            
        except Exception as e:
            vlogger.error(
                "ORDER_MONITOR.ORDER_TASK.ERROR",
                msg=f"监控订单失败: {order_id}",
                error_code="E-POSITION-023",
                extra={"order_id": order_id, "error": str(e)},
                trace_id=trace_id
            )
            raise

