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
    base_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws"
    ping_interval: int = 20  # 心跳间隔(秒)
    ping_timeout: int = 10  # 心跳超时(秒)
    reconnect_delay: int = 5  # 重连延迟(秒)
    max_reconnect_attempts: int = 10  # 最大重连次数
    message_queue_size: int = 1000  # 消息队列大小

    def get_url(self, channel: ChannelType) -> str:
        """根据频道类型获取对应的 WebSocket URL"""
        return f"{self.base_url}/{channel.value}"


class PolymarketWSClient:
    """
    Polymarket CLOB WebSocket 客户端

    功能:
    - 支持 USER 和 MARKET 频道订阅(使用不同的 WebSocket 端点)
    - USER 频道: wss://ws-subscriptions-clob.polymarket.com/ws/user
    - MARKET 频道: wss://ws-subscriptions-clob.polymarket.com/ws/market
    - 自动重连机制
    - 心跳保活
    - 消息回调处理
    - 订阅管理

    示例:
        # 市场频道(无需认证,自动连接到 /ws/market)
        client = PolymarketWSClient()
        client.on_message(lambda msg: print(msg))
        await client.subscribe_market("market_id")

        # 用户频道(需要认证,自动连接到 /ws/user)
        client = PolymarketWSClient()
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

        # 为不同频道维护独立的连接
        self._ws_user: Optional[WebSocketClientProtocol] = None
        self._ws_market: Optional[WebSocketClientProtocol] = None

        self._running_user = False
        self._running_market = False
        self._reconnect_count_user = 0
        self._reconnect_count_market = 0
        self._subscriptions: Set[str] = set()  # 已订阅的频道

        # 回调函数
        self._message_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        self._connect_callbacks: List[Callable[[], None]] = []
        self._disconnect_callbacks: List[Callable[[], None]] = []

        # 任务
        self._receive_task_user: Optional[asyncio.Task] = None
        self._receive_task_market: Optional[asyncio.Task] = None
        self._ping_task_user: Optional[asyncio.Task] = None
        self._ping_task_market: Optional[asyncio.Task] = None

        vlogger.info("INGEST.WS.INIT", msg="WebSocket 客户端初始化", extra={
            "base_url": self.config.base_url,
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

    async def _connect_channel(self, channel: ChannelType) -> None:
        """建立指定频道的 WebSocket 连接"""
        if channel == ChannelType.USER:
            if self._running_user:
                vlogger.warn("INGEST.WS.ALREADY_CONNECTED", msg="USER 频道已连接")
                return
            ws_attr = "_ws_user"
            running_attr = "_running_user"
            reconnect_attr = "_reconnect_count_user"
            receive_task_attr = "_receive_task_user"
            ping_task_attr = "_ping_task_user"
        else:
            if self._running_market:
                vlogger.warn("INGEST.WS.ALREADY_CONNECTED", msg="MARKET 频道已连接")
                return
            ws_attr = "_ws_market"
            running_attr = "_running_market"
            reconnect_attr = "_reconnect_count_market"
            receive_task_attr = "_receive_task_market"
            ping_task_attr = "_ping_task_market"

        try:
            url = self.config.get_url(channel)
            vlogger.info("INGEST.WS.CONNECTING", msg=f"正在连接 {channel.value.upper()} 频道", extra={
                "url": url,
                "channel": channel.value
            })

            ws = await websockets.connect(
                url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout
            )

            setattr(self, ws_attr, ws)
            setattr(self, running_attr, True)
            setattr(self, reconnect_attr, 0)

            vlogger.info("INGEST.WS.CONNECTED", msg=f"{channel.value.upper()} 频道连接成功", extra={
                "url": url,
                "channel": channel.value
            })

            # 触发连接回调
            for callback in self._connect_callbacks:
                try:
                    callback()
                except Exception as e:
                    vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="连接回调执行失败",
                                error_code="E-WS-001", extra={"error": str(e)})

            # 启动接收和心跳任务
            receive_task = asyncio.create_task(self._receive_loop(channel))
            ping_task = asyncio.create_task(self._ping_loop(channel))
            setattr(self, receive_task_attr, receive_task)
            setattr(self, ping_task_attr, ping_task)

        except Exception as e:
            vlogger.error("INGEST.WS.CONNECT_FAILED", msg=f"{channel.value.upper()} 频道连接失败",
                        error_code="E-WS-002", extra={"error": str(e), "channel": channel.value})
            await self._handle_error(e)
            raise

    async def _disconnect_channel(self, channel: ChannelType) -> None:
        """断开指定频道的 WebSocket 连接"""
        if channel == ChannelType.USER:
            if not self._running_user:
                return
            ws = self._ws_user
            running_attr = "_running_user"
            receive_task = self._receive_task_user
            ping_task = self._ping_task_user
        else:
            if not self._running_market:
                return
            ws = self._ws_market
            running_attr = "_running_market"
            receive_task = self._receive_task_market
            ping_task = self._ping_task_market

        vlogger.info("INGEST.WS.DISCONNECTING", msg=f"正在断开 {channel.value.upper()} 频道连接")

        setattr(self, running_attr, False)

        # 取消任务
        if receive_task:
            receive_task.cancel()
        if ping_task:
            ping_task.cancel()

        # 关闭连接
        if ws:
            await ws.close()
            if channel == ChannelType.USER:
                self._ws_user = None
            else:
                self._ws_market = None

        # 触发断开回调
        for callback in self._disconnect_callbacks:
            try:
                callback()
            except Exception as e:
                vlogger.error("INGEST.WS.CALLBACK_ERROR", msg="断开回调执行失败",
                            error_code="E-WS-003", extra={"error": str(e)})

        vlogger.info("INGEST.WS.DISCONNECTED", msg=f"{channel.value.upper()} 频道已断开")

    async def disconnect(self) -> None:
        """断开所有 WebSocket 连接"""
        await self._disconnect_channel(ChannelType.USER)
        await self._disconnect_channel(ChannelType.MARKET)

    async def subscribe_user(self) -> None:
        """
        订阅用户频道

        需要提供 API 认证信息
        """
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            raise ValueError("订阅 USER 频道需要提供 API 认证信息")

        # 先连接 USER 频道
        if not self._running_user:
            await self._connect_channel(ChannelType.USER)

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

        await self._send_message(message, ChannelType.USER)
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
        # 先连接 MARKET 频道
        if not self._running_market:
            await self._connect_channel(ChannelType.MARKET)

        channel = ChannelType.MARKET.value

        message = {
            "auth": {},
            "markets": [market_id],
            "assets_ids": [],
            "type": "subscribe",
            "channel": channel
        }

        await self._send_message(message, ChannelType.MARKET)
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
        # 先连接对应频道
        if channel == ChannelType.USER:
            if not self._running_user:
                await self._connect_channel(ChannelType.USER)
        else:
            if not self._running_market:
                await self._connect_channel(ChannelType.MARKET)

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

        await self._send_message(message, channel)
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

        await self._send_message(message, ChannelType.MARKET)
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

        await self._send_message(message, ChannelType.USER)
        self._subscriptions.discard(channel)

        vlogger.info("INGEST.WS.UNSUBSCRIBED", msg="取消订阅用户频道", extra={
            "channel": channel
        })

    async def _send_message(self, message: Dict[str, Any], channel: ChannelType) -> None:
        """发送消息到指定频道"""
        if channel == ChannelType.USER:
            ws = self._ws_user
            running = self._running_user
        else:
            ws = self._ws_market
            running = self._running_market

        if not ws or not running:
            raise RuntimeError(f"{channel.value.upper()} 频道未连接")

        try:
            await ws.send(json.dumps(message))
            vlogger.debug("INGEST.WS.MESSAGE_SENT", msg="发送消息", extra={
                "message_type": message.get("type"),
                "channel": message.get("channel")
            })
        except Exception as e:
            vlogger.error("INGEST.WS.SEND_FAILED", msg="发送消息失败",
                        error_code="E-WS-004", extra={"error": str(e), "channel": channel.value})
            raise

    async def _receive_loop(self, channel: ChannelType) -> None:
        """接收消息循环"""
        if channel == ChannelType.USER:
            ws = self._ws_user
            running_attr = "_running_user"
        else:
            ws = self._ws_market
            running_attr = "_running_market"

        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    vlogger.error("INGEST.WS.PARSE_ERROR", msg="消息解析失败",
                                error_code="E-DATA-001", extra={
                                    "error": str(e),
                                    "message": message,
                                    "channel": channel.value
                                })
                except Exception as e:
                    vlogger.error("INGEST.WS.HANDLE_ERROR", msg="消息处理失败",
                                error_code="E-WS-005", extra={
                                    "error": str(e),
                                    "channel": channel.value
                                })
        except asyncio.CancelledError:
            vlogger.debug("INGEST.WS.RECEIVE_CANCELLED", msg=f"{channel.value.upper()} 频道接收循环已取消")
        except Exception as e:
            vlogger.error("INGEST.WS.RECEIVE_ERROR", msg=f"{channel.value.upper()} 频道接收循环异常",
                        error_code="E-WS-006", extra={"error": str(e), "channel": channel.value})
            await self._handle_error(e)
            if getattr(self, running_attr):
                await self._reconnect(channel)

    async def _ping_loop(self, channel: ChannelType) -> None:
        """心跳循环"""
        if channel == ChannelType.USER:
            ws_attr = "_ws_user"
            running_attr = "_running_user"
        else:
            ws_attr = "_ws_market"
            running_attr = "_running_market"

        try:
            while getattr(self, running_attr):
                await asyncio.sleep(self.config.ping_interval)
                ws = getattr(self, ws_attr)
                if ws and getattr(self, running_attr):
                    try:
                        pong = await ws.ping()
                        await asyncio.wait_for(pong, timeout=self.config.ping_timeout)
                        vlogger.debug("INGEST.WS.PING", msg=f"{channel.value.upper()} 频道心跳成功")
                    except asyncio.TimeoutError:
                        vlogger.warn("INGEST.WS.PING_TIMEOUT", msg=f"{channel.value.upper()} 频道心跳超时")
                        if getattr(self, running_attr):
                            await self._reconnect(channel)
                        break
        except asyncio.CancelledError:
            vlogger.debug("INGEST.WS.PING_CANCELLED", msg=f"{channel.value.upper()} 频道心跳循环已取消")
        except Exception as e:
            vlogger.error("INGEST.WS.PING_ERROR", msg=f"{channel.value.upper()} 频道心跳循环异常",
                        error_code="E-WS-007", extra={"error": str(e), "channel": channel.value})

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

    async def _reconnect(self, channel: ChannelType) -> None:
        """重连指定频道"""
        if channel == ChannelType.USER:
            reconnect_count_attr = "_reconnect_count_user"
        else:
            reconnect_count_attr = "_reconnect_count_market"

        reconnect_count = getattr(self, reconnect_count_attr)

        if reconnect_count >= self.config.max_reconnect_attempts:
            vlogger.error("INGEST.WS.RECONNECT_FAILED", msg=f"{channel.value.upper()} 频道达到最大重连次数",
                        error_code="E-WS-010", extra={
                            "reconnect_count": reconnect_count,
                            "max_attempts": self.config.max_reconnect_attempts,
                            "channel": channel.value
                        })
            await self._disconnect_channel(channel)
            return

        setattr(self, reconnect_count_attr, reconnect_count + 1)

        vlogger.info("INGEST.WS.RECONNECTING", msg=f"{channel.value.upper()} 频道正在重连", extra={
            "attempt": reconnect_count + 1,
            "max_attempts": self.config.max_reconnect_attempts,
            "delay": self.config.reconnect_delay,
            "channel": channel.value
        })

        await self._disconnect_channel(channel)
        await asyncio.sleep(self.config.reconnect_delay)

        try:
            await self._connect_channel(channel)

            # 重新订阅该频道的订阅
            subscriptions = list(self._subscriptions)
            # 清除该频道的订阅记录
            self._subscriptions = {s for s in self._subscriptions if not s.startswith(channel.value)}

            for sub in subscriptions:
                if channel == ChannelType.USER and sub == ChannelType.USER.value:
                    await self.subscribe_user()
                elif channel == ChannelType.MARKET and sub.startswith(f"{ChannelType.MARKET.value}:"):
                    market_id = sub.split(":", 1)[1]
                    if market_id.startswith("asset:"):
                        asset_id = market_id.split(":", 1)[1]
                        await self.subscribe_asset(asset_id, ChannelType.MARKET)
                    else:
                        await self.subscribe_market(market_id)

            vlogger.info("INGEST.WS.RECONNECTED", msg=f"{channel.value.upper()} 频道重连成功", extra={
                "attempt": reconnect_count + 1,
                "channel": channel.value
            })

        except Exception as e:
            vlogger.error("INGEST.WS.RECONNECT_ERROR", msg=f"{channel.value.upper()} 频道重连失败",
                        error_code="E-WS-011", extra={
                            "error": str(e),
                            "attempt": reconnect_count + 1,
                            "channel": channel.value
                        })
            await self._reconnect(channel)

    @property
    def is_connected(self) -> bool:
        """是否已连接(任一频道连接即返回 True)"""
        user_connected = self._running_user and self._ws_user is not None and not self._ws_user.closed
        market_connected = self._running_market and self._ws_market is not None and not self._ws_market.closed
        return user_connected or market_connected

    @property
    def is_user_connected(self) -> bool:
        """USER 频道是否已连接"""
        return self._running_user and self._ws_user is not None and not self._ws_user.closed

    @property
    def is_market_connected(self) -> bool:
        """MARKET 频道是否已连接"""
        return self._running_market and self._ws_market is not None and not self._ws_market.closed

    @property
    def subscriptions(self) -> Set[str]:
        """获取当前订阅列表"""
        return self._subscriptions.copy()
