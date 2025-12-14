# -*- coding: utf-8 -*-
"""
Polymarket 数据类型定义

包含 Market、Event、Tag 等核心数据结构。
这些数据类型从 gamma_markets.py 抽离，供整个项目使用。
"""

from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import json

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger


@dataclass
class Market:
    """
    市场数据结构

    属性:
        id: 市场 ID
        question: 市场问题
        slug: 市场 slug
        conditionId: 条件 ID
        outcomes: 市场选项
        outcome_prices: 选项价格
        active: 是否活跃
        volume: 交易量
        liquidity: 流动性
        end_date: 结束时间
        tau: 结算剩余天数
        tags: 标签列表
        marks: 自定义标签集合（用于标记和分类）
        negRisk: 是否为负风险市场
        clobTokenIds: CLOB 代币 ID 列表
    """
    id: str
    question: str
    slug: str
    conditionId: Optional[str] = None
    outcomes: Optional[str] = None
    outcome_prices: Optional[str] = None
    active: Optional[bool] = None
    volume: Optional[str] = None
    liquidity: Optional[str] = None
    end_date: Optional[str] = None
    tau: Optional[int] = None
    tags: Optional[List[Dict[str, Any]]] = None
    marks: Set[str] = field(default_factory=set)
    negRisk: Optional[bool] = None
    clobTokenIds: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Market':
        """从字典创建 Market 对象"""
        end_data = data.get('endDate')
        tau = None
        if end_data:
            try:
                end_date = datetime.strptime(end_data, "%Y-%m-%dT%H:%M:%SZ")
                tau = (end_date - datetime.now()).days
            except ValueError as e:
                vlogger.warn("MARKET.DATE.PARSE_ERROR", msg="时间格式解析失败", extra={
                    "end_date": end_data,
                    "error": str(e)
                })

        market = cls(
            id=data.get('id', ''),
            question=data.get('question', ''),
            slug=data.get('slug', ''),
            conditionId=data.get('conditionId'),
            outcomes=data.get('outcomes'),
            outcome_prices=data.get('outcomePrices'),
            active=data.get('active'),
            volume=data.get('volume'),
            liquidity=data.get('liquidity'),
            end_date=data.get('endDate'),
            tau=tau,
            tags=data.get('tags', []),
            negRisk=data.get('negRisk'),
            clobTokenIds=data.get('clobTokenIds')
        )

        # 如果数据中包含 marks，则加载它
        if 'marks' in data:
            marks_data = data['marks']
            if isinstance(marks_data, (list, set)):
                market.marks = set(marks_data)
            elif isinstance(marks_data, str):
                # 如果是字符串，尝试解析为 JSON
                try:
                    parsed = json.loads(marks_data)
                    if isinstance(parsed, list):
                        market.marks = set(parsed)
                except:
                    pass

        return market

    def add_marks(self, mark: str) -> None:
        """
        添加单个标签

        参数:
            mark: 要添加的标签字符串
        """
        if not mark or not isinstance(mark, str):
            vlogger.warn("MARKET.MARKS.INVALID", msg="无效的标签", extra={"mark": mark, "market_id": self.id})
            return

        self.marks.add(mark.strip())
        vlogger.debug("MARKET.MARKS.ADDED", msg="添加标签", extra={"mark": mark, "market_id": self.id})

    def remove_marks(self, mark: str) -> bool:
        """
        移除单个标签

        参数:
            mark: 要移除的标签字符串

        返回:
            bool: 如果标签存在并被移除返回 True，否则返回 False
        """
        if not mark or not isinstance(mark, str):
            vlogger.warn("MARKET.MARKS.INVALID", msg="无效的标签", extra={"mark": mark, "market_id": self.id})
            return False

        mark = mark.strip()
        if mark in self.marks:
            self.marks.remove(mark)
            vlogger.debug("MARKET.MARKS.REMOVED", msg="移除标签", extra={"mark": mark, "market_id": self.id})
            return True
        else:
            vlogger.debug("MARKET.MARKS.NOT_FOUND", msg="标签不存在", extra={"mark": mark, "market_id": self.id})
            return False

    def has_mark(self, mark: str) -> bool:
        """
        检查是否包含指定标签

        参数:
            mark: 要检查的标签字符串

        返回:
            bool: 如果包含该标签返回 True，否则返回 False
        """
        return mark.strip() in self.marks if mark else False

    def get_marks(self) -> Set[str]:
        """
        获取所有标签

        返回:
            Set[str]: 标签集合的副本
        """
        return self.marks.copy()


