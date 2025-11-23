"""
AI 分析模块

提供基于 Coze AI 的事件过滤功能和基于 GPT API 的深度分析功能。
"""

# 导入 Coze AI 相关功能
from .coze_api import ai_filter_event, chat_with_coze

# 导入深度分析模块
from .deep_analysis import AnalysisTaskManager, AnalysisTask, TaskStatus

# 导入 GPT API 相关功能
from .gpt_api import send_request, get_result, parse_cookie_string

# 可用性标志
AI_ANALYSIS_AVAILABLE = True
DEEP_ANALYSIS_AVAILABLE = True

__all__ = [
    # Coze AI 相关
    'ai_filter_event',
    'chat_with_coze',

    # 深度分析相关
    'AnalysisTaskManager',
    'AnalysisTask',
    'TaskStatus',

    # GPT API 相关
    'send_request',
    'get_result',
    'parse_cookie_string',

    # 可用性标志
    'AI_ANALYSIS_AVAILABLE',
    'DEEP_ANALYSIS_AVAILABLE',
]

