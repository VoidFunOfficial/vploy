"""
Polymarket Orderbook API 客户端（只读查询版本）

该模块提供了对 Polymarket Orderbook (CLOB) API 的只读查询封装。
仅包含无需身份验证的公开查询功能。

主要功能：
- 订单簿查询（单个和批量）
- 价格和价差查询
- 市场数据查询（只读）
- 使用 VLogger 记录关键操作和错误

注意：
- 本模块不包含订单管理功能（创建、取消订单等）
- 订单管理和交易历史查询请使用 clob_api 模块（基于 py-clob-client）
"""

import requests
from typing import Optional, Dict, List, Any, Union
from urllib.parse import urljoin
import json
from datetime import datetime

# 导入全局 VLogger 实例
from backend.sys_configs.global_event_reg import vlogger


class PolymarketOrderbookClient:
    """
    Polymarket Orderbook API 客户端（只读查询版本）

    该类提供了访问 Polymarket CLOB API 的只读查询方法。
    支持以下功能：
    - 获取订单簿数据（单个和批量）
    - 查询市场价格和价差
    - 查询交易历史（只读）
    - 查询市场数据（只读）
    - 使用 VLogger 记录关键操作和错误

    注意：不包含订单管理功能（创建、取消订单等）
    """

    BASE_URL = "https://clob.polymarket.com"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        proxy: Optional[str] = None
    ):
        """
        初始化 Orderbook API 客户端

        参数:
            base_url (str): API 基础 URL，默认为 https://clob.polymarket.com
            timeout (int): 请求超时时间（秒），默认 30 秒
            proxy (str): 代理服务器地址，可选
        """
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout

        # 初始化 HTTP 会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Polymarket-Orderbook-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

        # 使用全局 VLogger 实例
        self._register_events_and_errors()

        vlogger.info("ORDERBOOK.CLIENT.INIT", msg="Polymarket Orderbook API 客户端初始化完成", extra={
            "base_url": self.base_url,
            "timeout": timeout,
            "proxy_enabled": proxy is not None
        })
    
    def _register_events_and_errors(self):
        """注册事件类型和错误码（仅查询功能）"""
        from backend.vlogger import register_event, register_error

        # 注册事件类型（仅查询相关）
        register_event("EVT-OB-001", "ORDERBOOK.CLIENT.INIT", "Orderbook 客户端初始化", overwrite=True)
        register_event("EVT-OB-002", "ORDERBOOK.BOOK.QUERY", "查询订单簿", overwrite=True)
        register_event("EVT-OB-003", "ORDERBOOK.PRICE.QUERY", "查询价格", overwrite=True)
        register_event("EVT-OB-004", "ORDERBOOK.TRADE.QUERY", "查询交易记录", overwrite=True)
        register_event("EVT-OB-005", "ORDERBOOK.MARKET.QUERY", "查询市场数据", overwrite=True)
        register_event("EVT-OB-006", "ORDERBOOK.REQUEST.START", "API 请求开始", overwrite=True)
        register_event("EVT-OB-007", "ORDERBOOK.REQUEST.SUCCESS", "API 请求成功", overwrite=True)

        # 注册错误码
        register_error("E-OB-001", "HTTP_ERROR", "HTTP 请求错误", "error", overwrite=True)
        register_error("E-OB-002", "TIMEOUT_ERROR", "请求超时", "warning", overwrite=True)
        register_error("E-OB-003", "JSON_DECODE_ERROR", "JSON 解析错误", "error", overwrite=True)
        register_error("E-OB-004", "INVALID_PARAMS", "无效参数", "warning", overwrite=True)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.session.close()
    
    def _make_request(
        self, 
        method: str,
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求的通用方法
        
        参数:
            method (str): HTTP 方法（GET, POST, DELETE 等）
            endpoint (str): API 端点路径
            params (dict): 查询参数，可选
            data (dict): 请求体数据，可选
            headers (dict): 额外的请求头，可选
        
        返回:
            dict: API 响应数据
        
        异常:
            requests.RequestException: 网络请求异常
            ValueError: JSON 解析异常
        """
        url = urljoin(self.base_url, endpoint)
        
        # 合并请求头
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        # 记录请求开始
        vlogger.info("ORDERBOOK.REQUEST.START", msg="开始 API 请求", extra={
            "method": method,
            "url": url,
            "params": params or {},
            "has_data": data is not None
        })
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 记录请求成功
            vlogger.info("ORDERBOOK.REQUEST.SUCCESS", msg="API 请求成功", extra={
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "response_size": len(response.content)
            })
            return response.json()
        
        except requests.exceptions.Timeout:
            error_msg = f"请求超时: {method} {url}"
            vlogger.error("ORDERBOOK.REQUEST.ERROR", msg=error_msg, error_code="E-OB-002", extra={
                "method": method,
                "url": url,
                "timeout": self.timeout
            })
            raise

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 错误: {e.response.status_code} - {method} {url}"
            vlogger.error("ORDERBOOK.REQUEST.ERROR", msg=error_msg, error_code="E-OB-001", extra={
                "method": method,
                "url": url,
                "status_code": e.response.status_code,
                "response_text": e.response.text[:500]
            })
            raise

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析错误: {str(e)}"
            vlogger.error("ORDERBOOK.REQUEST.ERROR", msg=error_msg, error_code="E-OB-003", extra={
                "method": method,
                "url": url,
                "json_error": str(e)
            })
            raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            vlogger.error("ORDERBOOK.REQUEST.ERROR", msg=error_msg, error_code="E-OB-001", extra={
                "method": method,
                "url": url,
                "exception": str(e),
                "exception_type": type(e).__name__
            })
            raise

    # ==================== 订单簿查询 ====================

    def get_orderbook(
        self,
        token_id: str,
        side: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取指定代币的订单簿摘要

        参数:
            token_id (str): 代币 ID
            side (str): 订单方向，可选值：BUY, SELL。如果不指定则返回双向订单簿

        返回:
            dict: 订单簿数据，包含以下字段：
                - market (str): 市场 ID
                - asset_id (str): 资产 ID
                - timestamp (str): 时间戳
                - hash (str): 订单簿哈希
                - bids (list): 买单列表，每个元素包含 price 和 size
                - asks (list): 卖单列表，每个元素包含 price 和 size
                - min_order_size (str): 最小订单数量
                - tick_size (str): 价格最小变动单位
                - neg_risk (bool): 是否为负风险市场

        示例:
            >>> client = PolymarketOrderbookClient()
            >>> orderbook = client.get_orderbook("21742633143463906290569050155826241533067272736897614950488156847949938836455")
            >>> print(f"买单数量: {len(orderbook['bids'])}, 卖单数量: {len(orderbook['asks'])}")
        """
        params = {"token_id": token_id}
        if side:
            params["side"] = side

        vlogger.info("ORDERBOOK.BOOK.QUERY", msg="查询订单簿", extra={
            "token_id": token_id,
            "side": side
        })

        return self._make_request("GET", "/book", params=params)

    # ==================== 价格查询 ====================

    def get_price(
        self,
        token_id: str,
        side: str
    ) -> float:
        """
        获取指定代币的最优价格

        参数:
            token_id (str): 代币 ID
            side (str): 订单方向，BUY 或 SELL

        返回:
            float: 最优价格

        示例:
            >>> client = PolymarketOrderbookClient()
            >>> buy_price = client.get_price("token_id", "BUY")
            >>> sell_price = client.get_price("token_id", "SELL")
        """
        params = {
            "token_id": token_id,
            "side": side
        }

        vlogger.info("ORDERBOOK.PRICE.QUERY", msg="查询价格", extra={
            "token_id": token_id,
            "side": side
        })

        result = self._make_request("GET", "/price", params=params)
        return float(result.get("price", 0))

    def get_midpoint(
        self,
        token_id: str
    ) -> float:
        """
        获取指定代币的中间价（买一和卖一的平均值）

        参数:
            token_id (str): 代币 ID

        返回:
            float: 中间价

        示例:
            >>> client = PolymarketOrderbookClient()
            >>> mid_price = client.get_midpoint("token_id")
        """
        params = {"token_id": token_id}

        vlogger.info("ORDERBOOK.PRICE.QUERY", msg="查询中间价", extra={
            "token_id": token_id
        })

        result = self._make_request("GET", "/midpoint", params=params)
        return float(result.get("mid", 0))

    def get_spread(
        self,
        token_id: str
    ) -> Dict[str, float]:
        """
        获取指定代币的买卖价差

        参数:
            token_id (str): 代币 ID

        返回:
            dict: 价差信息，包含以下字段：
                - bid (float): 最优买价
                - ask (float): 最优卖价
                - spread (float): 价差（ask - bid）
                - spread_percent (float): 价差百分比

        示例:
            >>> client = PolymarketOrderbookClient()
            >>> spread = client.get_spread("token_id")
            >>> print(f"价差: {spread['spread']}, 百分比: {spread['spread_percent']}%")
        """
        params = {"token_id": token_id}
        vlogger.info("ORDERBOOK.PRICE.QUERY", msg="查询价差", extra={
            "token_id": token_id
        })

        return self._make_request("GET", "/spread", params=params)


# ==================== 模块导出 ====================

__all__ = [
    "PolymarketOrderbookClient",
]

