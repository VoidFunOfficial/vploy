"""
Purse - 本地钱包管理模块

提供单例模式的钱包管理功能，支持资金锁定、盈亏记录、市场统计等。
"""

from .purse import Purse, get_purse

__all__ = ['Purse', 'get_purse']

