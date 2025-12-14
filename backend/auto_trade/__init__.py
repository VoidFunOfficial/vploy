"""
自动交易模块

实现完整的自动化交易流程，包括：
- 交易决策获取
- 订单簿分析
- 滑点控制
- 限价单执行
- 智能扫单交易
"""

from .auto_trade_exec import (
    scan_orderbook,
    trade,
)

__all__ = [
    "scan_orderbook",
    "trade",
]

