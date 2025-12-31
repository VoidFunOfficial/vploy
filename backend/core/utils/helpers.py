"""
辅助工具函数

提供通用的辅助函数,如对象转字典等

注意: event_to_dict 和 market_to_dict 已移至 backend.utils.converters
以避免循环导入问题。此文件保留以保持向后兼容性。
"""

# 从新位置导入，保持向后兼容
from ...utils.converters import event_to_dict, market_to_dict

__all__ = ["event_to_dict", "market_to_dict"]

