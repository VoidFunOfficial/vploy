"""
自动决策模块

提供基于 Kelly 公式 + 水位法 + 时间贴现的多市场自动仓位分配算法，支持：
- 水位法(water-filling)进行多市场资金分配
- 时间贴现(time discount)优先分配短期市场
- 集成purse模块进行资金管理
- 完整的VLogger日志记录
"""

from .position_manager import (
    allocate,
    convert_gamma_market_to_simple_market
)
from ..types import SimpleMarket, TradeAllocation

__all__ = [
    "allocate",
    "SimpleMarket",
    "TradeAllocation",
    "convert_gamma_market_to_simple_market"
]

