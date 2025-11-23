"""
Polymarket CLOB API 客户端封装（需要身份验证）

该模块提供了对 Polymarket CLOB (Central Limit Order Book) API 的封装，
专注于需要身份验证的订单管理和账户操作功能。

主要功能：
- 全局客户端实例管理（单例模式）
- 订单创建、提交、取消（需要身份验证）
- 交易记录查询（需要身份验证）
- 账户余额和授权查询（需要身份验证）
- 服务器时间同步

注意：
- 本模块的所有功能都需要身份验证（私钥）
- 无需身份验证的公开查询功能（订单簿、价格、市场数据等）请使用 orderbook_api 模块
"""

import os
from typing import Optional, Dict, List, Any, Union
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    OrderArgs, MarketOrderArgs, OrderType,
    TradeParams, OpenOrderParams, BalanceAllowanceParams, AssetType, BookParams,
    PartialCreateOrderOptions
)
from py_clob_client.order_builder.constants import BUY, SELL
from py_order_utils.model import SignedOrder

# 导入全局 VLogger 实例
from backend.sys_configs.global_event_reg import vlogger




# ==================== 配置常量 ====================

# CLOB API 端点
HOST = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")

# 链 ID (137 = Polygon Mainnet, 80002 = Amoy Testnet)
CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))

# 私钥（从环境变量读取）
PRIVATE_KEY = os.getenv("PK", "0xc8cf499fdb0fc33c316dcecfe0338d1faf7f896422bb54396a59f33638ab4dbf")

# 代理资金地址
PROXY_FUNDER = os.getenv("PROXY_FUNDER", "0x72E84A3675A23CE1eAbb2b4B8ca94F7Bb025584A")


# ==================== 全局客户端实例 ====================

_global_client: Optional[ClobClient] = None


def get_client(
    host: Optional[str] = None,
    key: Optional[str] = None,
    chain_id: Optional[int] = None,
    signature_type: int = 1,
    funder: Optional[str] = None,
    force_new: bool = False
) -> ClobClient:
    """
    获取全局 CLOB 客户端实例（单例模式）

    参数:
        host (str): CLOB API 端点，默认使用环境变量或 https://clob.polymarket.com
        key (str): 钱包私钥，默认从环境变量 PK 读取
        chain_id (int): 链 ID，默认 137 (Polygon Mainnet)
        signature_type (int): 签名类型，1 表示 email/Magic wallet 签名
        funder (str): 代理资金地址
        force_new (bool): 是否强制创建新实例，默认 False

    返回:
        ClobClient: CLOB 客户端实例


    异常:
        ValueError: 如果缺少必要的配置参数
    """
    global _global_client

    # 如果已有实例且不强制创建新实例，直接返回
    if _global_client is not None and not force_new:
        return _global_client

    # 使用提供的参数或默认值
    host = host or HOST
    key = key or PRIVATE_KEY
    chain_id = chain_id or CHAIN_ID
    funder = funder or PROXY_FUNDER

    # 验证必要参数
    if not key:
        error_msg = "缺少私钥配置，请设置环境变量 PK 或传入 key 参数"
        vlogger.error("CLOB.CLIENT.INIT_ERROR", msg=error_msg, error_code="E-CLOB-001")
        raise ValueError(error_msg)

    # 创建客户端实例
    _global_client = ClobClient(
        host=host,
        key=key,
        chain_id=chain_id,
        signature_type=1,
        funder=funder
    )
    

    # 使用 L1 签名，创建或派生 API 凭证
    api_creds = _global_client.create_or_derive_api_creds()
    _global_client.set_api_creds(api_creds)

    vlogger.info("CLOB.CLIENT.INIT", msg="CLOB 客户端初始化成功", extra={
        "host": host,
        "chain_id": chain_id
    })

    return _global_client


# ==================== 订单管理接口 ====================

