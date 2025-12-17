# -*- coding: utf-8 -*-
"""
交易记录模块

根据TradeAllocation数据结构记录交易信息到数据库。
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .database import PositionDatabase
from .models import Position, Trade, Order, PositionStatus, OrderStatus
from ..types import TradeAllocation
from ..sys_configs.global_event_reg import vlogger


class TradeRecorder:
    """
    交易记录器
    
    负责根据TradeAllocation记录交易信息到数据库。
    """
    
    def __init__(self, db: Optional[PositionDatabase] = None):
        """
        初始化交易记录器
        
        参数:
            db: PositionDatabase实例，如果为None则创建新实例
        """
        self.db = db or PositionDatabase()
        
        vlogger.info(
            "TRADE_RECORDER.INIT",
            msg="交易记录器初始化完成"
        )
    
    def record_trade_allocation(
        self,
        allocation: TradeAllocation,
        order_id: Optional[str] = None,
        token_id: Optional[str] = None,
        task_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        根据TradeAllocation记录交易

        参数:
            allocation: TradeAllocation对象
            order_id: 订单ID（可选）
            token_id: Token ID（可选）
            task_metadata: 任务元信息（可选），包含analysis、market、marks、source_analysis_task_id等

        返回:
            int: 创建的持仓ID
        """
        try:
            # 构建持仓metadata
            position_metadata = {
                "subjective_probability": allocation.p,
                "odds": allocation.b,
                "position_fraction": allocation.f
            }

            # 如果提供了任务元信息，添加到metadata中
            if task_metadata:
                # 添加analysis信息（概率、理由等）
                if "analysis" in task_metadata:
                    position_metadata["analysis"] = task_metadata["analysis"]

                # 添加market信息（问题、结算日期等）
                if "market" in task_metadata:
                    position_metadata["market"] = task_metadata["market"]

                # 添加marks标签
                if "marks" in task_metadata:
                    position_metadata["marks"] = task_metadata["marks"]

                # 添加源分析任务ID
                if "source_analysis_task_id" in task_metadata:
                    position_metadata["source_analysis_task_id"] = task_metadata["source_analysis_task_id"]

            # 创建持仓记录
            position = Position(
                market_id=str(allocation.id),
                side=allocation.side,
                entry_price=allocation.price,
                shares=allocation.shares,
                invest_amount=allocation.invest,
                settle_day=allocation.settle_day,
                status=PositionStatus.OPEN,
                current_price=allocation.price,
                pnl=0.0,
                metadata=position_metadata
            )
            
            position_id = self.db.create_position(position)
            
            # 创建交易记录
            trade = Trade(
                position_id=position_id,
                market_id=str(allocation.id),
                side=allocation.side,
                price=allocation.price,
                shares=allocation.shares,
                amount=allocation.invest,
                trade_type="OPEN",
                order_id=order_id,
                metadata={
                    "allocation": allocation.to_dict()
                }
            )
            
            trade_id = self.db.create_trade(trade)
            
            # 如果提供了订单ID，创建订单记录
            if order_id and token_id:
                order = Order(
                    order_id=order_id,
                    position_id=position_id,
                    market_id=str(allocation.id),
                    token_id=token_id,
                    side="BUY" if allocation.side == "YES" else "SELL",
                    price=allocation.price,
                    size=allocation.shares,
                    status=OrderStatus.PENDING,
                    metadata={
                        "allocation": allocation.to_dict()
                    }
                )
                
                self.db.create_order(order)
            
            vlogger.trade(
                "TRADE_RECORDER.RECORD",
                msg="记录交易分配",
                extra={
                    "position_id": position_id,
                    "trade_id": trade_id,
                    "market_id": allocation.id,
                    "side": allocation.side,
                    "invest": allocation.invest,
                    "shares": allocation.shares,
                    "order_id": order_id
                }
            )
            
            return position_id
            
        except Exception as e:
            vlogger.error(
                "TRADE_RECORDER.RECORD.ERROR",
                msg="记录交易分配失败",
                error_code="E-POSITION-007",
                extra={
                    "error": str(e),
                    "market_id": allocation.id,
                    "side": allocation.side
                }
            )
            raise
    
    def update_position_price(
        self,
        position_id: int,
        current_price: float
    ) -> bool:
        """
        更新持仓的当前价格和盈亏
        
        参数:
            position_id: 持仓ID
            current_price: 当前价格
            
        返回:
            bool: 是否更新成功
        """
        try:
            position = self.db.get_position(position_id)
            if not position:
                vlogger.warn(
                    "TRADE_RECORDER.UPDATE.NOT_FOUND",
                    msg="持仓不存在",
                    error_code="E-POSITION-008",
                    extra={"position_id": position_id}
                )
                return False
            
            # 更新当前价格
            position.current_price = current_price
            
            # 计算盈亏
            # PnL = (当前价格 - 入场价格) * 份额
            position.pnl = (current_price - position.entry_price) * position.shares
            
            position.update_time = datetime.now()
            
            return self.db.update_position(position)
            
        except Exception as e:
            vlogger.error(
                "TRADE_RECORDER.UPDATE.ERROR",
                msg="更新持仓价格失败",
                error_code="E-POSITION-009",
                extra={
                    "error": str(e),
                    "position_id": position_id
                }
            )
            raise
    
    def settle_position(
        self,
        position_id: int,
        settlement_result: str,
        settlement_payout: float
    ) -> bool:
        """
        结算持仓
        
        参数:
            position_id: 持仓ID
            settlement_result: 结算结果（YES/NO）
            settlement_payout: 结算收益
            
        返回:
            bool: 是否结算成功
        """
        try:
            position = self.db.get_position(position_id)
            if not position:
                vlogger.warn(
                    "TRADE_RECORDER.SETTLE.NOT_FOUND",
                    msg="持仓不存在",
                    error_code="E-POSITION-010",
                    extra={"position_id": position_id}
                )
                return False
            
            # 更新结算信息
            position.is_settled = True
            position.settlement_result = settlement_result
            position.settlement_payout = settlement_payout
            position.status = PositionStatus.CLOSED
            position.close_time = datetime.now()
            
            # 计算最终盈亏
            position.pnl = settlement_payout - position.invest_amount
            
            success = self.db.update_position(position)
            
            if success:
                vlogger.trade(
                    "TRADE_RECORDER.SETTLE",
                    msg="持仓结算完成",
                    extra={
                        "position_id": position_id,
                        "settlement_result": settlement_result,
                        "settlement_payout": settlement_payout,
                        "pnl": position.pnl
                    }
                )
            
            return success
            
        except Exception as e:
            vlogger.error(
                "TRADE_RECORDER.SETTLE.ERROR",
                msg="结算持仓失败",
                error_code="E-POSITION-011",
                extra={
                    "error": str(e),
                    "position_id": position_id
                }
            )
            raise
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        获取持仓汇总信息
        
        返回:
            Dict[str, Any]: 持仓汇总数据
        """
        try:
            open_positions = self.db.get_open_positions()
            
            total_invest = sum(p.invest_amount for p in open_positions)
            total_pnl = sum(p.pnl or 0.0 for p in open_positions)
            
            summary = {
                "total_positions": len(open_positions),
                "total_invest": total_invest,
                "total_pnl": total_pnl,
                "positions": [p.to_dict() for p in open_positions]
            }
            
            vlogger.info(
                "TRADE_RECORDER.SUMMARY",
                msg="获取持仓汇总",
                extra={
                    "total_positions": len(open_positions),
                    "total_invest": total_invest,
                    "total_pnl": total_pnl
                }
            )
            
            return summary
            
        except Exception as e:
            vlogger.error(
                "TRADE_RECORDER.SUMMARY.ERROR",
                msg="获取持仓汇总失败",
                error_code="E-POSITION-012",
                extra={"error": str(e)}
            )
            raise

