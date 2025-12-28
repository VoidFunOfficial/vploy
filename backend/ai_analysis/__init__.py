"""
AI 分析模块

提供基于 Coze AI 的事件过滤功能和基于 GPT API 的深度分析功能。
"""

# 导入 Coze AI 相关功能
from .coze_api import ai_filter_event, chat_with_coze

# 导入深度分析模块
from .deep_analysis import AnalysisTaskManager
from .analysis_tasks import AnalysisStatus

# 导入任务状态（从task_manager）
from ..task_manager.models import TaskStatus

# 导入 GPT API 相关功能
from .gpt_api import send_request, get_result, parse_cookie_string
# 导入总结报告功能
from .ai_summary import generate_summary_report
# 导入 info sniff 功能
from .info_sniff import InfoSniffTaskManager
# 可用性标志
AI_ANALYSIS_AVAILABLE = True
DEEP_ANALYSIS_AVAILABLE = True

__all__ = [
    # Coze AI 相关
    'ai_filter_event',
    'chat_with_coze',

    # 深度分析相关
    'AnalysisTaskManager',
    'AnalysisStatus',
    'TaskStatus',

    # GPT API 相关
    'send_request',
    'get_result',
    'parse_cookie_string',
    'generate_summary_report',
    'InfoSniffTaskManager',

    # 可用性标志
    'AI_ANALYSIS_AVAILABLE',
    'DEEP_ANALYSIS_AVAILABLE',
]

