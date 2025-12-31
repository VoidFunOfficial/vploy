"""
辅助工具模块

注意: event_to_dict 和 market_to_dict 已移至 backend.utils.converters
以避免循环导入问题。此模块保留以保持向后兼容性。
"""

from ...utils.converters import event_to_dict, market_to_dict

__all__ = ["event_to_dict", "market_to_dict"]

