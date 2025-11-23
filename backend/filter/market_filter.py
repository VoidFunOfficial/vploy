"""
市场过滤器模块 - 多步骤市场数据过滤

实现完整的市场过滤流程：
1. Category 过滤
2. Tag 过滤
3. 描述关键词过滤
4. 数据库去重与黑名单检查
5. AI 处理预留接口

使用 VLogger 记录每个过滤步骤的统计信息。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入 polymarket_api 数据结构
try:
    from ..polymarket_api import Market, Event
    POLYMARKET_API_AVAILABLE = True
except ImportError:
    print("[Error] polymarket_api not found, using simple Market class")
    exit(1)


# 导入 VLogger 日志系统
from ..sys_configs.global_event_reg import vlogger

# 导入数据库模块
from .database import (
    get_blacklist,
    is_market_processed,
    mark_market_as_processed,
)


class MarketFilter:
    """
    市场过滤器

    提供多步骤的市场数据过滤功能，包括：
    - Category 黑名单过滤
    - Tag 黑名单过滤
    - 描述关键词黑名单过滤
    - 数据库去重检查
    - AI 处理预留接口
    """

    def __init__(self, db_path: str = "backend/sys_configs/system_config.db"):
        """
        初始化市场过滤器

        参数:
            db_path: 数据库文件路径（默认使用统一配置数据库）
        """
        self.db_path = db_path

        vlogger.info("FILTER.INIT", msg="市场过滤器初始化完成", extra={
            "db_path": db_path
        })
    
    def filter_markets(self, markets: List[Market]) -> List[Market]:
        """
        执行完整的市场过滤流程
        
        参数:
            markets: 待过滤的市场列表
            
        返回:
            List[Market]: 通过所有过滤步骤的市场列表
        """
        if not markets:
            vlogger.info("FILTER.EMPTY_INPUT", msg="输入市场列表为空")
            return []

        initial_count = len(markets)

        vlogger.info("FILTER.START", msg="开始市场过滤流程", extra={
            "initial_count": initial_count
        })
        
        # 步骤1: Category 过滤
        markets = self._filter_by_category(markets)
        
        # 步骤2: Tag 过滤
        markets = self._filter_by_tag(markets)
        
        # 步骤3: 描述关键词过滤
        markets = self._filter_by_description(markets)
        
        # 步骤4: 数据库去重检查
        markets = self._filter_by_database(markets)
        
        # 步骤5: AI 处理（预留接口）
        markets = self._filter_by_ai(markets)
        
        final_count = len(markets)
        filtered_count = initial_count - final_count

        vlogger.info("FILTER.COMPLETE", msg="市场过滤流程完成", extra={
            "initial_count": initial_count,
            "final_count": final_count,
            "filtered_count": filtered_count,
            "pass_rate": f"{final_count / initial_count * 100:.2f}%" if initial_count > 0 else "0%"
        })
        
        return markets
    
    def _filter_by_category(self, markets: List[Market]) -> List[Market]:
        """
        步骤1: 根据 Category 黑名单过滤
        
        参数:
            markets: 待过滤的市场列表
            
        返回:
            List[Market]: 通过 Category 过滤的市场列表
        """
        input_count = len(markets)
        
        # 从数据库读取 category 黑名单
        blacklist_dict = get_blacklist('category', self.db_path)
        category_blacklist = blacklist_dict.get('category', [])
        
        if not category_blacklist:
            vlogger.debug("FILTER.CATEGORY.SKIP", msg="Category 黑名单为空，跳过过滤")
            return markets
        
        # 过滤市场
        filtered_markets = []
        for market in markets:
            # 获取市场的 category 字段
            category = getattr(market, 'category', None)
            
            if category and category.lower() in [c.lower() for c in category_blacklist]:
                vlogger.debug("FILTER.CATEGORY.BLOCKED", msg="市场被 Category 黑名单过滤", extra={
                    "market_id": getattr(market, 'id', 'unknown'),
                    "category": category
                })
                continue
            
            filtered_markets.append(market)
        
        output_count = len(filtered_markets)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.CATEGORY.COMPLETE", msg="Category 过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": category_blacklist
        })
        
        return filtered_markets
    
    def _filter_by_tag(self, markets: List[Market]) -> List[Market]:
        """
        步骤2: 根据 Tag 黑名单过滤
        
        参数:
            markets: 待过滤的市场列表
            
        返回:
            List[Market]: 通过 Tag 过滤的市场列表
        """
        input_count = len(markets)
        
        # 从数据库读取 tag 黑名单
        blacklist_dict = get_blacklist('tag', self.db_path)
        tag_blacklist = blacklist_dict.get('tag', [])
        
        if not tag_blacklist:
            vlogger.debug("FILTER.TAG.SKIP", msg="Tag 黑名单为空，跳过过滤")
            return markets
        
        # 过滤市场
        filtered_markets = []
        for market in markets:
            # 获取市场的 tags 字段
            tags = getattr(market, 'tags', None)
            
            if tags:
                # tags 可能是列表或字符串
                if isinstance(tags, list):
                    # 提取标签的 label 或 slug 字段
                    tag_values = []
                    for tag in tags:
                        if isinstance(tag, dict):
                            tag_values.append(tag.get('label', '').lower())
                            tag_values.append(tag.get('slug', '').lower())
                        elif isinstance(tag, str):
                            tag_values.append(tag.lower())
                    
                    # 检查是否包含黑名单标签
                    if any(bl_tag.lower() in tag_values for bl_tag in tag_blacklist):
                        vlogger.debug("FILTER.TAG.BLOCKED", msg="市场被 Tag 黑名单过滤", extra={
                            "market_id": getattr(market, 'id', 'unknown'),
                            "tags": tag_values
                        })
                        continue
                elif isinstance(tags, str):
                    # tags 是字符串
                    if any(bl_tag.lower() in tags.lower() for bl_tag in tag_blacklist):
                        vlogger.debug("FILTER.TAG.BLOCKED", msg="市场被 Tag 黑名单过滤", extra={
                            "market_id": getattr(market, 'id', 'unknown'),
                            "tags": tags
                        })
                        continue
            
            filtered_markets.append(market)
        
        output_count = len(filtered_markets)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.TAG.COMPLETE", msg="Tag 过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": tag_blacklist
        })

        return filtered_markets

    def _filter_by_description(self, markets: List[Market]) -> List[Market]:
        """
        步骤3: 根据描述关键词黑名单过滤

        参数:
            markets: 待过滤的市场列表

        返回:
            List[Market]: 通过描述关键词过滤的市场列表
        """
        input_count = len(markets)

        # 从数据库读取 description_keyword 黑名单
        blacklist_dict = get_blacklist('description_keyword', self.db_path)
        keyword_blacklist = blacklist_dict.get('description_keyword', [])

        if not keyword_blacklist:
            vlogger.debug("FILTER.DESCRIPTION.SKIP", msg="描述关键词黑名单为空，跳过过滤")
            return markets

        # 过滤市场
        filtered_markets = []
        for market in markets:
            # 获取市场的 question 字段（作为描述）
            question = getattr(market, 'question', '')

            if question:
                # 不区分大小写检查关键词
                question_lower = question.lower()
                if any(keyword.lower() in question_lower for keyword in keyword_blacklist):
                    vlogger.debug("FILTER.DESCRIPTION.BLOCKED", msg="市场被描述关键词黑名单过滤", extra={
                        "market_id": getattr(market, 'id', 'unknown'),
                        "question": question[:100]  # 限制日志长度
                    })
                    continue

            filtered_markets.append(market)

        output_count = len(filtered_markets)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.DESCRIPTION.COMPLETE", msg="描述关键词过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": keyword_blacklist
        })

        return filtered_markets

    def _filter_by_database(self, markets: List[Market]) -> List[Market]:
        """
        步骤4: 数据库去重与黑名单检查

        参数:
            markets: 待过滤的市场列表

        返回:
            List[Market]: 通过数据库检查的市场列表
        """
        input_count = len(markets)

        # 过滤市场
        filtered_markets = []
        for market in markets:
            market_id = getattr(market, 'id', None)

            if not market_id:
                vlogger.warn("FILTER.DATABASE.NO_ID", msg="市场缺少 ID 字段，跳过")
                continue

            # 检查是否已处理
            if is_market_processed(market_id, self.db_path):
                vlogger.debug("FILTER.DATABASE.DUPLICATE", msg="市场已处理，跳过", extra={
                    "market_id": market_id
                })
                continue

            filtered_markets.append(market)

        # 将通过过滤的市场标记为已处理
        for market in filtered_markets:
            market_id = getattr(market, 'id', None)
            if market_id:
                mark_market_as_processed(market_id, self.db_path)

        output_count = len(filtered_markets)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.DATABASE.COMPLETE", msg="数据库去重检查完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count
        })

        return filtered_markets

    def _filter_by_ai(self, markets: List[Market]) -> List[Market]:
        """
        步骤5: AI 处理预留接口

        参数:
            markets: 待过滤的市场列表

        返回:
            List[Market]: 通过 AI 过滤的市场列表
        """
        input_count = len(markets)

        # TODO: 未来集成 AI 过滤逻辑
        # 当前实现直接返回所有市场（占位实现）

        vlogger.info("FILTER.AI.SKIP", msg="AI 过滤未实现，跳过", extra={
            "input_count": input_count
        })

        return markets

    async def ai_process_market(self, market: Market) -> bool:
        """
        AI 处理单个市场（预留接口）

        参数:
            market: 待处理的市场对象

        返回:
            bool: 是否通过 AI 过滤

        注意:
            这是一个预留接口，用于未来集成 AI 过滤逻辑。
            当前实现直接返回 True（通过过滤）。
        """
        # TODO: 实现 AI 过滤逻辑
        # 例如：调用 LLM API 分析市场描述，判断是否符合投资标准

        vlogger.debug("FILTER.AI.PROCESS", msg="AI 处理市场（占位实现）", extra={
            "market_id": getattr(market, 'id', 'unknown')
        })

        return True


# ==================== 便捷函数 ====================

def filter_markets(markets: List[Market], db_path: str = "backend/sys_configs/system_config.db") -> List[Market]:
    """
    过滤市场的便捷函数

    参数:
        markets: 待过滤的市场列表
        db_path: 数据库文件路径（默认使用统一配置数据库）

    返回:
        List[Market]: 通过所有过滤步骤的市场列表
    """
    filter_instance = MarketFilter(db_path)
    return filter_instance.filter_markets(markets)


def filter_events(events: List[Event], db_path: str = "backend/sys_configs/system_config.db") -> List[Event]:
    """
    过滤事件的便捷函数

    注意: 此函数会过滤事件下的所有市场，并返回至少包含一个通过过滤的市场的事件

    参数:
        events: 待过滤的事件列表
        db_path: 数据库文件路径（默认使用统一配置数据库）

    返回:
        List[Event]: 包含通过过滤的市场的事件列表
    """
    filter_instance = MarketFilter(db_path)

    filtered_events = []
    for event in events:
        # 获取事件下的市场列表
        markets = getattr(event, 'markets', None)

        if markets and isinstance(markets, list):
            # 将字典转换为 Market 对象
            market_objects = []
            for market_data in markets:
                if isinstance(market_data, dict):
                    try:
                        market = Market.from_dict(market_data)
                        market_objects.append(market)
                    except Exception:
                        continue
                elif isinstance(market_data, Market):
                    market_objects.append(market_data)

            # 过滤市场
            filtered_market_objects = filter_instance.filter_markets(market_objects)

            # 如果有市场通过过滤，则保留该事件
            if filtered_market_objects:
                filtered_events.append(event)

    return filtered_events