def create_limit_order(
    token_id: str,
    price: float,
    size: float,
    side: str,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> SignedOrder:
    """
    创建限价订单

    参数:
        token_id (str): 代币 ID
        price (float): 订单价格
        size (float): 订单数量
        side (str): 订单方向，BUY 或 SELL
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        SignedOrder: 签名后的订单对象

    异常:
        ValueError: 如果参数无效
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CREATE_LIMIT", msg="创建限价订单", extra={
        "token_id": token_id,
        "price": price,
        "size": size,
        "side": side,
        "neg_risk": neg_risk
    })

    order_args = OrderArgs(
        price=price,
        size=size,
        side=side,
        token_id=token_id
    )

    # 如果指定了 neg_risk，则传入 PartialCreateOrderOptions
    options = None
    if neg_risk is not None:
        options = PartialCreateOrderOptions(neg_risk=neg_risk)

    signed_order = client.create_order(order_args, options)

    vlogger.info("CLOB.ORDER.CREATE_SUCCESS", msg="限价订单创建成功", extra={
        "order_salt": str(signed_order.order.salt)
    })

    return signed_order


def create_market_order(
    token_id: str,
    amount: float,
    side: str,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> SignedOrder:
    """
    创建市价订单

    参数:
        token_id (str): 代币 ID
        amount (float): 订单金额（以 USDC 计价）
        side (str): 订单方向，BUY 或 SELL
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        SignedOrder: 签名后的订单对象

    异常:
        ValueError: 如果参数无效
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CREATE_MARKET", msg="创建市价订单", extra={
        "token_id": token_id,
        "amount": amount,
        "side": side,
        "neg_risk": neg_risk
    })

    order_args = MarketOrderArgs(
        token_id=token_id,
        amount=amount,
        side=side
    )

    # 如果指定了 neg_risk，则传入 PartialCreateOrderOptions
    options = None
    if neg_risk is not None:
        options = PartialCreateOrderOptions(neg_risk=neg_risk)

    signed_order = client.create_market_order(order_args, options)

    vlogger.info("CLOB.ORDER.CREATE_SUCCESS", msg="市价订单创建成功", extra={
        "order_salt": str(signed_order.order.salt)
    })

    return signed_order