@dataclass
class Event:
    """
    事件数据结构

    属性:
        id: 事件 ID
        title: 事件标题
        slug: 事件 slug
        description: 事件描述
        start_date: 开始时间
        end_date: 结束时间
        tau: 结算剩余天数
        active: 是否活跃
        markets: 关联市场列表
        tags: 标签列表
        volume: 交易量
        liquidity: 流动性
        marks: 自定义标签集合（用于标记和分类）
        negRisk: 是否为负风险事件
    """
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tau: Optional[int] = None
    active: Optional[bool] = None
    markets: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[Dict[str, Any]]] = None
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    marks: Set[str] = field(default_factory=set)
    negRisk: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """从字典创建 Event 对象"""
        end_data = data.get('endDate')
        tau = None
        if end_data:
            try:
                end_date = datetime.strptime(end_data, "%Y-%m-%dT%H:%M:%SZ")
                tau = (end_date - datetime.now()).days
            except ValueError as e:
                vlogger.warn("EVENT.DATE.PARSE_ERROR", msg="时间格式解析失败", extra={
                    "end_date": end_data,
                    "error": str(e)
                })

        event = cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            slug=data.get('slug', ''),
            description=data.get('description'),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            tau=tau,
            active=data.get('active'),
            markets=data.get('markets', []),
            tags=data.get('tags', []),
            volume=data.get('volume'),
            liquidity=data.get('liquidity'),
            negRisk=data.get('negRisk')
        )

        # 如果数据中包含 marks，则加载它
        if 'marks' in data:
            marks_data = data['marks']
            if isinstance(marks_data, (list, set)):
                event.marks = set(marks_data)
            elif isinstance(marks_data, str):
                # 如果是字符串，尝试解析为 JSON
                try:
                    parsed = json.loads(marks_data)
                    if isinstance(parsed, list):
                        event.marks = set(parsed)
                except:
                    pass

        return event

    def add_marks(self, mark: str) -> None:
        """
        添加单个标签

        参数:
            mark: 要添加的标签字符串
        """
        if not mark or not isinstance(mark, str):
            vlogger.warn("EVENT.MARKS.INVALID", msg="无效的标签", extra={"mark": mark, "event_id": self.id})
            return

        self.marks.add(mark.strip())
        vlogger.debug("EVENT.MARKS.ADDED", msg="添加标签", extra={"mark": mark, "event_id": self.id})

    def remove_marks(self, mark: str) -> bool:
        """
        移除单个标签

        参数:
            mark: 要移除的标签字符串

        返回:
            bool: 如果标签存在并被移除返回 True，否则返回 False
        """
        if not mark or not isinstance(mark, str):
            vlogger.warn("EVENT.MARKS.INVALID", msg="无效的标签", extra={"mark": mark, "event_id": self.id})
            return False

        mark = mark.strip()
        if mark in self.marks:
            self.marks.remove(mark)
            vlogger.debug("EVENT.MARKS.REMOVED", msg="移除标签", extra={"mark": mark, "event_id": self.id})
            return True
        else:
            vlogger.debug("EVENT.MARKS.NOT_FOUND", msg="标签不存在", extra={"mark": mark, "event_id": self.id})
            return False

    def has_mark(self, mark: str) -> bool:
        """
        检查是否包含指定标签

        参数:
            mark: 要检查的标签字符串

        返回:
            bool: 如果包含该标签返回 True，否则返回 False
        """
        return mark.strip() in self.marks if mark else False

    def get_marks(self) -> Set[str]:
        """
        获取所有标签

        返回:
            Set[str]: 标签集合的副本
        """
        return self.marks.copy()

    def get_markets_with_marks(self) -> List['Market']:
        """
        获取 Event 的所有 Market 对象，并自动将 Event 的 marks 传播到每个 Market

        该方法会将 Event.markets（字典列表）转换为 Market 对象列表，
        并自动将 Event 的所有 marks 添加到每个 Market 中。

        返回:
            List[Market]: Market 对象列表，每个 Market 都继承了 Event 的 marks
        """
        if not self.markets:
            return []

        market_objects = []
        for market_data in self.markets:
            # 如果已经是 Market 对象，直接使用
            if isinstance(market_data, Market):
                market = market_data
            # 如果是字典，转换为 Market 对象
            elif isinstance(market_data, dict):
                try:
                    market = Market.from_dict(market_data)
                except Exception as e:
                    vlogger.warn("EVENT.MARKET.PARSE_ERROR", msg="市场数据解析失败", extra={
                        "event_id": self.id,
                        "market_data": market_data,
                        "error": str(e)
                    })
                    continue
            else:
                continue

            # 将 Event 的 marks 传播到 Market
            if self.marks:
                for mark in self.marks:
                    market.add_marks(mark)

            market_objects.append(market)

        if market_objects and self.marks:
            vlogger.debug("EVENT.MARKS.PROPAGATED", msg="标签已传播到关联市场", extra={
                "event_id": self.id,
                "marks_count": len(self.marks),
                "markets_count": len(market_objects)
            })

        return market_objects


@dataclass
class Tag:
    """
    标签数据结构

    属性:
        id: 标签 ID
        label: 标签名称
        slug: 标签 slug
    """
    id: str
    label: str
    slug: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tag':
        """从字典创建 Tag 对象"""
        return cls(
            id=data.get('id', ''),
            label=data.get('label', ''),
            slug=data.get('slug', '')
        )

