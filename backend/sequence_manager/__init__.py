"""
序列号管理模块

提供基于 SQLite 的线程安全序列号管理服务。

主要功能:
- 获取下一个序列号（原子操作）
- 初始化和重置序列
- 查询序列状态
- 管理多种业务序列

使用示例:
    >>> from backend.sequence_manager import get_sequence_manager
    >>> seq_mgr = get_sequence_manager()
    >>> 
    >>> # 获取下一个序列号
    >>> seq_id = seq_mgr.get_next_sequence('filter_sequence', result='过滤完成')
    >>> print(f"Filter序列号: {seq_id}")
    >>> 
    >>> # 查询当前序列值
    >>> current = seq_mgr.get_current_value('trade_sequence')
    >>> print(f"Trade当前序列值: {current}")
    >>> 
    >>> # 重置序列
    >>> seq_mgr.reset_sequence('analysis_sequence', value=0, result='月度重置')
    >>> 
    >>> # 列出所有序列
    >>> all_seqs = seq_mgr.list_all_sequences()
    >>> for name, info in all_seqs.items():
    >>>     print(f"{name}: {info['current_value']}")
"""

from .sequence_manager import (
    SequenceManager,
    get_sequence_manager,
)

__all__ = [
    'SequenceManager',
    'get_sequence_manager',
]

__version__ = '1.0.0'

