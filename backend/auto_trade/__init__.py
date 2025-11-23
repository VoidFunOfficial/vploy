"""
自动交易模块

实现完整的自动化交易流程，包括：
- 交易决策获取
- 订单簿分析
- 滑点控制
- 限价单执行
"""

from .auto_trade import (
    AutoTrader,
    OrderBookAnalysis,
    SlippageAnalysis,
    TradeExecution,
    execute_auto_trading,
    get_execution_summary,
)

__all__ = [
    "AutoTrader",
    "OrderBookAnalysis",
    "SlippageAnalysis",
    "TradeExecution",
    "execute_auto_trading",
    "get_execution_summary",
]

