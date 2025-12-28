"""
数据获取模块

通过 Polymarket API 获取市场实时数据和历史数据，用于止盈决策。
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime, timedelta

from ..polymarket_api import (
    PolymarketOrderbookClient,
    GammaMarketsAPI,
    get_last_trade_price
)
from ..sys_configs.global_event_reg import vlogger


def get_market_realtime_data(
    token_id: str
) -> Dict[str, Any]:
    """
    获取市场实时数据（当前价格、订单簿深度、点差）

    参数:
        token_id: Token ID（已经是具体的YES或NO token地址）

    返回:
        Dict包含:
            - current_price: 当前价格（使用bid价格，即卖出价）
            - bid_depth: 买单深度
            - ask_depth: 卖单深度
            - spread: 点差
            - mid_price: 中间价
    """
    try:
        with PolymarketOrderbookClient() as client:
            # 获取订单簿
            orderbook = client.get_orderbook(token_id)

            # 获取价格和点差
            spread_info = client.get_spread(token_id)
            mid_price = client.get_midpoint(token_id)

            # 计算订单簿深度
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            # 计算前5档深度
            bid_depth = sum(float(b.get('size', 0)) for b in bids[:5]) if bids else 0.0
            ask_depth = sum(float(a.get('size', 0)) for a in asks[:5]) if asks else 0.0

            # 使用bid价格（卖出时能获得的价格）
            current_price = spread_info.get('bid', mid_price)

            result = {
                'current_price': float(current_price),
                'bid_depth': float(bid_depth),
                'ask_depth': float(ask_depth),
                'spread': float(spread_info.get('spread', 0)),
                'mid_price': float(mid_price)
            }

            vlogger.info(
                "SURPLUS.DATA.REALTIME",
                msg="获取实时市场数据成功",
                extra={
                    "token_id": token_id,
                    "price": result['current_price']
                }
            )

            return result

    except Exception as e:
        vlogger.error(
            "SURPLUS.DATA.REALTIME.ERROR",
            msg="获取实时市场数据失败",
            error_code="E-SURPLUS-001",
            extra={
                "token_id": token_id,
                "error": str(e)
            }
        )
        raise


def get_market_history_data(
    token_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    interval: str = "1h",
    fidelity: int = 60
) -> Dict[str, List[float]]:
    """
    获取市场历史数据（价格序列、交易量序列、点差序列）

    参数:
        token_id: Token ID
        start_time: 开始时间
        end_time: 结束时间
        interval: 时间间隔 ("1h", "6h", "1d", "1w", "1m", "max")
        fidelity: 数据分辨率（分钟）

    返回:
        Dict包含:
            - prices: 价格序列
            - volumes: 交易量序列（估算）
            - spreads: 点差序列（估算）
            - timestamps: 时间戳序列
    """
    try:
        with PolymarketOrderbookClient() as client:
            # 构建查询参数
            if start_time and end_time:
                # 使用时间戳范围
                start_ts = int(start_time.timestamp())
                end_ts = int(end_time.timestamp())
                history = client.get_prices_history(
                    market=token_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    fidelity=fidelity
                )
            else:
                # 使用时间间隔
                history = client.get_prices_history(
                    market=token_id,
                    interval=interval,
                    fidelity=fidelity
                )

            # 解析历史数据
            history_data = history.get('history', [])

            if not history_data:
                vlogger.warn(
                    "SURPLUS.DATA.HISTORY.EMPTY",
                    msg="历史数据为空",
                    extra={"token_id": token_id}
                )
                return {
                    'prices': [],
                    'volumes': [],
                    'spreads': [],
                    'timestamps': []
                }

            # 提取价格和时间戳
            prices = [float(point.get('p', 0)) for point in history_data]
            timestamps = [int(point.get('t', 0)) for point in history_data]

            # 估算交易量（基于价格变化幅度）
            volumes = []
            for i in range(len(prices)):
                if i == 0:
                    volumes.append(1.0)
                else:
                    # 价格变化越大，假设交易量越大
                    price_change = abs(prices[i] - prices[i-1])
                    volume = max(1.0, price_change * 1000)
                    volumes.append(volume)

            # 估算点差（基于价格波动率）
            spreads = []
            window = min(10, len(prices))
            for i in range(len(prices)):
                if i < window:
                    spread = 0.01  # 默认点差
                else:
                    # 基于最近窗口的波动率估算点差
                    recent_prices = prices[i-window:i]
                    volatility = np.std(recent_prices)
                    spread = max(0.005, min(0.05, volatility * 2))
                spreads.append(spread)

            result = {
                'prices': prices,
                'volumes': volumes,
                'spreads': spreads,
                'timestamps': timestamps
            }

            vlogger.info(
                "SURPLUS.DATA.HISTORY",
                msg="获取历史市场数据成功",
                extra={
                    "token_id": token_id,
                    "data_points": len(prices),
                    "interval": interval
                }
            )

            return result

    except Exception as e:
        vlogger.error(
            "SURPLUS.DATA.HISTORY.ERROR",
            msg="获取历史市场数据失败",
            error_code="E-SURPLUS-002",
            extra={
                "token_id": token_id,
                "error": str(e)
            }
        )
        raise


def prepare_decision_data(
    token_id: str,
    entry_time: datetime,
    lookback_hours: int = 168  # 默认回看7天
) -> Dict[str, Any]:
    """
    准备止盈决策所需的完整数据

    参数:
        token_id: Token ID（已经是具体的YES或NO token地址）
        entry_time: 入场时间
        lookback_hours: 回看时长（小时）

    返回:
        Dict包含所有决策所需数据
    """
    try:
        # 计算时间范围
        end_time = datetime.now()
        start_time = entry_time - timedelta(hours=lookback_hours)

        # 获取历史数据
        history = get_market_history_data(
            token_id=token_id,
            start_time=start_time,
            end_time=end_time,
            fidelity=60  # 1小时分辨率
        )

        # 获取实时数据
        realtime = get_market_realtime_data(token_id=token_id)

        # 找到entry_time对应的索引
        entry_ts = int(entry_time.timestamp())
        timestamps = history['timestamps']

        # 找到最接近entry_time的索引
        entry_index = 0
        if timestamps:
            entry_index = min(
                range(len(timestamps)),
                key=lambda i: abs(timestamps[i] - entry_ts)
            )

        result = {
            'prices': history['prices'],
            'volumes': history['volumes'],
            'spreads': history['spreads'],
            'timestamps': history['timestamps'],
            'entry_index': entry_index,
            'current_price': realtime['current_price'],
            'current_bid_depth': realtime['bid_depth'],
            'current_ask_depth': realtime['ask_depth'],
            'current_spread': realtime['spread']
        }

        vlogger.info(
            "SURPLUS.DATA.PREPARE",
            msg="准备决策数据成功",
            extra={
                "token_id": token_id,
                "entry_index": entry_index,
                "data_points": len(history['prices'])
            }
        )

        return result

    except Exception as e:
        vlogger.error(
            "SURPLUS.DATA.PREPARE.ERROR",
            msg="准备决策数据失败",
            error_code="E-SURPLUS-003",
            extra={
                "token_id": token_id,
                "error": str(e)
            }
        )
        raise