from .coze_api import chat_with_coze
from ..sys_configs.global_event_reg import vlogger
import os
prompt = open(os.path.join(os.path.dirname(__file__), 'mark_prompt.md'), 'r', encoding='utf-8').read()
def mark_event(event: Event) -> str:
    """
    使用Coze AI对事件进行标记
    
    参数:
        event (Event): 事件信息
    
    返回:
        str: 事件标记
    """
    try:
        response = chat_with_coze(bot_id=mark_bot_id, prompt=prompt)
        return response
    except Exception as e:
        vlogger.error("EVT-8065", msg="Coze AI调用失败", error_code="E-MARK-001", extra={"error": str(e)})
        return "unknown"