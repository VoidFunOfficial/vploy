"""
辅助工具函数

提供通用的辅助函数,如对象转字典等
"""

from typing import Dict, Any


def event_to_dict(event) -> Dict[str, Any]:
    """
    将 Event 对象转换为字典
    
    参数:
        event: Event 对象
        
    返回:
        dict: Event 对象的字典表示
    """
    return {
        'id': event.id,
        'title': event.title,
        'slug': event.slug,
        'description': event.description,
        'start_date': event.start_date,
        'end_date': event.end_date,
        'active': event.active,
        'markets': event.markets,
        'tags': event.tags,
        'volume': event.volume,
        'liquidity': event.liquidity,
        'marks': list(event.marks) if event.marks else [],
        'negRisk': event.negRisk
    }


def market_to_dict(market) -> Dict[str, Any]:
    """
    将 Market 对象转换为字典
    
    参数:
        market: Market 对象
        
    返回:
        dict: Market 对象的字典表示
    """
    return {
        'id': market.id,
        'question': market.question,
        'slug': market.slug,
        'outcomes': market.outcomes,
        'outcome_prices': market.outcome_prices,
        'active': market.active,
        'volume': market.volume,
        'liquidity': market.liquidity,
        'end_date': market.end_date,
        'category': market.category,
        'tags': market.tags,
        'events': market.events,
        'closedTime': market.closedTime,
        'marks': list(market.marks) if market.marks else [],
        'negRisk': market.negRisk,
        'clobTokenIds': market.clobTokenIds
    }

