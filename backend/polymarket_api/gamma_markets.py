import requests
from typing import Optional, Dict, List, Any, Union, Set
from urllib.parse import urljoin
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# 导入全局 VLogger 实例
from backend.sys_configs.global_event_reg import vlogger


@dataclass
class Market:
    """
    市场数据结构

    属性:
        id: 市场 ID
        question: 市场问题
        slug: 市场 slug
        outcomes: 市场选项
        outcome_prices: 选项价格
        active: 是否活跃
        volume: 交易量
        liquidity: 流动性
        end_date: 结束时间
        category: 分类
        tags: 标签列表
        events: 关联事件列表
        closedTime: 关闭时间
        marks: 自定义标签集合（用于标记和分类）
    """
    id: str
    question: str
    slug: str
    outcomes: Optional[str] = None
    outcome_prices: Optional[str] = None
    active: Optional[bool] = None
    volume: Optional[str] = None
    liquidity: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[Dict[str, Any]]] = None
    closedTime: Optional[str] = None
    marks: Set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Market':
        """从字典创建 Market 对象"""
        market = cls(
            id=data.get('id', ''),
            question=data.get('question', ''),
            slug=data.get('slug', ''),
            outcomes=data.get('outcomes'),
            outcome_prices=data.get('outcomePrices'),
            active=data.get('active'),
            volume=data.get('volume'),
            liquidity=data.get('liquidity'),
            end_date=data.get('endDate'),
            category=data.get('category'),
            tags=data.get('tags', []),
            events=data.get('events', []),
            closedTime=data.get('closedTime')
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
        active: 是否活跃
        markets: 关联市场列表
        tags: 标签列表
        volume: 交易量
        liquidity: 流动性
        marks: 自定义标签集合（用于标记和分类）
    """
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: Optional[bool] = None
    markets: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[Dict[str, Any]]] = None
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    marks: Set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """从字典创建 Event 对象"""
        event = cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            slug=data.get('slug', ''),
            description=data.get('description'),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            active=data.get('active'),
            markets=data.get('markets', []),
            tags=data.get('tags', []),
            volume=data.get('volume'),
            liquidity=data.get('liquidity')
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


class GammaMarketsAPI:
    """
    Polymarket Gamma Markets API 客户端

    该类提供了访问 Polymarket 市场数据的方法，包括事件、市场、标签等信息。
    支持以下功能：
    - 获取单个 Event 下所有 Market
    - 获取每个 Market 的所有选项及其价格信息
    - 获取当前所有活跃市场
    - 获取新增市场
    - 通过 slug 查询市场
    - 通过 tag 过滤市场
    - 使用 VLogger 记录关键操作和错误
    """

    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, timeout: int = 30, proxy: str = None):
        """
        初始化 API 客户端

        参数:
            timeout (int): 请求超时时间（秒），默认 30 秒
            proxy (str): 代理服务器地址，可选
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Polymarket-Python-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

        # 使用全局 VLogger 实例
        self._register_events_and_errors()

        vlogger.info("API.CLIENT.INIT", msg="Polymarket Gamma API 客户端初始化完成", extra={
            "base_url": self.BASE_URL,
            "timeout": timeout,
            "proxy_enabled": proxy is not None
        })

    def _register_events_and_errors(self):
        """注册事件类型和错误码"""
        from backend.vlogger import register_event, register_error

        # 注册事件类型
        register_event("EVT-PM-001", "API.CLIENT.INIT", "API 客户端初始化", overwrite=True)
        register_event("EVT-PM-002", "API.REQUEST.START", "API 请求开始", overwrite=True)
        register_event("EVT-PM-003", "API.REQUEST.SUCCESS", "API 请求成功", overwrite=True)
        register_event("EVT-PM-004", "API.REQUEST.ERROR", "API 请求错误", overwrite=True)
        register_event("EVT-PM-005", "API.MARKET.FETCH", "获取市场数据", overwrite=True)
        register_event("EVT-PM-006", "API.EVENT.FETCH", "获取事件数据", overwrite=True)
        register_event("EVT-PM-007", "API.TAG.FETCH", "获取标签数据", overwrite=True)

        # 注册错误码
        register_error("E-PM-001", "HTTP_ERROR", "HTTP 请求错误", "error", overwrite=True)
        register_error("E-PM-002", "TIMEOUT_ERROR", "请求超时", "warning", overwrite=True)
        register_error("E-PM-003", "JSON_DECODE_ERROR", "JSON 解析错误", "error", overwrite=True)
        register_error("E-PM-004", "INVALID_PARAMS", "无效参数", "warning", overwrite=True)
        register_error("E-PM-005", "RATE_LIMIT", "请求频率限制", "warning", overwrite=True)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.session.close()

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 HTTP 请求的通用方法

        参数:
            endpoint (str): API 端点路径
            params (dict): 查询参数，可选

        返回:
            dict: API 响应数据

        异常:
            requests.RequestException: 网络请求异常
            ValueError: JSON 解析异常
        """
        url = urljoin(self.BASE_URL, endpoint)

        # 记录请求开始
        vlogger.info("API.REQUEST.START", msg="开始 API 请求", extra={
            "url": url,
            "params": params or {}
        })

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # 记录请求成功
            vlogger.info("API.REQUEST.SUCCESS", msg="API 请求成功", extra={
                "url": url,
                "status_code": response.status_code,
                "response_size": len(response.content)
            })

            return response.json()

        except requests.exceptions.Timeout:
            error_msg = f"请求超时: {url}"
            vlogger.error("API.REQUEST.ERROR", msg=error_msg, error_code="E-PM-002", extra={
                "url": url,
                "timeout": self.timeout
            })
            raise

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 错误: {e.response.status_code} - {url}"
            vlogger.error("API.REQUEST.ERROR", msg=error_msg, error_code="E-PM-001", extra={
                "url": url,
                "status_code": e.response.status_code,
                "response_text": e.response.text[:500]  # 限制响应文本长度
            })
            raise

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析错误: {str(e)}"
            vlogger.error("API.REQUEST.ERROR", msg=error_msg, error_code="E-PM-003", extra={
                "url": url,
                "json_error": str(e)
            })
            raise ValueError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求异常: {str(e)}"
            vlogger.error("API.REQUEST.ERROR", msg=error_msg, error_code="E-PM-001", extra={
                "url": url,
                "exception": str(e)
            })
            raise

    # ==================== 市场相关方法 ====================

    def get_markets(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
        closed: Optional[bool] = None,
        tag_id: Optional[str] = None,
        exclude_tag_id: Optional[str] = None,
        related_tags: Optional[bool] = None
    ) -> List[Market]:
        """
        获取市场列表

        参数:
            limit (int): 返回结果数量限制，可选
            offset (int): 分页偏移量，可选
            order (str): 排序字段，可选
            ascending (bool): 是否升序排列，可选
            closed (bool): 是否包含已关闭市场，可选
            tag_id (str): 按标签 ID 过滤，可选
            exclude_tag_id (str): 排除标签 ID，可选
            related_tags (bool): 是否包含相关标签，可选

        返回:
            List[Market]: 市场对象列表
        """
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset
        if order is not None:
            params['order'] = order
        if ascending is not None:
            params['ascending'] = str(ascending).lower()
        if closed is not None:
            params['closed'] = str(closed).lower()
        if tag_id is not None:
            params['tag_id'] = tag_id
        if exclude_tag_id is not None:
            params['exclude_tag_id'] = exclude_tag_id
        if related_tags is not None:
            params['related_tags'] = str(related_tags).lower()

        vlogger.info("API.MARKET.FETCH", msg="获取市场列表", extra={
            "params": params
        })

        data = self._make_request("/markets", params)

        # 将响应数据转换为 Market 对象列表
        markets = []
        if isinstance(data, list):
            for item in data:
                try:
                    market = Market.from_dict(item)
                    markets.append(market)
                except Exception as e:
                    vlogger.warn("API.MARKET.PARSE_ERROR", msg="市场数据解析失败", extra={
                        "item": item,
                        "error": str(e)
                    })

        vlogger.info("API.MARKET.FETCH", msg="市场列表获取完成", extra={
            "count": len(markets)
        })

        return markets

    def get_market_by_id(self, market_id: str) -> Optional[Market]:
        """
        根据 ID 获取单个市场

        参数:
            market_id (str): 市场 ID

        返回:
            Market: 市场对象，如果不存在则返回 None
        """
        if not market_id:
            vlogger.warn("API.MARKET.INVALID_PARAMS", msg="市场 ID 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/markets/{market_id}")
            return Market.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.MARKET.NOT_FOUND", msg="市场不存在", extra={
                    "market_id": market_id
                })
                return None
            raise

    def get_market_by_slug(self, slug: str) -> Optional[Market]:
        """
        根据 slug 获取单个市场

        参数:
            slug (str): 市场 slug

        返回:
            Market: 市场对象，如果不存在则返回 None
        """
        if not slug:
            vlogger.warn("API.MARKET.INVALID_PARAMS", msg="市场 slug 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/markets/slug/{slug}")
            return Market.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.MARKET.NOT_FOUND", msg="市场不存在", extra={
                    "slug": slug
                })
                return None
            raise

    def get_market_tags(self, market_id: str) -> List[Tag]:
        """
        获取市场的标签列表

        参数:
            market_id (str): 市场 ID

        返回:
            List[Tag]: 标签对象列表
        """
        if not market_id:
            vlogger.warn("API.MARKET.INVALID_PARAMS", msg="市场 ID 不能为空", error_code="E-PM-004")
            return []

        try:
            data = self._make_request(f"/markets/{market_id}/tags")
            tags = []
            if isinstance(data, list):
                for item in data:
                    try:
                        tag = Tag.from_dict(item)
                        tags.append(tag)
                    except Exception as e:
                        vlogger.warn("API.TAG.PARSE_ERROR", msg="标签数据解析失败", extra={
                            "item": item,
                            "error": str(e)
                        })
            return tags
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.MARKET.NOT_FOUND", msg="市场不存在", extra={
                    "market_id": market_id
                })
                return []
            raise

    # ==================== 事件相关方法 ====================

    def get_events(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
        closed: Optional[bool] = None,
        tag_id: Optional[str] = None,
        exclude_tag_id: Optional[str] = None
    ) -> List[Event]:
        """
        获取事件列表

        参数:
            limit (int): 返回结果数量限制，可选
            offset (int): 分页偏移量，可选
            order (str): 排序字段，可选
            ascending (bool): 是否升序排列，可选
            closed (bool): 是否包含已关闭事件，可选
            tag_id (str): 按标签 ID 过滤，可选
            exclude_tag_id (str): 排除标签 ID，可选

        返回:
            List[Event]: 事件对象列表
        """
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset
        if order is not None:
            params['order'] = order
        if ascending is not None:
            params['ascending'] = str(ascending).lower()
        if closed is not None:
            params['closed'] = str(closed).lower()
        if tag_id is not None:
            params['tag_id'] = tag_id
        if exclude_tag_id is not None:
            params['exclude_tag_id'] = exclude_tag_id

        vlogger.info("API.EVENT.FETCH", msg="获取事件列表", extra={
            "params": params
        })

        data = self._make_request("/events", params)

        # 将响应数据转换为 Event 对象列表
        events = []
        if isinstance(data, list):
            for item in data:
                try:
                    event = Event.from_dict(item)
                    events.append(event)
                except Exception as e:
                    vlogger.warn("API.EVENT.PARSE_ERROR", msg="事件数据解析失败", extra={
                        "item": item,
                        "error": str(e)
                    })

        vlogger.info("API.EVENT.FETCH", msg="事件列表获取完成", extra={
            "count": len(events)
        })

        return events

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        根据 ID 获取单个事件

        参数:
            event_id (str): 事件 ID

        返回:
            Event: 事件对象，如果不存在则返回 None
        """
        if not event_id:
            vlogger.warn("API.EVENT.INVALID_PARAMS", msg="事件 ID 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/events/{event_id}")
            return Event.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.EVENT.NOT_FOUND", msg="事件不存在", extra={
                    "event_id": event_id
                })
                return None
            raise

    def get_event_by_slug(self, slug: str) -> Optional[Event]:
        """
        根据 slug 获取单个事件

        参数:
            slug (str): 事件 slug

        返回:
            Event: 事件对象，如果不存在则返回 None
        """
        if not slug:
            vlogger.warn("API.EVENT.INVALID_PARAMS", msg="事件 slug 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/events/slug/{slug}")
            return Event.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.EVENT.NOT_FOUND", msg="事件不存在", extra={
                    "slug": slug
                })
                return None
            raise

    def get_event_tags(self, event_id: str) -> List[Tag]:
        """
        获取事件的标签列表

        参数:
            event_id (str): 事件 ID

        返回:
            List[Tag]: 标签对象列表
        """
        if not event_id:
            vlogger.warn("API.EVENT.INVALID_PARAMS", msg="事件 ID 不能为空", error_code="E-PM-004")
            return []

        try:
            data = self._make_request(f"/events/{event_id}/tags")
            tags = []
            if isinstance(data, list):
                for item in data:
                    try:
                        tag = Tag.from_dict(item)
                        tags.append(tag)
                    except Exception as e:
                        vlogger.warn("API.TAG.PARSE_ERROR", msg="标签数据解析失败", extra={
                            "item": item,
                            "error": str(e)
                        })
            return tags
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.EVENT.NOT_FOUND", msg="事件不存在", extra={
                    "event_id": event_id
                })
                return []
            raise

    def get_event_markets(self, event_id: str, propagate_marks: bool = True) -> List[Market]:
        """
        获取单个事件下的所有市场

        参数:
            event_id (str): 事件 ID
            propagate_marks (bool): 是否将 Event 的 marks 传播到 Market，默认为 True

        返回:
            List[Market]: 市场对象列表
        """
        if not event_id:
            vlogger.warn("API.EVENT.INVALID_PARAMS", msg="事件 ID 不能为空", error_code="E-PM-004")
            return []

        # 首先获取事件详情，其中包含关联的市场
        event = self.get_event_by_id(event_id)
        if not event or not event.markets:
            return []

        # 将市场数据转换为 Market 对象
        markets = []
        for market_data in event.markets:
            try:
                market = Market.from_dict(market_data)

                # 如果启用了 marks 传播，将 Event 的 marks 添加到 Market
                if propagate_marks and event.marks:
                    for mark in event.marks:
                        market.add_marks(mark)

                markets.append(market)
            except Exception as e:
                vlogger.warn("API.MARKET.PARSE_ERROR", msg="市场数据解析失败", extra={
                    "market_data": market_data,
                    "error": str(e)
                })

        vlogger.info("API.EVENT.MARKETS", msg="获取事件市场完成", extra={
            "event_id": event_id,
            "market_count": len(markets),
            "marks_propagated": propagate_marks and len(event.marks) > 0
        })

        return markets

    # ==================== 标签相关方法 ====================

    def get_tags(self) -> List[Tag]:
        """
        获取所有标签列表

        返回:
            List[Tag]: 标签对象列表
        """
        vlogger.info("API.TAG.FETCH", msg="获取标签列表")

        data = self._make_request("/tags")

        # 将响应数据转换为 Tag 对象列表
        tags = []
        if isinstance(data, list):
            for item in data:
                try:
                    tag = Tag.from_dict(item)
                    tags.append(tag)
                except Exception as e:
                    vlogger.warn("API.TAG.PARSE_ERROR", msg="标签数据解析失败", extra={
                        "item": item,
                        "error": str(e)
                    })

        vlogger.info("API.TAG.FETCH", msg="标签列表获取完成", extra={
            "count": len(tags)
        })

        return tags

    def get_tag_by_id(self, tag_id: str) -> Optional[Tag]:
        """
        根据 ID 获取单个标签

        参数:
            tag_id (str): 标签 ID

        返回:
            Tag: 标签对象，如果不存在则返回 None
        """
        if not tag_id:
            vlogger.warn("API.TAG.INVALID_PARAMS", msg="标签 ID 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/tags/{tag_id}")
            return Tag.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.TAG.NOT_FOUND", msg="标签不存在", extra={
                    "tag_id": tag_id
                })
                return None
            raise

    def get_tag_by_slug(self, slug: str) -> Optional[Tag]:
        """
        根据 slug 获取单个标签

        参数:
            slug (str): 标签 slug

        返回:
            Tag: 标签对象，如果不存在则返回 None
        """
        if not slug:
            vlogger.warn("API.TAG.INVALID_PARAMS", msg="标签 slug 不能为空", error_code="E-PM-004")
            return None

        try:
            data = self._make_request(f"/tags/slug/{slug}")
            return Tag.from_dict(data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                vlogger.warn("API.TAG.NOT_FOUND", msg="标签不存在", extra={
                    "slug": slug
                })
                return None
            raise

    # ==================== 搜索相关方法 ====================

    def search(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        搜索市场、事件和用户资料

        参数:
            query (str): 搜索查询字符串
            limit (int): 返回结果数量限制，可选
            offset (int): 分页偏移量，可选

        返回:
            dict: 搜索结果，包含市场、事件等信息
        """
        if not query:
            vlogger.warn("API.SEARCH.INVALID_PARAMS", msg="搜索查询不能为空", error_code="E-PM-004")
            return {}

        params = {'q': query}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset

        vlogger.info("API.SEARCH.START", msg="开始搜索", extra={
            "query": query,
            "params": params
        })

        data = self._make_request("/public-search", params)

        vlogger.info("API.SEARCH.COMPLETE", msg="搜索完成", extra={
            "query": query,
            "result_keys": list(data.keys()) if isinstance(data, dict) else "non-dict"
        })

        return data

    # ==================== 便捷方法 ====================

    def get_active_markets(self, limit: Optional[int] = None) -> List[Market]:
        """
        获取当前所有活跃市场

        参数:
            limit (int): 返回结果数量限制，可选

        返回:
            List[Market]: 活跃市场对象列表
        """
        vlogger.info("API.MARKET.ACTIVE", msg="获取活跃市场")

        return self.get_markets(limit=limit, closed=False)

    def get_markets_by_tag(self, tag_slug: str, limit: Optional[int] = None) -> List[Market]:
        """
        根据标签获取市场列表

        参数:
            tag_slug (str): 标签 slug
            limit (int): 返回结果数量限制，可选

        返回:
            List[Market]: 市场对象列表
        """
        if not tag_slug:
            vlogger.warn("API.MARKET.INVALID_PARAMS", msg="标签 slug 不能为空", error_code="E-PM-004")
            return []

        # 首先获取标签信息
        tag = self.get_tag_by_slug(tag_slug)
        if not tag:
            vlogger.warn("API.TAG.NOT_FOUND", msg="标签不存在", extra={
                "tag_slug": tag_slug
            })
            return []

        vlogger.info("API.MARKET.BY_TAG", msg="根据标签获取市场", extra={
            "tag_slug": tag_slug,
            "tag_id": tag.id
        })

        return self.get_markets(limit=limit, tag_id=tag.id)

    def get_new_markets(self, limit: Optional[int] = None) -> List[Market]:
        """
        获取新增市场（按创建时间排序）

        参数:
            limit (int): 返回结果数量限制，可选

        返回:
            List[Market]: 新增市场对象列表
        """
        vlogger.info("API.MARKET.NEW", msg="获取新增市场")

        # 按创建时间降序排列获取最新市场
        return self.get_markets(limit=limit, order="createdAt", ascending=False)

    def get_market_outcomes_and_prices(self, market_id: str) -> Dict[str, Any]:
        """
        获取市场的所有选项（outcomes）及其价格信息

        参数:
            market_id (str): 市场 ID

        返回:
            dict: 包含选项和价格信息的字典
        """
        if not market_id:
            vlogger.warn("API.MARKET.INVALID_PARAMS", msg="市场 ID 不能为空", error_code="E-PM-004")
            return {}

        market = self.get_market_by_id(market_id)
        if not market:
            return {}

        result = {
            "market_id": market.id,
            "question": market.question,
            "outcomes": market.outcomes,
            "outcome_prices": market.outcome_prices,
            "active": market.active,
            "volume": market.volume,
            "liquidity": market.liquidity
        }

        vlogger.info("API.MARKET.OUTCOMES", msg="获取市场选项和价格完成", extra={
            "market_id": market_id,
            "has_outcomes": market.outcomes is not None,
            "has_prices": market.outcome_prices is not None
        })

        return result

    def get_event_with_all_markets(self, event_id: str) -> Dict[str, Any]:
        """
        获取事件及其所有关联市场的完整信息

        参数:
            event_id (str): 事件 ID

        返回:
            dict: 包含事件和市场信息的字典
        """
        if not event_id:
            vlogger.warn("API.EVENT.INVALID_PARAMS", msg="事件 ID 不能为空", error_code="E-PM-004")
            return {}

        # 获取事件信息
        event = self.get_event_by_id(event_id)
        if not event:
            return {}

        # 获取事件下的所有市场
        markets = self.get_event_markets(event_id)

        # 为每个市场获取详细的选项和价格信息
        detailed_markets = []
        for market in markets:
            market_details = self.get_market_outcomes_and_prices(market.id)
            detailed_markets.append(market_details)

        result = {
            "event": {
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "description": event.description,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "active": event.active,
                "volume": event.volume,
                "liquidity": event.liquidity
            },
            "markets": detailed_markets,
            "market_count": len(detailed_markets)
        }

        vlogger.info("API.EVENT.COMPLETE", msg="获取事件完整信息完成", extra={
            "event_id": event_id,
            "market_count": len(detailed_markets)
        })

        return result

    # ==================== 健康检查方法 ====================

    def health_check(self) -> bool:
        """
        检查 API 服务健康状态
        使用官方健康检查端点: https://data-api.polymarket.com/

        返回:
            bool: True 表示服务正常，False 表示服务异常
        """
        try:
            # 使用官方健康检查端点
            health_url = "https://data-api.polymarket.com/"
            response = self.session.get(health_url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            if data.get("data") == "OK":
                vlogger.info("API.HEALTH.OK", msg="API 服务健康检查通过")
                return True
            return False
        except Exception as e:
            vlogger.error("API.HEALTH.FAIL", msg="API 服务健康检查失败", extra={
                "error": str(e)
            })
            return False

    def get_new_events(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Event]:
        """
        获取最新创建的事件列表（按创建时间降序排列）

        参数:
            limit (int): 返回结果数量限制，可选
            offset (int): 分页偏移量，可选

        返回:
            List[Event]: 事件对象列表，按创建时间降序排列
        """
        vlogger.info("API.EVENT.NEW", msg="获取新增事件")

        params = {
            "order": "createdAt",
            "ascending": "false"
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        vlogger.info("EVT-PM-006", msg="获取事件列表", extra={"params": params})

        response = self._make_request("/events", params)
        if not response:
            return []

        events = []
        for event_data in response:
            try:
                event = Event.from_dict(event_data)
                events.append(event)
            except Exception as e:
                vlogger.warn("API.EVENT.PARSE_ERROR", msg="解析事件数据失败", extra={
                    "event_data": event_data,
                    "error": str(e)
                })
                continue

        vlogger.info("EVT-PM-006", msg="事件列表获取完成", extra={"count": len(events)})

        return events


# ==================== 便捷函数 ====================

def get_active_markets(timeout: int = 30, proxy: str = None, limit: Optional[int] = None) -> List[Market]:
    """
    获取活跃市场的便捷函数

    参数:
        timeout (int): 请求超时时间（秒），默认 30 秒
        proxy (str): 代理服务器地址，可选
        limit (int): 返回结果数量限制，可选

    返回:
        List[Market]: 活跃市场对象列表
    """
    with GammaMarketsAPI(timeout=timeout, proxy=proxy) as api:
        return api.get_active_markets(limit=limit)


def get_new_events(timeout: int = 30, proxy: str = None, limit: Optional[int] = None) -> List[Event]:
    """
    获取最新创建事件的便捷函数

    参数:
        timeout (int): 请求超时时间（秒），默认 30 秒
        proxy (str): 代理服务器地址，可选
        limit (int): 返回结果数量限制，可选

    返回:
        List[Event]: 最新事件对象列表，按创建时间降序排列
    """
    with GammaMarketsAPI(timeout=timeout, proxy=proxy) as api:
        return api.get_new_events(limit=limit)


def search(query: str, timeout: int = 30, proxy: str = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    搜索的便捷函数

    参数:
        query (str): 搜索查询字符串
        timeout (int): 请求超时时间（秒），默认 30 秒
        proxy (str): 代理服务器地址，可选
        limit (int): 返回结果数量限制，可选

    返回:
        dict: 搜索结果
    """
    with GammaMarketsAPI(timeout=timeout, proxy=proxy) as api:
        return api.search(query, limit=limit)


def base_filter(
    tag_slug: Optional[str] = None,
    closed: Optional[bool] = None,
    limit: Optional[int] = None,
    timeout: int = 30,
    proxy: str = None
) -> List[Market]:
    """
    基础过滤的便捷函数

    参数:
        tag_slug (str): 标签 slug，可选
        closed (bool): 是否包含已关闭市场，可选
        limit (int): 返回结果数量限制，可选
        timeout (int): 请求超时时间（秒），默认 30 秒
        proxy (str): 代理服务器地址，可选

    返回:
        List[Market]: 过滤后的市场对象列表
    """
    with GammaMarketsAPI(timeout=timeout, proxy=proxy) as api:
        if tag_slug:
            return api.get_markets_by_tag(tag_slug, limit=limit)
        else:
            return api.get_markets(limit=limit, closed=closed)

def event_summary_readable(event: Event) -> str:
    """
    事件摘要的可读函数

    参数:
        event (Event): 事件对象

    返回:
        str: 该事件的摘要，包括事件下所有市场的摘要、价格列表和volume列表，以可读的字符串形式返回
    """
    if not event:
        return "无效的事件对象"
    
    # 构建事件基本信息
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append(f"Event Title: {event.title}")
    if event.description:
        summary_lines.append(f"Description: {event.description}")
    
    if event.start_date:
        summary_lines.append(f"开始时间: {event.start_date}")
    
    if event.end_date:
        summary_lines.append(f"结束时间: {event.end_date}")
    
    if event.volume is not None:
        summary_lines.append(f"总交易量: ${event.volume:,.2f}")
    
    if event.liquidity is not None:
        summary_lines.append(f"总流动性: ${event.liquidity:,.2f}")
    
    # 标签信息
    if event.tags:
        tag_names = [tag.get('label', tag.get('slug', '未知')) for tag in event.tags]
        summary_lines.append(f"标签: {', '.join(tag_names)}")
    
    # 市场信息
    if event.markets:
        summary_lines.append(f"\n关联市场数量: {len(event.markets)}")
        summary_lines.append("-" * 80)
        
        for idx, market_data in enumerate(event.markets, 1):
            summary_lines.append(f"\n市场 #{idx}:")
            summary_lines.append(f"  问题: {market_data.get('question', '未知')}")
            summary_lines.append(f"  市场ID: {market_data.get('id', '未知')}")
            summary_lines.append(f"  Slug: {market_data.get('slug', '未知')}")
            summary_lines.append(f"  状态: {'活跃' if market_data.get('active') else '已关闭'}")
            
            # 选项和价格
            outcomes = market_data.get('outcomes')
            outcome_prices = market_data.get('outcomePrices')
            
            if outcomes and outcome_prices:
                try:
                    # 尝试解析 JSON 字符串
                    if isinstance(outcomes, str):
                        import json
                        outcomes = json.loads(outcomes)
                    if isinstance(outcome_prices, str):
                        outcome_prices = json.loads(outcome_prices)
                    
                    summary_lines.append("  选项和价格:")
                    for outcome, price in zip(outcomes, outcome_prices):
                        summary_lines.append(f"    - {outcome}: ${price}")
                except Exception as e:
                    summary_lines.append(f"  选项: {outcomes}")
                    summary_lines.append(f"  价格: {outcome_prices}")
            
            # 交易量和流动性
            volume = market_data.get('volume')
            if volume:
                try:
                    volume_float = float(volume)
                    summary_lines.append(f"  交易量: ${volume_float:,.2f}")
                except (ValueError, TypeError):
                    summary_lines.append(f"  交易量: {volume}")
            
            liquidity = market_data.get('liquidity')
            if liquidity:
                try:
                    liquidity_float = float(liquidity)
                    summary_lines.append(f"  流动性: ${liquidity_float:,.2f}")
                except (ValueError, TypeError):
                    summary_lines.append(f"  流动性: {liquidity}")
    else:
        summary_lines.append("\n该事件暂无关联市场")
    
    summary_lines.append("=" * 80)
    
    return "\n".join(summary_lines)

def event_summary_readableforai(event: Event) -> str:
    """
    事件摘要的可读函数,用于AI处理

    参数:
        event (Event): 事件对象

    返回:
        str: 该事件的摘要，包括事件下所有市场的摘要、价格列表和volume列表，以可读的字符串形式返回
    """
    if not event:
        return "无效的事件对象"
    
    #节约token,省略不必要的信息
    summary_lines = []
    summary_lines.append(f"Event Title: {event.title}")
    
    
    if event.start_date:
        summary_lines.append(f"Start Date: {event.start_date}")
    
    if event.end_date:
        summary_lines.append(f"End Date: {event.end_date}")
    
    # 市场信息
    if event.markets:
        for idx, market_data in enumerate(event.markets, 1):
            idx = market_data.get('id')
            summary_lines.append(f"{idx}:")
            summary_lines.append(f"  End Date: {market_data.get('endDate', '未知')}\n")
            summary_lines.append(f"  Question: {market_data.get('question', '未知')}")
            
    else:
        summary_lines.append("\n该事件暂无关联市场")
    
    return "\n".join(summary_lines)