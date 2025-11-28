"""
Polymarket 便捷交易函数

提供高级交易功能,包括:
- 冰山订单 (Iceberg Order): 大额订单分批执行,避免市场冲击
- 其他高级交易策略

主要功能:
- 订单分片管理
- WebSocket 实时监听订单成交
- 自动补单机制
- 完整的异常处理和日志记录
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger

# 导入 CLOB API
from .clob_api import (
    get_client,
    create_limit_order,
    post_order,
    cancel_order,
    get_order,
    BUY,
    SELL
)

# 导入 WebSocket 客户端
from .wss_client import PolymarketWSClient, MessageType


# ==================== 数据结构 ====================

class IcebergOrderStatus(Enum):
    """冰山订单状态枚举"""
    PENDING = "PENDING"           # 待执行: 订单已创建,等待首次下单
    ACTIVE = "ACTIVE"             # 执行中: 正在执行订单片段
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交: 部分订单已成交
    COMPLETED = "COMPLETED"       # 已完成: 全部订单已成交
    CANCELLED = "CANCELLED"       # 已取消: 订单被取消
    FAILED = "FAILED"             # 失败: 订单执行失败


class SliceStatus(Enum):
    """订单片段状态枚举"""
    PENDING = "PENDING"           # 待提交
    SUBMITTED = "SUBMITTED"       # 已提交
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    FILLED = "FILLED"             # 完全成交
    CANCELLED = "CANCELLED"       # 已取消
    FAILED = "FAILED"             # 失败


@dataclass
class OrderSlice:
    """
    订单片段数据结构

    属性:
        slice_id: 片段ID
        size: 片段数量
        price: 片段价格
        status: 片段状态
        order_id: CLOB订单ID
        filled_size: 已成交数量
        created_at: 创建时间
        submitted_at: 提交时间
        filled_at: 成交时间
        error_message: 错误信息
    """
    slice_id: int
    size: float
    price: float
    status: SliceStatus = SliceStatus.PENDING
    order_id: Optional[str] = None
    filled_size: float = 0.0
    created_at: float = field(default_factory=time.time)
    submitted_at: Optional[float] = None
    filled_at: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class IcebergOrder:
    """
    冰山订单数据结构

    属性:
        token_id: 交易对的token ID
        price: 挂单价格
        total_size: 冰山单总数量
        display_size: 每次显示的挂单数量
        side: 买卖方向 (BUY/SELL)
        status: 订单状态
        slices: 订单片段列表
        total_filled: 总成交数量
        created_at: 创建时间
        started_at: 开始执行时间
        completed_at: 完成时间
        error_message: 错误信息
        metadata: 额外元数据
    """
    token_id: str
    price: float
    total_size: float
    display_size: float
    side: str
    status: IcebergOrderStatus = IcebergOrderStatus.PENDING
    slices: List[OrderSlice] = field(default_factory=list)
    total_filled: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_size(self) -> float:
        """剩余未成交数量"""
        return self.total_size - self.total_filled

    @property
    def fill_percentage(self) -> float:
        """成交百分比"""
        if self.total_size <= 0:
            return 0.0
        return (self.total_filled / self.total_size) * 100.0

    @property
    def active_slice(self) -> Optional[OrderSlice]:
        """获取当前活跃的订单片段"""
        for slice in reversed(self.slices):
            if slice.status in [SliceStatus.SUBMITTED, SliceStatus.PARTIALLY_FILLED]:
                return slice
        return None


# ==================== 冰山订单管理器 ====================

class IcebergOrderManager:
    """
    冰山订单管理器

    负责管理冰山订单的生命周期,包括:
    - 订单片段创建和提交
    - WebSocket 监听订单成交
    - 自动补单机制
    - 异常处理和重试
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None
    ):
        """
        初始化冰山订单管理器

        参数:
            api_key: CLOB API Key
            api_secret: CLOB API Secret
            api_passphrase: CLOB API Passphrase
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

        # WebSocket 客户端
        self._ws_client: Optional[PolymarketWSClient] = None
        self._ws_connected = False

        # 订单追踪
        self._active_orders: Dict[str, IcebergOrder] = {}  # order_id -> IcebergOrder

        vlogger.info("ICEBERG.MANAGER.INIT", msg="冰山订单管理器初始化", extra={
            "has_auth": bool(api_key and api_secret and api_passphrase)
        })

    async def _init_websocket(self) -> None:
        """初始化 WebSocket 连接"""
        if self._ws_connected:
            return


        vlogger.info("ICEBERG.WS.INIT", msg="初始化 WebSocket 连接")

        try:
            self._ws_client = PolymarketWSClient()

            # 注册消息回调
            self._ws_client.on_message(self._handle_ws_message)
            self._ws_client.on_error(self._handle_ws_error)
            self._ws_client.on_disconnect(self._handle_ws_disconnect)

            # 连接并订阅用户频道
            await self._ws_client.connect()
            await self._ws_client.subscribe_user()

            self._ws_connected = True

            vlogger.info("ICEBERG.WS.CONNECTED", msg="WebSocket 连接成功")

        except Exception as e:
            error_msg = f"WebSocket 连接失败: {str(e)}"
            vlogger.error("ICEBERG.WS.CONNECT_ERROR", msg=error_msg, error_code="E-ICEBERG-001", extra={
                "error": str(e)
            })
            raise

    async def _close_websocket(self) -> None:
        """关闭 WebSocket 连接"""
        if self._ws_client and self._ws_connected:
            vlogger.info("ICEBERG.WS.CLOSING", msg="关闭 WebSocket 连接")
            await self._ws_client.disconnect()
            self._ws_connected = False
            self._ws_client = None

    def _handle_ws_message(self, msg: Dict[str, Any]) -> None:
        """处理 WebSocket 消息"""
        event_type = msg.get("event_type") or msg.get("type")

        # 只处理订单相关消息
        if event_type not in [MessageType.TRADE.value, MessageType.ORDER_UPDATE.value]:
            return

        order_id = msg.get("id")
        if not order_id:
            return

        # 查找对应的冰山订单
        iceberg_order = None
        for order in self._active_orders.values():
            active_slice = order.active_slice
            if active_slice and active_slice.order_id == order_id:
                iceberg_order = order
                break

        if not iceberg_order:
            return

        # 处理订单更新
        if event_type == MessageType.ORDER_UPDATE.value:
            self._handle_order_update(iceberg_order, msg)
        elif event_type == MessageType.TRADE.value:
            self._handle_trade(iceberg_order, msg)

    def _handle_order_update(self, iceberg_order: IcebergOrder, msg: Dict[str, Any]) -> None:
        """处理订单更新消息"""
        active_slice = iceberg_order.active_slice
        if not active_slice:
            return

        size_matched = float(msg.get("size_matched", 0))
        original_size = float(msg.get("original_size", active_slice.size))

        # 更新片段成交数量
        active_slice.filled_size = size_matched

        # 更新片段状态
        if size_matched >= original_size:
            active_slice.status = SliceStatus.FILLED
            active_slice.filled_at = time.time()

            vlogger.trade("ICEBERG.SLICE.FILLED", msg="订单片段完全成交", extra={
                "token_id": iceberg_order.token_id,
                "slice_id": active_slice.slice_id,
                "size": active_slice.size,
                "price": active_slice.price,
                "side": iceberg_order.side
            })
        elif size_matched > 0:
            active_slice.status = SliceStatus.PARTIALLY_FILLED

            vlogger.info("ICEBERG.SLICE.PARTIAL", msg="订单片段部分成交", extra={
                "token_id": iceberg_order.token_id,
                "slice_id": active_slice.slice_id,
                "filled_size": size_matched,
                "total_size": original_size,
                "fill_percentage": (size_matched / original_size) * 100
            })

        # 更新冰山订单总成交量
        self._update_iceberg_filled(iceberg_order)

    def _handle_trade(self, iceberg_order: IcebergOrder, msg: Dict[str, Any]) -> None:
        """处理交易消息"""
        trade_size = float(msg.get("size", 0))
        trade_price = float(msg.get("price", 0))

        vlogger.trade("ICEBERG.TRADE", msg="订单成交", extra={
            "token_id": iceberg_order.token_id,
            "size": trade_size,
            "price": trade_price,
            "side": iceberg_order.side,
            "total_filled": iceberg_order.total_filled,
            "total_size": iceberg_order.total_size
        })

    def _handle_ws_error(self, error: Exception) -> None:
        """处理 WebSocket 错误"""
        vlogger.error("ICEBERG.WS.ERROR", msg="WebSocket 错误", error_code="E-ICEBERG-002", extra={
            "error": str(error)
        })

    def _handle_ws_disconnect(self) -> None:
        """处理 WebSocket 断开连接"""
        self._ws_connected = False
        vlogger.warn("ICEBERG.WS.DISCONNECTED", msg="WebSocket 连接断开")

    def _update_iceberg_filled(self, iceberg_order: IcebergOrder) -> None:
        """更新冰山订单总成交量"""
        total_filled = sum(slice.filled_size for slice in iceberg_order.slices)
        iceberg_order.total_filled = total_filled

        # 检查是否完全成交
        if total_filled >= iceberg_order.total_size:
            iceberg_order.status = IcebergOrderStatus.COMPLETED
            iceberg_order.completed_at = time.time()

            vlogger.trade("ICEBERG.ORDER.COMPLETED", msg="冰山订单完全成交", extra={
                "token_id": iceberg_order.token_id,
                "total_size": iceberg_order.total_size,
                "total_filled": total_filled,
                "price": iceberg_order.price,
                "side": iceberg_order.side,
                "duration_seconds": iceberg_order.completed_at - iceberg_order.started_at
            })
        elif total_filled > 0:
            iceberg_order.status = IcebergOrderStatus.PARTIALLY_FILLED

    async def _submit_slice(self, iceberg_order: IcebergOrder, slice: OrderSlice) -> bool:
        """
        提交订单片段

        参数:
            iceberg_order: 冰山订单
            slice: 订单片段

        返回:
            bool: 是否提交成功
        """
        try:
            vlogger.info("ICEBERG.SLICE.SUBMIT", msg="提交订单片段", extra={
                "token_id": iceberg_order.token_id,
                "slice_id": slice.slice_id,
                "size": slice.size,
                "price": slice.price,
                "side": iceberg_order.side
            })

            # 创建限价订单
            signed_order = create_limit_order(
                token_id=iceberg_order.token_id,
                price=slice.price,
                size=slice.size,
                side=iceberg_order.side
            )

            # 提交订单
            response = post_order(signed_order)

            # 更新片段状态
            slice.order_id = response.get("orderID") or response.get("id")
            slice.status = SliceStatus.SUBMITTED
            slice.submitted_at = time.time()

            vlogger.info("ICEBERG.SLICE.SUBMITTED", msg="订单片段提交成功", extra={
                "token_id": iceberg_order.token_id,
                "slice_id": slice.slice_id,
                "order_id": slice.order_id,
                "size": slice.size,
                "price": slice.price
            })

            return True

        except Exception as e:
            error_msg = f"订单片段提交失败: {str(e)}"
            slice.status = SliceStatus.FAILED
            slice.error_message = error_msg

            vlogger.error("ICEBERG.SLICE.SUBMIT_ERROR", msg=error_msg, error_code="E-ICEBERG-003", extra={
                "token_id": iceberg_order.token_id,
                "slice_id": slice.slice_id,
                "error": str(e)
            })

            return False

    async def _execute_iceberg_order(self, iceberg_order: IcebergOrder) -> None:
        """
        执行冰山订单

        参数:
            iceberg_order: 冰山订单
        """
        iceberg_order.status = IcebergOrderStatus.ACTIVE
        iceberg_order.started_at = time.time()

        vlogger.info("ICEBERG.ORDER.START", msg="开始执行冰山订单", extra={
            "token_id": iceberg_order.token_id,
            "total_size": iceberg_order.total_size,
            "display_size": iceberg_order.display_size,
            "price": iceberg_order.price,
            "side": iceberg_order.side
        })

        try:
            # 初始化 WebSocket
            await self._init_websocket()

            # 循环执行订单片段
            while iceberg_order.remaining_size > 0:
                # 检查订单状态
                if iceberg_order.status in [IcebergOrderStatus.CANCELLED, IcebergOrderStatus.FAILED]:
                    break

                # 计算下一个片段的大小
                next_size = min(iceberg_order.display_size, iceberg_order.remaining_size)

                # 创建订单片段
                slice = OrderSlice(
                    slice_id=len(iceberg_order.slices),
                    size=next_size,
                    price=iceberg_order.price
                )
                iceberg_order.slices.append(slice)

                # 提交订单片段
                success = await self._submit_slice(iceberg_order, slice)

                if not success:
                    # 提交失败,标记订单为失败
                    iceberg_order.status = IcebergOrderStatus.FAILED
                    iceberg_order.error_message = f"订单片段 {slice.slice_id} 提交失败"
                    break

                # 等待当前片段完全成交
                await self._wait_for_slice_fill(iceberg_order, slice)

                # 检查是否已完全成交
                if iceberg_order.status == IcebergOrderStatus.COMPLETED:
                    break

            # 最终状态检查
            if iceberg_order.status == IcebergOrderStatus.ACTIVE:
                if iceberg_order.total_filled >= iceberg_order.total_size:
                    iceberg_order.status = IcebergOrderStatus.COMPLETED
                    iceberg_order.completed_at = time.time()
                elif iceberg_order.total_filled > 0:
                    iceberg_order.status = IcebergOrderStatus.PARTIALLY_FILLED

        except Exception as e:
            error_msg = f"冰山订单执行异常: {str(e)}"
            iceberg_order.status = IcebergOrderStatus.FAILED
            iceberg_order.error_message = error_msg

            vlogger.error("ICEBERG.ORDER.ERROR", msg=error_msg, error_code="E-ICEBERG-004", extra={
                "token_id": iceberg_order.token_id,
                "error": str(e)
            })

    async def _wait_for_slice_fill(
        self,
        iceberg_order: IcebergOrder,
        slice: OrderSlice,
        timeout: float = 300.0,  # 5分钟超时
        check_interval: float = 1.0  # 每秒检查一次
    ) -> None:
        """
        等待订单片段成交

        参数:
            iceberg_order: 冰山订单
            slice: 订单片段
            timeout: 超时时间(秒)
            check_interval: 检查间隔(秒)
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 检查片段状态
            if slice.status == SliceStatus.FILLED:
                return

            # 检查订单状态
            if iceberg_order.status in [IcebergOrderStatus.CANCELLED, IcebergOrderStatus.FAILED]:
                return

            # 等待一段时间
            await asyncio.sleep(check_interval)

            # 主动查询订单状态(作为备份机制)
            if slice.order_id:
                try:
                    order_info = get_order(slice.order_id)
                    size_matched = float(order_info.get("size_matched", 0))

                    # 更新片段成交数量
                    slice.filled_size = size_matched

                    # 更新片段状态
                    if size_matched >= slice.size:
                        slice.status = SliceStatus.FILLED
                        slice.filled_at = time.time()
                        self._update_iceberg_filled(iceberg_order)
                        return
                    elif size_matched > 0:
                        slice.status = SliceStatus.PARTIALLY_FILLED
                        self._update_iceberg_filled(iceberg_order)

                except Exception as e:
                    vlogger.warn("ICEBERG.SLICE.QUERY_ERROR", msg="查询订单状态失败", extra={
                        "order_id": slice.order_id,
                        "error": str(e)
                    })

        # 超时处理
        vlogger.warn("ICEBERG.SLICE.TIMEOUT", msg="订单片段等待超时", extra={
            "token_id": iceberg_order.token_id,
            "slice_id": slice.slice_id,
            "timeout_seconds": timeout,
            "filled_size": slice.filled_size,
            "total_size": slice.size
        })

    async def execute_iceberg_order(
        self,
        token_id: str,
        price: float,
        total_size: float,
        display_size: float,
        side: str
    ) -> IcebergOrder:
        """
        执行冰山订单

        参数:
            token_id: 交易对的token ID
            price: 挂单价格
            total_size: 冰山单总数量
            display_size: 每次显示的挂单数量
            side: 买卖方向 (BUY/SELL)

        返回:
            IcebergOrder: 冰山订单对象

        异常:
            ValueError: 参数无效
            Exception: 执行失败
        """
        # 参数验证
        if total_size <= 0:
            raise ValueError("total_size 必须大于 0")

        if display_size <= 0:
            raise ValueError("display_size 必须大于 0")

        if display_size > total_size:
            raise ValueError("display_size 不能大于 total_size")

        if price <= 0 or price >= 1:
            raise ValueError("price 必须在 (0, 1) 范围内")

        if side not in [BUY, SELL]:
            raise ValueError(f"side 必须是 BUY 或 SELL, 当前值: {side}")

        # 创建冰山订单
        iceberg_order = IcebergOrder(
            token_id=token_id,
            price=price,
            total_size=total_size,
            display_size=display_size,
            side=side
        )

        # 添加到活跃订单列表
        order_key = f"{token_id}_{int(time.time() * 1000)}"
        self._active_orders[order_key] = iceberg_order

        try:
            # 执行订单
            await self._execute_iceberg_order(iceberg_order)

        finally:
            # 从活跃订单列表中移除
            self._active_orders.pop(order_key, None)

        return iceberg_order

    async def cancel_iceberg_order(self, iceberg_order: IcebergOrder) -> bool:
        """
        取消冰山订单

        参数:
            iceberg_order: 冰山订单

        返回:
            bool: 是否取消成功
        """
        vlogger.info("ICEBERG.ORDER.CANCEL", msg="取消冰山订单", extra={
            "token_id": iceberg_order.token_id,
            "total_filled": iceberg_order.total_filled,
            "total_size": iceberg_order.total_size
        })

        try:
            # 取消活跃的订单片段
            active_slice = iceberg_order.active_slice
            if active_slice and active_slice.order_id:
                try:
                    cancel_order(active_slice.order_id)
                    active_slice.status = SliceStatus.CANCELLED

                    vlogger.info("ICEBERG.SLICE.CANCELLED", msg="订单片段已取消", extra={
                        "slice_id": active_slice.slice_id,
                        "order_id": active_slice.order_id
                    })
                except Exception as e:
                    vlogger.warn("ICEBERG.SLICE.CANCEL_ERROR", msg="取消订单片段失败", extra={
                        "slice_id": active_slice.slice_id,
                        "order_id": active_slice.order_id,
                        "error": str(e)
                    })

            # 更新订单状态
            iceberg_order.status = IcebergOrderStatus.CANCELLED
            iceberg_order.completed_at = time.time()

            vlogger.info("ICEBERG.ORDER.CANCELLED", msg="冰山订单已取消", extra={
                "token_id": iceberg_order.token_id,
                "total_filled": iceberg_order.total_filled,
                "total_size": iceberg_order.total_size
            })

            return True

        except Exception as e:
            error_msg = f"取消冰山订单失败: {str(e)}"
            vlogger.error("ICEBERG.ORDER.CANCEL_ERROR", msg=error_msg, error_code="E-ICEBERG-005", extra={
                "token_id": iceberg_order.token_id,
                "error": str(e)
            })
            return False

    async def close(self) -> None:
        """关闭管理器,清理资源"""
        await self._close_websocket()


