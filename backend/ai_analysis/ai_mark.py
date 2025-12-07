from .coze_api import chat_with_coze
from ..sys_configs.global_event_reg import vlogger
from ..polymarket_api.gamma_markets import Event


def mark_event(event: Event) -> str:
    """
    使用Coze AI对事件进行标记

    参数:
        event (Event): 事件信息

    返回:
        str: 事件标记
    """
    # TODO: 实现真正的AI标记逻辑
    # try:
    #     response = chat_with_coze(bot_id=mark_bot_id, prompt=prompt)
    #     return response
    # except Exception as e:
    #     vlogger.error("EVT-8065", msg="Coze AI调用失败", error_code="E-MARK-001", extra={"error": str(e)})
    #     return "unknown"

    vlogger.info("MARK.AI.TEMP", msg="使用临时标记（待实现真正的AI标记）", extra={
        "event_id": event.id,
        "event_title": event.title
    })

    return "TEMP_MARK"