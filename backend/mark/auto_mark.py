from ..polymarket_api.gamma_markets import Event
from ..sys_configs.global_event_reg import vlogger
from ..ai_analysis.ai_mark import mark_event


def mark(event: Event) -> str:
    """
    对事件进行标记

    参数:
        event (Event): 事件信息

    返回:
        str: 事件标记
    """
    try:
        # 调用AI标记函数
        mark_result = mark_event(event)

        vlogger.info("MARK.SUCCESS", msg="事件标记完成", extra={
            "event_id": event.id,
            "event_title": event.title,
            "mark_result": mark_result
        })

        return mark_result

    except Exception as e:
        vlogger.error("MARK.ERROR", msg="事件标记失败", error_code="E-MARK-001", extra={
            "event_id": event.id,
            "error": str(e)
        })
        # 返回默认标记
        return "UNKNOWN"