def post_order(
    signed_order: SignedOrder,
    order_type: Optional[OrderType] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    提交订单到交易所

    参数:
        signed_order (SignedOrder): 签名后的订单对象
        order_type (OrderType): 订单类型（GTC, FOK, GTD 等），可选
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单提交响应

    异常:
        Exception: 如果订单提交失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.POST", msg="提交订单到交易所", extra={
        "order_salt": str(signed_order.order.salt),
        "order_type": str(order_type) if order_type else "default"
    })

    try:
        if order_type:
            response = client.post_order(signed_order, orderType=order_type)
        else:
            response = client.post_order(signed_order)

        vlogger.info("CLOB.ORDER.POST_SUCCESS", msg="订单提交成功", extra={
            "order_salt": str(signed_order.order.salt),
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"订单提交失败: {str(e)}"
        vlogger.error("CLOB.ORDER.POST_ERROR", msg=error_msg, extra={
            "order_salt": str(signed_order.order.salt),
            "error": str(e)
        })
        raise


def cancel_order(
    order_id: str,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    取消单个订单

    参数:
        order_id (str): 订单 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 取消订单响应

    异常:
        Exception: 如果取消订单失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CANCEL", msg="取消单个订单", extra={
        "order_id": order_id
    })

    try:
        response = client.cancel(order_id=order_id)

        vlogger.info("CLOB.ORDER.CANCEL_SUCCESS", msg="订单取消成功", extra={
            "order_id": order_id,
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"取消订单失败: {str(e)}"
        vlogger.error("CLOB.ORDER.CANCEL_ERROR", msg=error_msg, extra={
            "order_id": order_id,
            "error": str(e)
        })
        raise


def cancel_orders(
    order_ids: List[str],
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    批量取消订单

    参数:
        order_ids (List[str]): 订单 ID 列表
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 取消订单响应

    异常:
        Exception: 如果取消订单失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CANCEL_BATCH", msg="批量取消订单", extra={
        "order_ids": order_ids,
        "count": len(order_ids)
    })

    try:
        response = client.cancel_orders(order_ids=order_ids)

        vlogger.info("CLOB.ORDER.CANCEL_BATCH_SUCCESS", msg="批量取消订单成功", extra={
            "order_ids": order_ids,
            "count": len(order_ids),
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"批量取消订单失败: {str(e)}"
        vlogger.error("CLOB.ORDER.CANCEL_BATCH_ERROR", msg=error_msg, extra={
            "order_ids": order_ids,
            "count": len(order_ids),
            "error": str(e)
        })
        raise


def cancel_all_orders(
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    取消所有订单

    参数:
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 取消订单响应

    异常:
        Exception: 如果取消订单失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CANCEL_ALL", msg="取消所有订单")

    try:
        response = client.cancel_all()

        vlogger.info("CLOB.ORDER.CANCEL_ALL_SUCCESS", msg="取消所有订单成功", extra={
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"取消所有订单失败: {str(e)}"
        vlogger.error("CLOB.ORDER.CANCEL_ALL_ERROR", msg=error_msg, extra={
            "error": str(e)
        })
        raise


def cancel_market_orders(
    market: str,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    取消指定市场的所有订单

    参数:
        market (str): 市场 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 取消订单响应

    异常:
        Exception: 如果取消订单失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CANCEL_MARKET", msg="取消指定市场的所有订单", extra={
        "market": market
    })

    try:
        response = client.cancel_market_orders(market=market)

        vlogger.info("CLOB.ORDER.CANCEL_MARKET_SUCCESS", msg="取消市场订单成功", extra={
            "market": market,
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"取消市场订单失败: {str(e)}"
        vlogger.error("CLOB.ORDER.CANCEL_MARKET_ERROR", msg=error_msg, extra={
            "market": market,
            "error": str(e)
        })
        raise

    client = client or get_client()
    # 时间戳
    expiration = int(time.time()) + expiration
    order_args = OrderArgs(
        price=price,
        size=amount,
        side=BUY,
        token_id=token_id,
        expiration=expiration,
    )
    signed_order = client.create_order(order_args)
    resp = client.post_order(signed_order, OrderType.GTD)
    vlogger.info("CLOB.ORDER.LIMIT_BUY_SUCCESS", msg="限价买入订单创建成功", extra={
        "token_id": token_id,
        "amount": amount,
        "price": price,
        "response": resp
    })
    return resp
# ==================== 订单查询接口 ====================

def get_order(
    order_id: str,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    查询单个订单详情

    参数:
        order_id (str): 订单 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单详情

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.GET", msg="查询单个订单详情", extra={
        "order_id": order_id
    })

    try:
        response = client.get_order(order_id=order_id)

        vlogger.info("CLOB.ORDER.GET_SUCCESS", msg="查询订单成功", extra={
            "order_id": order_id,
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"查询订单失败: {str(e)}"
        vlogger.error("CLOB.ORDER.GET_ERROR", msg=error_msg, extra={
            "order_id": order_id,
            "error": str(e)
        })
        raise


def get_orders(
    market: Optional[str] = None,
    client: Optional[ClobClient] = None
) -> List[Dict[str, Any]]:
    """
    查询订单列表

    参数:
        market (str): 市场 ID，如果指定则只返回该市场的订单
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        List[dict]: 订单列表

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.GET_LIST", msg="查询订单列表", extra={
        "market": market
    })

    try:
        if market:
            params = OpenOrderParams(market=market)
            response = client.get_orders(params)
        else:
            response = client.get_orders()

        vlogger.info("CLOB.ORDER.GET_LIST_SUCCESS", msg="查询订单列表成功", extra={
            "market": market,
            "count": len(response) if isinstance(response, list) else "unknown"
        })

        return response

    except Exception as e:
        error_msg = f"查询订单列表失败: {str(e)}"
        vlogger.error("CLOB.ORDER.GET_LIST_ERROR", msg=error_msg, extra={
            "market": market,
            "error": str(e)
        })
        raise

# ==================== 交易记录查询接口 ====================

def get_trades(
    market: Optional[str] = None,
    maker_address: Optional[str] = None,
    client: Optional[ClobClient] = None
) -> List[Dict[str, Any]]:
    """
    查询交易记录

    参数:
        market (str): 市场 ID，可选
        maker_address (str): Maker 地址，可选（默认使用当前账户地址）
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        List[dict]: 交易记录列表

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.TRADE.GET_LIST", msg="查询交易记录", extra={
        "market": market,
        "maker_address": maker_address
    })

    try:
        # 如果没有指定 maker_address，使用当前账户地址
        if maker_address is None:
            maker_address = client.get_address()

        params = TradeParams(
            maker_address=maker_address,
            market=market
        )
        response = client.get_trades(params)

        vlogger.info("CLOB.TRADE.GET_LIST_SUCCESS", msg="查询交易记录成功", extra={
            "market": market,
            "maker_address": maker_address,
            "count": len(response) if isinstance(response, list) else "unknown"
        })

        return response

    except Exception as e:
        error_msg = f"查询交易记录失败: {str(e)}"
        vlogger.error("CLOB.TRADE.GET_LIST_ERROR", msg=error_msg, extra={
            "market": market,
            "maker_address": maker_address,
            "error": str(e)
        })
        raise


def get_last_trade_price(
    token_id: str,
    client: Optional[ClobClient] = None
) -> float:
    """
    获取最后成交价格

    参数:
        token_id (str): 代币 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        float: 最后成交价格

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.TRADE.GET_LAST_PRICE", msg="查询最后成交价格", extra={
        "token_id": token_id
    })

    try:
        response = client.get_last_trade_price(token_id)

        vlogger.info("CLOB.TRADE.GET_LAST_PRICE_SUCCESS", msg="查询最后成交价格成功", extra={
            "token_id": token_id,
            "price": response
        })

        return response

    except Exception as e:
        error_msg = f"查询最后成交价格失败: {str(e)}"
        vlogger.error("CLOB.TRADE.GET_LAST_PRICE_ERROR", msg=error_msg, extra={
            "token_id": token_id,
            "error": str(e)
        })
        raise


# ==================== 账户余额查询接口 ====================

def get_balance_allowance(
    asset_type: AssetType,
    token_id: Optional[str] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    查询账户余额和授权额度

    参数:
        asset_type (AssetType): 资产类型（COLLATERAL 或 CONDITIONAL）
        token_id (str): 代币 ID，当 asset_type 为 CONDITIONAL 时必需
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 余额和授权额度信息

    异常:
        ValueError: 如果参数无效
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.BALANCE.GET_ALLOWANCE", msg="查询账户余额和授权额度", extra={
        "asset_type": str(asset_type),
        "token_id": token_id
    })

    try:
        if asset_type == AssetType.CONDITIONAL and not token_id:
            raise ValueError("查询 CONDITIONAL 资产时必须提供 token_id")

        params = BalanceAllowanceParams(
            asset_type=asset_type,
            token_id=token_id
        )
        response = client.get_balance_allowance(params=params)

        vlogger.info("CLOB.BALANCE.GET_ALLOWANCE_SUCCESS", msg="查询余额和授权额度成功", extra={
            "asset_type": str(asset_type),
            "token_id": token_id,
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"查询余额失败: {str(e)}"
        vlogger.error("CLOB.BALANCE.GET_ALLOWANCE_ERROR", msg=error_msg, extra={
            "asset_type": str(asset_type),
            "token_id": token_id,
            "error": str(e)
        })
        raise


def get_collateral_balance(
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    查询抵押品（USDC）余额

    参数:
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 抵押品余额信息

    异常:
        Exception: 如果查询失败
    """
    vlogger.info("CLOB.BALANCE.GET_COLLATERAL", msg="查询抵押品余额")
    return get_balance_allowance(AssetType.COLLATERAL, client=client)


def get_conditional_balance(
    token_id: str,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    查询条件代币余额

    参数:
        token_id (str): 代币 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 条件代币余额信息

    异常:
        Exception: 如果查询失败
    """
    vlogger.info("CLOB.BALANCE.GET_CONDITIONAL", msg="查询条件代币余额", extra={
        "token_id": token_id
    })
    return get_balance_allowance(AssetType.CONDITIONAL, token_id=token_id, client=client)


# ==================== 其他辅助接口 ====================

def get_server_time(
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    获取服务器时间

    参数:
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 服务器时间信息

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.SERVER.GET_TIME", msg="查询服务器时间")

    try:
        response = client.get_server_time()

        vlogger.info("CLOB.SERVER.GET_TIME_SUCCESS", msg="查询服务器时间成功", extra={
            "response": response
        })

        return response

    except Exception as e:
        error_msg = f"查询服务器时间失败: {str(e)}"
        vlogger.error("CLOB.SERVER.GET_TIME_ERROR", msg=error_msg, extra={
            "error": str(e)
        })
        raise


def get_address(
    client: Optional[ClobClient] = None
) -> str:
    """
    获取当前账户地址

    参数:
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        str: 账户地址
    """
    client = client or get_client()
    address = client.get_address()

    vlogger.info("CLOB.ACCOUNT.GET_ADDRESS", msg="获取当前账户地址", extra={
        "address": address
    })

    return address


def is_order_scoring(
    order_id: str,
    client: Optional[ClobClient] = None
) -> bool:
    """
    检查订单是否正在评分

    参数:
        order_id (str): 订单 ID
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        bool: 如果订单正在评分返回 True

    异常:
        Exception: 如果查询失败
    """
    client = client or get_client()

    vlogger.info("CLOB.ORDER.CHECK_SCORING", msg="检查订单是否正在评分", extra={
        "order_id": order_id
    })

    try:
        response = client.is_order_scoring(order_id)

        vlogger.info("CLOB.ORDER.CHECK_SCORING_SUCCESS", msg="查询订单评分状态成功", extra={
            "order_id": order_id,
            "is_scoring": response
        })

        return response

    except Exception as e:
        error_msg = f"查询订单评分状态失败: {str(e)}"
        vlogger.error("CLOB.ORDER.CHECK_SCORING_ERROR", msg=error_msg, extra={
            "order_id": order_id,
            "error": str(e)
        })
        raise


# ==================== 便捷函数 ====================

def place_limit_buy_order(
    token_id: str,
    price: float,
    size: float,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    下限价买单的便捷函数

    参数:
        token_id (str): 代币 ID
        price (float): 订单价格
        size (float): 订单数量
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单提交响应
    """
    vlogger.info("CLOB.ORDER.PLACE_LIMIT_BUY", msg="下限价买单", extra={
        "token_id": token_id,
        "price": price,
        "size": size,
        "neg_risk": neg_risk
    })

    signed_order = create_limit_order(token_id, price, size, BUY, neg_risk, client)
    return post_order(signed_order, client=client)


def place_limit_sell_order(
    token_id: str,
    price: float,
    size: float,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    下限价卖单的便捷函数

    参数:
        token_id (str): 代币 ID
        price (float): 订单价格
        size (float): 订单数量
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单提交响应
    """
    vlogger.info("CLOB.ORDER.PLACE_LIMIT_SELL", msg="下限价卖单", extra={
        "token_id": token_id,
        "price": price,
        "size": size,
        "neg_risk": neg_risk
    })

    signed_order = create_limit_order(token_id, price, size, SELL, neg_risk, client)
    return post_order(signed_order, client=client)


def place_market_buy_order(
    token_id: str,
    amount: float,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    下市价买单的便捷函数（FOK 订单）

    参数:
        token_id (str): 代币 ID
        amount (float): 订单金额（以 USDC 计价）
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单提交响应
    """
    vlogger.info("CLOB.ORDER.PLACE_MARKET_BUY", msg="下市价买单", extra={
        "token_id": token_id,
        "amount": amount,
        "neg_risk": neg_risk
    })

    signed_order = create_market_order(token_id, amount, BUY, neg_risk, client)
    return post_order(signed_order, order_type=OrderType.FOK, client=client)


def place_market_sell_order(
    token_id: str,
    amount: float,
    neg_risk: Optional[bool] = None,
    client: Optional[ClobClient] = None
) -> Dict[str, Any]:
    """
    下市价卖单的便捷函数（FOK 订单）

    参数:
        token_id (str): 代币 ID
        amount (float): 订单金额（以 USDC 计价）
        neg_risk (bool): 是否为负风险市场，如果为 None 则自动检测
        client (ClobClient): 客户端实例，如果为 None 则使用全局实例

    返回:
        dict: 订单提交响应
    """
    vlogger.info("CLOB.ORDER.PLACE_MARKET_SELL", msg="下市价卖单", extra={
        "token_id": token_id,
        "amount": amount,
        "neg_risk": neg_risk
    })

    signed_order = create_market_order(token_id, amount, SELL, neg_risk, client)
    return post_order(signed_order, order_type=OrderType.FOK, client=client)


# ==================== 模块导出 ====================

__all__ = [
    # 客户端管理
    "get_client",
    "get_address",

    # 订单创建
    "create_limit_order",
    "create_market_order",
    "post_order",

    # 订单取消
    "cancel_order",
    "cancel_orders",
    "cancel_all_orders",
    "cancel_market_orders",

    # 订单查询
    "get_order",
    "get_orders",
    "is_order_scoring",

    # 交易记录（需要身份验证）
    "get_trades",
    "get_last_trade_price",

    # 账户余额
    "get_balance_allowance",
    "get_collateral_balance",
    "get_conditional_balance",

    # 其他
    "get_server_time",

    # 便捷函数
    "place_limit_buy_order",
    "place_limit_sell_order",
    "place_market_buy_order",
    "place_market_sell_order",

    # 常量
    "BUY",
    "SELL",
    "AssetType",
    "OrderType",
]
