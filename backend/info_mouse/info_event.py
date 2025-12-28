from enum import Enum
from typing import Dict, Any
from ..sys_configs.global_event_reg import vlogger
from ..polymarket_api import GammaMarketsAPI


prompt = open("info.md", "r", encoding="utf-8").read()
def judge_condition(analysis_result: Dict[str, Any], market_id: str,side: str,now_price: float,rule: str):
    """
    获取当前condition原因
    """
    if side == "YES":
        side = "p"
    else:
        side = "n"
    side_probalibity = analysis_result[side]
    reason_y = analysis_result[f"reasons_y"]
    reason_n = analysis_result[f"reasons_n"]
    prompt = prompt.replace("[QUESTION]", market_id)
    prompt = prompt.replace("[SIDE]", side)
    prompt = prompt.replace("[REASON_Y]", reason_y)
    prompt = prompt.replace("[REASON_N]", reason_n)
    prompt = prompt.replace("[OUR_PROBABILITY]", side_probalibity)
    prompt = prompt.replace("[CURRENT_PRICE]", now_price)
    prompt = prompt.replace("[RULE]", rule)