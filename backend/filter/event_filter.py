"""
事件过滤器模块 - 多步骤事件数据过滤

实现完整的事件（Event）过滤流程：
1. Tag 黑名单过滤
2. 标题关键词黑名单过滤
3. 描述关键词黑名单过滤
4. 数据库去重检查
5. 使用 AI 过滤事件

使用 VLogger 记录每个过滤步骤的统计信息。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入 AI 过滤函数
from ..ai_analysis import ai_filter_event

# 导入 polymarket_api 数据结构
try:
    from polymarket_api import Event
    POLYMARKET_API_AVAILABLE = True
except ImportError:
    print("[Error] polymarket_api not found")
    exit(1)

# 导入 VLogger 日志系统
from backend.sys_configs.global_event_reg import vlogger

# 导入数据库模块
from .database import (
    get_blacklist,
    is_market_processed,
    mark_market_as_processed,
)


class EventFilter:
    """
    事件过滤器

    提供多步骤的事件数据过滤功能，包括：
    - Tag 黑名单过滤
    - 标题关键词黑名单过滤
    - 描述关键词黑名单过滤
    - 数据库去重检查
    - 使用 AI 过滤事件
    """

    def __init__(self, db_path: str = "backend/sys_configs/system_config.db"):
        """
        初始化事件过滤器

        参数:
            db_path: 数据库文件路径（默认使用统一配置数据库）
        """
        self.db_path = db_path

        vlogger.info("FILTER.INIT", msg="事件过滤器初始化完成", extra={
            "db_path": db_path
        })
    
    def filter_events(self, events: List[Event]) -> List[Event]:
        """
        执行完整的事件过滤流程
        
        参数:
            events: 待过滤的事件列表
            
        返回:
            List[Event]: 通过所有过滤步骤的事件列表
        """
        if not events:
            vlogger.info("FILTER.EMPTY_INPUT", msg="输入事件列表为空")
            return []

        initial_count = len(events)

        vlogger.info("FILTER.START", msg="开始事件过滤流程", extra={
            "initial_count": initial_count
        })
        
        # 执行多步骤过滤
        filtered_events = events
        
        # 步骤 1: Tag 黑名单过滤
        filtered_events = self._filter_by_tag(filtered_events)
        
        # 步骤 2: 标题关键词黑名单过滤
        filtered_events = self._filter_by_title(filtered_events)
        
        # 步骤 3: 描述关键词黑名单过滤
        filtered_events = self._filter_by_description(filtered_events)
        
        # 步骤 4: 数据库去重检查
        filtered_events = self._filter_by_database(filtered_events)
        
        # 步骤 5: 使用 AI 过滤事件
        filtered_events = self._filter_by_ai(filtered_events)
        
        # 记录最终结果
        final_count = len(filtered_events)
        filtered_count = initial_count - final_count
        pass_rate = (final_count / initial_count * 100) if initial_count > 0 else 0

        vlogger.info("FILTER.COMPLETE", msg="事件过滤流程完成", extra={
            "initial_count": initial_count,
            "final_count": final_count,
            "filtered_count": filtered_count,
            "pass_rate": f"{pass_rate:.2f}%"
        })
        
        return filtered_events
    
    def _filter_by_tag(self, events: List[Event]) -> List[Event]:
        """
        步骤1: 根据 Tag 黑名单过滤
        
        参数:
            events: 待过滤的事件列表
            
        返回:
            List[Event]: 通过 Tag 过滤的事件列表
        """
        input_count = len(events)
        
        # 从数据库读取 tag 黑名单
        blacklist_dict = get_blacklist('tag', self.db_path)
        tag_blacklist = blacklist_dict.get('tag', [])
        
        if not tag_blacklist:
            vlogger.debug("FILTER.TAG.SKIP", msg="Tag 黑名单为空，跳过过滤")
            return events
        
        # 过滤事件
        filtered_events = []
        for event in events:
            # 获取事件的 tags 字段
            tags = getattr(event, 'tags', None)
            
            if tags:
                # 处理 tags 可能是 List[Dict] 或 List[str] 的情况
                tag_values = []
                if isinstance(tags, list):
                    for tag in tags:
                        if isinstance(tag, dict):
                            # 提取 'label' 或 'slug' 字段
                            tag_values.append(tag.get('label', ''))
                            tag_values.append(tag.get('slug', ''))
                        elif isinstance(tag, str):
                            tag_values.append(tag)
                
                # 检查是否有任何标签在黑名单中（不区分大小写）
                tag_values_lower = [t.lower() for t in tag_values if t]
                if any(bl.lower() in tag_values_lower for bl in tag_blacklist):
                    vlogger.debug("FILTER.TAG.BLOCKED", msg="事件被 Tag 黑名单过滤", extra={
                        "event_id": getattr(event, 'id', 'unknown'),
                        "tags": tag_values[:5]  # 限制日志长度
                    })
                    continue
            
            filtered_events.append(event)
        
        output_count = len(filtered_events)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.TAG.COMPLETE", msg="Tag 过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": tag_blacklist
        })
        
        return filtered_events
    
    def _filter_by_title(self, events: List[Event]) -> List[Event]:
        """
        步骤2: 根据标题关键词黑名单过滤
        
        参数:
            events: 待过滤的事件列表
            
        返回:
            List[Event]: 通过标题关键词过滤的事件列表
        """
        input_count = len(events)
        
        # 从数据库读取 title_keyword 黑名单
        blacklist_dict = get_blacklist('title_keyword', self.db_path)
        keyword_blacklist = blacklist_dict.get('title_keyword', [])
        
        if not keyword_blacklist:
            vlogger.debug("FILTER.TITLE.SKIP", msg="标题关键词黑名单为空，跳过过滤")
            return events
        
        # 过滤事件
        filtered_events = []
        for event in events:
            # 获取事件的 title 字段
            title = getattr(event, 'title', '')
            
            if title:
                # 不区分大小写检查关键词
                title_lower = title.lower()
                if any(keyword.lower() in title_lower for keyword in keyword_blacklist):
                    vlogger.debug("FILTER.TITLE.BLOCKED", msg="事件被标题关键词黑名单过滤", extra={
                        "event_id": getattr(event, 'id', 'unknown'),
                        "title": title[:100]  # 限制日志长度
                    })
                    continue
            
            filtered_events.append(event)
        
        output_count = len(filtered_events)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.TITLE.COMPLETE", msg="标题关键词过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": keyword_blacklist
        })
        
        return filtered_events
    
    def _filter_by_description(self, events: List[Event]) -> List[Event]:
        """
        步骤3: 根据描述关键词黑名单过滤
        
        参数:
            events: 待过滤的事件列表
            
        返回:
            List[Event]: 通过描述关键词过滤的事件列表
        """
        input_count = len(events)
        
        # 从数据库读取 description_keyword 黑名单
        blacklist_dict = get_blacklist('description_keyword', self.db_path)
        keyword_blacklist = blacklist_dict.get('description_keyword', [])
        
        if not keyword_blacklist:
            vlogger.debug("FILTER.DESCRIPTION.SKIP", msg="描述关键词黑名单为空，跳过过滤")
            return events
        
        # 过滤事件
        filtered_events = []
        for event in events:
            # 获取事件的 description 字段
            description = getattr(event, 'description', '')
            
            if description:
                # 不区分大小写检查关键词
                description_lower = description.lower()
                if any(keyword.lower() in description_lower for keyword in keyword_blacklist):
                    vlogger.debug("FILTER.DESCRIPTION.BLOCKED", msg="事件被描述关键词黑名单过滤", extra={
                        "event_id": getattr(event, 'id', 'unknown'),
                        "description": description[:100]  # 限制日志长度
                    })
                    continue
            
            filtered_events.append(event)
        
        output_count = len(filtered_events)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.DESCRIPTION.COMPLETE", msg="描述关键词过滤完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count,
            "blacklist": keyword_blacklist
        })

        return filtered_events

    def _filter_by_database(self, events: List[Event]) -> List[Event]:
        """
        步骤4: 数据库去重检查

        参数:
            events: 待过滤的事件列表

        返回:
            List[Event]: 通过数据库检查的事件列表
        """
        input_count = len(events)

        # 过滤事件
        filtered_events = []
        for event in events:
            event_id = getattr(event, 'id', None)

            if not event_id:
                vlogger.warn("FILTER.DATABASE.NO_ID", msg="事件缺少 ID 字段，跳过")
                continue

            # 检查是否已处理（使用 event_id 作为 market_id）
            if is_market_processed(event_id, self.db_path):
                vlogger.debug("FILTER.DATABASE.DUPLICATE", msg="事件已处理，跳过", extra={
                    "event_id": event_id
                })
                continue

            filtered_events.append(event)

        # 将通过过滤的事件标记为已处理
        for event in filtered_events:
            event_id = getattr(event, 'id', None)
            if event_id:
                mark_market_as_processed(event_id, self.db_path)

        output_count = len(filtered_events)
        filtered_count = input_count - output_count

        vlogger.info("FILTER.DATABASE.COMPLETE", msg="数据库去重检查完成", extra={
            "input_count": input_count,
            "output_count": output_count,
            "filtered_count": filtered_count
        })

        return filtered_events

    def _filter_by_ai(self, events: List[Event]) -> List[Event]:
        """
        步骤5: 使用 AI 过滤事件

        参数:
            events: 待过滤的事件列表

        返回:
            List[Event]: 通过 AI 过滤的事件列表
        """
        events = [event for event in events if ai_filter_event(event)]

        return events

    async def ai_process_event(self, event: Event) -> bool:
        """
        AI 处理单个事件（预留接口）

        参数:
            event: 待处理的事件对象

        返回:
            bool: 是否通过 AI 过滤
        """
        return ai_filter_event(event)


# ==================== 便捷函数 ====================

def filter_events(events: List[Event], db_path: str = "backend/sys_configs/system_config.db") -> List[Event]:
    """
    过滤事件的便捷函数

    参数:
        events: 待过滤的事件列表
        db_path: 数据库文件路径（默认使用统一配置数据库）

    返回:
        List[Event]: 通过所有过滤步骤的事件列表
    """
    filter_instance = EventFilter(db_path)
    return filter_instance.filter_events(events)

