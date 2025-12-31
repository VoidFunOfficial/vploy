import json
from ..types import Event, Market, Tag, TradeAllocation
from ..sys_configs.global_event_reg import vlogger
from ..auto_decision import convert_gamma_market_to_simple_market
def featureMark(market: dict,allocate: TradeAllocation) -> str:
    tags=[]
    if int(market['tau']) < 3:
        tags.append("short_tau")
    if int(market['tau']) < 7:
        tags.append("normal_tau")
    if int(market['tau']) < 14 and int(market['tau']) >= 7:
        tags.append("long_tau")
    if int(market['tau']) > 30:
        tags.append("longlong_tau")
    if int(market['tau']) > 60:
        tags.append("superlong_tau")
    if "trump" in str(market['tags']) or "Trump" in market['question']:
        tags.append("trump")
    outcomePrices = market['outcome_prices']
    outcomePrices = json.loads(outcomePrices)
    buy_price = outcomePrices[0] if allocate.side == "YES" else outcomePrices[1]
    if float(buy_price) < 0.3:
        tags.append("speculation")
    if float(buy_price) > 0.7:
        tags.append("consensus")
    tags.append("auto_mark")
    return tags


def mark(market: dict,allocate: TradeAllocation) -> str:
    """
    对事件进行标记

    参数:
        market (market): 事件信息

    返回:
        str: 事件标记
    """
    try:
        # 调用AI标记函数
        mark_result = featureMark(market,allocate)

        vlogger.info("MARK.SUCCESS", msg="事件标记完成", extra={
            "event_id": market['id'],
            "mark_result": mark_result
        })

        return mark_result

    except Exception as e:
        vlogger.error("MARK.ERROR", msg="事件标记失败", error_code="E-MARK-001", extra={
            "event_id": market['id'],
            "error": str(e)
        })
        # 返回默认标记
        return "UNKNOWN"