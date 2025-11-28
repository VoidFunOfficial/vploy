"""
Polymarket CLOB WebSocket 客户端

基于官方文档实现: https://docs.polymarket.com/developers/CLOB/websocket/wss-overview
支持 USER 和 MARKET 频道的订阅和消息处理
"""

import asyncio
import json
import time
import hmac
import hashlib
from typing import Optional, Dict, Callable, Any, List, Set
from enum import Enum
from dataclasses import dataclass

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    raise ImportError("需要安装 websockets 库: pip install websockets")

from ..sys_configs.global_event_reg import vlogger
from ..polymarket_api.clob_api import get_client

class ChannelType(Enum):
    """WebSocket 频道类型"""
    USER = "user"  # 用户频道 - 需要认证
    MARKET = "market"  # 市场频道 - 无需认证


class MessageType(Enum):
    """消息类型"""
    # User Channel
    TRADE = "TRADE"
    ORDER_PLACEMENT = "PLACEMENT"
    ORDER_UPDATE = "UPDATE"
    ORDER_CANCELLATION = "CANCELLATION"

    # Market Channel
    BOOK = "book"
    PRICE_CHANGE = "price_change"
    TICK_SIZE_CHANGE = "tick_size_change"
    LAST_TRADE_PRICE = "last_trade_price"


@dataclass
class WSConfig:
    """WebSocket 配置"""
    url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/"
    ping_interval: int = 20  # 心跳间隔(秒)
    ping_timeout: int = 10  # 心跳超时(秒)
    reconnect_delay: int = 5  # 重连延迟(秒)
    max_reconnect_attempts: int = 10  # 最大重连次数
    message_queue_size: int = 1000  # 消息队列大小


