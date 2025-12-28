"""
自动止盈系统

基于多因子决策算法的智能止盈系统。

主要模块:
- surplus_cal: 核心决策算法
- easy_info: 数据获取模块
- auto_surplus: 自动止盈执行
- surplus_monitor: 监控集成模块

使用示例:
    from backend.surplus_dog import auto_surplus_decision, SurplusMonitor
    
    # 单个持仓决策
    result = auto_surplus_decision(
        position_id=123,
        token_id="xxx",
        execute=True
    )
    
    # 批量监控
    monitor = SurplusMonitor()
    result = monitor.monitor_all_positions_with_surplus(execute_sell=True)
"""

# 核心决策算法
from .surplus_cal import (
    decide_hold_or_sell,
    get_params,
    compute_factors,
    compute_score,
    Params
)

# 数据获取
from .easy_info import (
    get_market_realtime_data,
    get_market_history_data,
    prepare_decision_data
)

# 自动止盈执行
from .auto_surplus import (
    auto_surplus_decision,
    auto_surplus_all_positions,
    determine_strategy_tag,
    execute_sell_order
)

# 监控集成
from .surplus_monitor import (
    SurplusMonitor,
    surplus_monitor_task,
    surplus_monitor_position_task
)

__version__ = "1.0.0"

__all__ = [
    # 核心决策算法
    "decide_hold_or_sell",
    "get_params",
    "compute_factors",
    "compute_score",
    "Params",
    
    # 数据获取
    "get_market_realtime_data",
    "get_market_history_data",
    "prepare_decision_data",
    
    # 自动止盈执行
    "auto_surplus_decision",
    "auto_surplus_all_positions",
    "determine_strategy_tag",
    "execute_sell_order",
    
    # 监控集成
    "SurplusMonitor",
    "surplus_monitor_task",
    "surplus_monitor_position_task",
]

