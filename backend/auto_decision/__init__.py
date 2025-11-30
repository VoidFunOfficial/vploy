"""
自动决策模块

提供基于 Kelly 公式的最优仓位分配算法，支持：
- 多市场并行分析和资金分配
- 集成 AI 分析结果和风险因子
- 完整的风险管理和日志记录
"""

from .position_manager import (
    allocate,
    convert_to_simple_market
)

__all__ = [
    "allocate",
    "convert_to_simple_market"
]