class PolymarketWSClient:
    """
    Polymarket CLOB WebSocket 客户端

    功能:
    - 支持 USER 和 MARKET 频道订阅
    - 自动重连机制
    - 心跳保活
    - 消息回调处理
    - 订阅管理

    示例:
        # 市场频道(无需认证)
        client = PolymarketWSClient()
        client.on_message(lambda msg: print(msg))
        await client.connect()
        await client.subscribe_market("market_id")

        # 用户频道(需要认证)
        client = PolymarketWSClient(
            api_key="your_key",
            api_secret="your_secret",
            api_passphrase="your_passphrase"
        )
        await client.connect()
        await client.subscribe_user()
    """

    def __init__(
        self,
        config: Optional[WSConfig] = None
    ):
        """
        初始化 WebSocket 客户端

        参数:
            api_key: CLOB API Key (USER 频道必需)
            api_secret: CLOB API Secret (USER 频道必需)
            api_passphrase: CLOB API Passphrase (USER 频道必需)
            config: WebSocket 配置
        """
        a = get_client().create_or_derive_api_creds()
        self.api_key = a.api_key
        self.api_secret = a.api_secret
        self.api_passphrase = a.api_passphrase
        self.config = config or WSConfig()

        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_count = 0
        self._subscriptions: Set[str] = set()  # 已订阅的频道

        # 回调函数
        self._message_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        self._connect_callbacks: List[Callable[[], None]] = []
        self._disconnect_callbacks: List[Callable[[], None]] = []

        # 任务
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

        vlogger.info("INGEST.WS.INIT", msg="WebSocket 客户端初始化", extra={
            "url": self.config.url,
            "has_auth": bool(self.api_key and self.api_secret and self.api_passphrase)
        })

    def on_message(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """注册消息回调"""
        self._message_callbacks.append(callback)

    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """注册错误回调"""
        self._error_callbacks.append(callback)

    def on_connect(self, callback: Callable[[], None]) -> None:
        """注册连接成功回调"""
        self._connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[], None]) -> None:
        """注册断开连接回调"""
        self._disconnect_callbacks.append(callback)

    async def connect(self) -> None:
        """建立 WebSocket 连接"""
        if self._running:
            vlogger.warn("INGEST.WS.ALREADY_CONNECTED", msg="WebSocket 已连接")
            return

        try:
            vlogger.info("INGEST.WS.CONNECTING", msg="正在连接 WebSocket", extra={
                "url": self.config.url
            })

            self._ws = await websockets.connect(
                self.config.url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout
            )

            self._running = True
            self._reconnect_count = 0

            vlogger.info("INGEST.WS.CONNECTED", msg="WebSocket 连接成功", extra={
                "url": self.config.url
            })

            # 触发连接回调
            for callback in self._connect_callbacks:
                try:
                    callback()
                except Exception as e:
                    vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="连接回调执行失败",
                                error_code="E-WS-001", extra={"error": str(e)})

            # 启动接收和心跳任务
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._ping_task = asyncio.create_task(self._ping_loop())

        except Exception as e:
            vlogger.error("INGEST.WS.CONNECT_FAILED", msg="WebSocket 连接失败",
                        error_code="E-WS-002", extra={"error": str(e)})
            await self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """断开 WebSocket 连接"""
        if not self._running:
            return

        vlogger.info("INGEST.WS.DISCONNECTING", msg="正在断开 WebSocket 连接")

        self._running = False

        # 取消任务
        if self._receive_task:
            self._receive_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()

        # 关闭连接
        if self._ws:
            await self._ws.close()
            self._ws = None

        # 触发断开回调
        for callback in self._disconnect_callbacks:
            try:
                callback()
            except Exception as e:
                vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="断开回调执行失败",
                            error_code="E-WS-003", extra={"error": str(e)})

        vlogger.info("INGEST.WS.DISCONNECTED", msg="WebSocket 已断开")

    async def subscribe_user(self) -> None:
        """
        订阅用户频道

        需要提供 API 认证信息
        """
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            raise ValueError("订阅 USER 频道需要提供 API 认证信息")

        channel = ChannelType.USER.value

        # 构建认证消息
        message = {
            "auth": {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "passphrase": self.api_passphrase
            },
            "markets": [],
            "assets_ids": [],
            "type": "subscribe",
            "channel": channel
        }

        await self._send_message(message)
        self._subscriptions.add(channel)

        vlogger.info("INGEST.WS.SUBSCRIBED", msg="订阅用户频道", extra={
            "channel": channel
        })

    async def subscribe_market(self, market_id: str) -> None:
        """
        订阅市场频道

        参数:
            market_id: 市场 ID (condition ID)
        """
        channel = ChannelType.MARKET.value

        message = {
            "auth": {},
            "markets": [market_id],
            "assets_ids": [],
            "type": "subscribe",
            "channel": channel
        }

        await self._send_message(message)
        self._subscriptions.add(f"{channel}:{market_id}")

        vlogger.info("INGEST.WS.SUBSCRIBED", msg="订阅市场频道", extra={
            "channel": channel,
            "market_id": market_id
        })

    async def subscribe_asset(self, asset_id: str, channel: ChannelType = ChannelType.MARKET) -> None:
        """
        订阅资产

        参数:
            asset_id: 资产 ID (token ID)
            channel: 频道类型
        """
        auth = {}
        if channel == ChannelType.USER:
            if not all([self.api_key, self.api_secret, self.api_passphrase]):
                raise ValueError("订阅 USER 频道需要提供 API 认证信息")
            auth = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "passphrase": self.api_passphrase
            }

        message = {
            "auth": auth,
            "markets": [],
            "assets_ids": [asset_id],
            "type": "subscribe",
            "channel": channel.value
        }

        await self._send_message(message)
        self._subscriptions.add(f"{channel.value}:asset:{asset_id}")

        vlogger.info("INGEST.WS.SUBSCRIBED", msg="订阅资产", extra={
            "channel": channel.value,
            "asset_id": asset_id
        })

    async def unsubscribe_market(self, market_id: str) -> None:
        """
        取消订阅市场频道

        参数:
            market_id: 市场 ID
        """
        channel = ChannelType.MARKET.value

        message = {
            "auth": {},
            "markets": [market_id],
            "assets_ids": [],
            "type": "unsubscribe",
            "channel": channel
        }

        await self._send_message(message)
        self._subscriptions.discard(f"{channel}:{market_id}")

        vlogger.info("INGEST.WS.UNSUBSCRIBED", msg="取消订阅市场频道", extra={
            "channel": channel,
            "market_id": market_id
        })

    async def unsubscribe_user(self) -> None:
        """取消订阅用户频道"""
        channel = ChannelType.USER.value

        message = {
            "auth": {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "passphrase": self.api_passphrase
            },
            "markets": [],
            "assets_ids": [],
            "type": "unsubscribe",
            "channel": channel
        }

        await self._send_message(message)
        self._subscriptions.discard(channel)

        vlogger.info("INGEST.WS.UNSUBSCRIBED", msg="取消订阅用户频道", extra={
            "channel": channel
        })

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """发送消息"""
        if not self._ws or not self._running:
            raise RuntimeError("WebSocket 未连接")

        try:
            await self._ws.send(json.dumps(message))
            vlogger.debug("INGEST.WS.MESSAGE_SENT", msg="发送消息", extra={
                "message_type": message.get("type"),
                "channel": message.get("channel")
            })
        except Exception as e:
            vlogger.error("INGEST.WS.SEND_FAILED", msg="发送消息失败",
                        error_code="E-WS-004", extra={"error": str(e)})
            raise

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    vlogger.error("INGEST.WS.PARSE_ERROR", msg="消息解析失败",
                                error_code="E-DATA-001", extra={"error": str(e), "message": message})
                except Exception as e:
                    vlogger.error("INGEST.WS.HANDLE_ERROR", msg="消息处理失败",
                                error_code="E-WS-005", extra={"error": str(e)})
        except asyncio.CancelledError:
            vlogger.debug("INGEST.WS.RECEIVE_CANCELLED", msg="接收循环已取消")
        except Exception as e:
            vlogger.error("INGEST.WS.RECEIVE_ERROR", msg="接收循环异常",
                        error_code="E-WS-006", extra={"error": str(e)})
            await self._handle_error(e)
            if self._running:
                await self._reconnect()

    async def _ping_loop(self) -> None:
        """心跳循环"""
        try:
            while self._running:
                await asyncio.sleep(self.config.ping_interval)
                if self._ws and self._running:
                    try:
                        pong = await self._ws.ping()
                        await asyncio.wait_for(pong, timeout=self.config.ping_timeout)
                        vlogger.debug("INGEST.WS.PING", msg="心跳成功")
                    except asyncio.TimeoutError:
                        vlogger.warn("INGEST.WS.PING_TIMEOUT", msg="心跳超时")
                        if self._running:
                            await self._reconnect()
                        break
        except asyncio.CancelledError:
            vlogger.debug("INGEST.WS.PING_CANCELLED", msg="心跳循环已取消")
        except Exception as e:
            vlogger.error("INGEST.WS.PING_ERROR", msg="心跳循环异常",
                        error_code="E-WS-007", extra={"error": str(e)})

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        event_type = data.get("event_type") or data.get("type")

        vlogger.debug("INGEST.WS.MESSAGE_RECEIVED", msg="收到消息", extra={
            "event_type": event_type,
            "data_keys": list(data.keys())
        })

        # 触发消息回调
        for callback in self._message_callbacks:
            try:
                callback(data)
            except Exception as e:
                vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="消息回调执行失败",
                            error_code="E-WS-008", extra={"error": str(e)})

    async def _handle_error(self, error: Exception) -> None:
        """处理错误"""
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="错误回调执行失败",
                            error_code="E-WS-009", extra={"error": str(e)})

    async def _reconnect(self) -> None:
        """重连"""
        if self._reconnect_count >= self.config.max_reconnect_attempts:
            vlogger.error("INGEST.WS.RECONNECT_FAILED", msg="达到最大重连次数",
                        error_code="E-WS-010", extra={
                            "reconnect_count": self._reconnect_count,
                            "max_attempts": self.config.max_reconnect_attempts
                        })
            await self.disconnect()
            return

        self._reconnect_count += 1

        vlogger.info("INGEST.WS.RECONNECTING", msg="正在重连", extra={
            "attempt": self._reconnect_count,
            "max_attempts": self.config.max_reconnect_attempts,
            "delay": self.config.reconnect_delay
        })

        await self.disconnect()
        await asyncio.sleep(self.config.reconnect_delay)

        try:
            await self.connect()

            # 重新订阅
            subscriptions = list(self._subscriptions)
            self._subscriptions.clear()

            for sub in subscriptions:
                if sub == ChannelType.USER.value:
                    await self.subscribe_user()
                elif sub.startswith(f"{ChannelType.MARKET.value}:"):
                    market_id = sub.split(":", 1)[1]
                    if market_id.startswith("asset:"):
                        asset_id = market_id.split(":", 1)[1]
                        await self.subscribe_asset(asset_id)
                    else:
                        await self.subscribe_market(market_id)

            vlogger.info("INGEST.WS.RECONNECTED", msg="重连成功", extra={
                "attempt": self._reconnect_count
            })

        except Exception as e:
            vlogger.error("INGEST.WS.RECONNECT_ERROR", msg="重连失败",
                        error_code="E-WS-011", extra={
                            "error": str(e),
                            "attempt": self._reconnect_count
                        })
            await self._reconnect()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._running and self._ws is not None and not self._ws.closed

    @property
    def subscriptions(self) -> Set[str]:
        """获取当前订阅列表"""
        return self._subscriptions.copy()
