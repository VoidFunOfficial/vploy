from ..types import Event, Market, Tag
from ..sys_configs.global_event_reg import vlogger
from ..ai_analysis.ai_mark import mark_event
from ..auto_decision import convert_gamma_market_to_simple_market
def featureMark(event: Event) -> str:
    tags=[]
    if Event.volume < 100:
        tags.append("low_volume")
    if Event.liquidity < 100:
        tags.append("low_liquidity")
    if Event.tau < 7:
        tags.append("short_tau")
    if Event.tau > 30:
        tags.append("long_tau")
    if Event.tau > 60:
        tags.append("very_long_tau")
    if Event.negRisk == True:
        tags.append("negRisk")
    if "trump" in str(Event.tags):
        tags.append("trump")
    
    
    return tags
def mark(event: Event,allocate) -> str:
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