# ==================== 便捷函数 ====================

async def iceberg_order(
    token_id: str,
    price: float,
    total_size: float,
    display_size: float,
    side: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    api_passphrase: Optional[str] = None
) -> IcebergOrder:
    """
    执行冰山订单的便捷函数

    参数:
        token_id: 交易对的token ID
        price: 挂单价格
        total_size: 冰山单总数量
        display_size: 每次显示的挂单数量
        side: 买卖方向 (BUY/SELL)
        api_key: CLOB API Key (可选,如果不提供则从环境变量读取)
        api_secret: CLOB API Secret (可选,如果不提供则从环境变量读取)
        api_passphrase: CLOB API Passphrase (可选,如果不提供则从环境变量读取)

    返回:
        IcebergOrder: 冰山订单对象

    示例:
        >>> import asyncio
        >>> from backend.polymarket_api.easy_trade import iceberg_order, BUY
        >>>
        >>> async def main():
        >>>     order = await iceberg_order(
        >>>         token_id="21742633143463906290569050155826241533067272736897614950488156847949938836455",
        >>>         price=0.55,
        >>>         total_size=1000.0,
        >>>         display_size=100.0,
        >>>         side=BUY
        >>>     )
        >>>     print(f"订单状态: {order.status}")
        >>>     print(f"成交数量: {order.total_filled}/{order.total_size}")
        >>>
        >>> asyncio.run(main())

    异常:
        ValueError: 参数无效
        Exception: 执行失败
    """
    manager = IcebergOrderManager(
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase
    )

    try:
        order = await manager.execute_iceberg_order(
            token_id=token_id,
            price=price,
            total_size=total_size,
            display_size=display_size,
            side=side
        )
        return order
    finally:
        await manager.close()


# ==================== 模块导出 ====================

__all__ = [
    # 数据结构
    "IcebergOrder",
    "IcebergOrderStatus",
    "OrderSlice",
    "SliceStatus",

    # 管理器
    "IcebergOrderManager",

    # 便捷函数
    "iceberg_order",

    # 常量
    "BUY",
    "SELL",
]
