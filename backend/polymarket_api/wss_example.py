"""
Polymarket WebSocket 客户端使用示例

演示如何使用 PolymarketWSClient 订阅市场数据和用户订单流
"""

import asyncio
from backend.polymarket_api import PolymarketWSClient, ChannelType, MessageType


async def example_market_channel():
    """
    示例 1: 订阅市场频道（无需认证）
    
    订阅市场的订单簿、价格变化、最新成交价等实时数据
    """
    print("=== 示例 1: 市场频道订阅 ===\n")
    
    # 创建客户端（无需认证）
    client = PolymarketWSClient()
    
    # 注册消息回调
    def on_message(msg):
        event_type = msg.get("event_type") or msg.get("type")
        
        if event_type == MessageType.BOOK.value:
            # 订单簿消息
            print(f"📖 订单簿更新:")
            print(f"  市场: {msg.get('market')}")
            print(f"  资产: {msg.get('asset_id')}")
            print(f"  买单数: {len(msg.get('buys', []))}")
            print(f"  卖单数: {len(msg.get('sells', []))}")
            
        elif event_type == MessageType.PRICE_CHANGE.value:
            # 价格变化消息
            print(f"💰 价格变化:")
            for change in msg.get("price_changes", []):
                print(f"  资产: {change.get('asset_id')}")
                print(f"  价格: {change.get('price')}")
                print(f"  方向: {change.get('side')}")
                
        elif event_type == MessageType.LAST_TRADE_PRICE.value:
            # 最新成交价消息
            print(f"🔔 最新成交:")
            print(f"  市场: {msg.get('market')}")
            print(f"  价格: {msg.get('price')}")
            print(f"  数量: {msg.get('size')}")
            print(f"  方向: {msg.get('side')}")
            
        elif event_type == MessageType.TICK_SIZE_CHANGE.value:
            # 最小价格变动单位变化
            print(f"📏 Tick Size 变化:")
            print(f"  资产: {msg.get('asset_id')}")
            print(f"  旧值: {msg.get('old_tick_size')}")
            print(f"  新值: {msg.get('new_tick_size')}")
        
        print()
    
    # 注册连接/断开回调
    client.on_message(on_message)
    client.on_connect(lambda: print("✅ WebSocket 已连接\n"))
    client.on_disconnect(lambda: print("❌ WebSocket 已断开\n"))
    client.on_error(lambda e: print(f"⚠️ 错误: {e}\n"))
    
    try:
        # 连接 WebSocket
        await client.connect()
        
        # 订阅市场（使用实际的市场 ID）
        market_id = "0x1234567890abcdef"  # 替换为真实的市场 ID
        await client.subscribe_market(market_id)
        
        print(f"📡 已订阅市场: {market_id}\n")
        
        # 运行 30 秒
        await asyncio.sleep(30)
        
    finally:
        # 断开连接
        await client.disconnect()


async def example_user_channel():
    """
    示例 2: 订阅用户频道（需要认证）
    
    订阅用户的订单和交易记录实时更新
    """
    print("=== 示例 2: 用户频道订阅 ===\n")
    
    # 创建客户端（需要提供 API 认证信息）
    client = PolymarketWSClient(
        api_key="your_api_key",
        api_secret="your_api_secret",
        api_passphrase="your_api_passphrase"
    )
    
    # 注册消息回调
    def on_message(msg):
        event_type = msg.get("event_type") or msg.get("type")
        
        if event_type == MessageType.TRADE.value:
            # 交易消息
            print(f"💸 交易执行:")
            print(f"  市场: {msg.get('market')}")
            print(f"  价格: {msg.get('price')}")
            print(f"  数量: {msg.get('size')}")
            print(f"  方向: {msg.get('side')}")
            print(f"  状态: {msg.get('status')}")
            
        elif event_type in [MessageType.ORDER_PLACEMENT.value, 
                           MessageType.ORDER_UPDATE.value,
                           MessageType.ORDER_CANCELLATION.value]:
            # 订单消息
            print(f"📝 订单 {event_type}:")
            print(f"  订单ID: {msg.get('id')}")
            print(f"  市场: {msg.get('market')}")
            print(f"  价格: {msg.get('price')}")
            print(f"  原始数量: {msg.get('original_size')}")
            print(f"  已成交: {msg.get('size_matched')}")
            print(f"  方向: {msg.get('side')}")
        
        print()
    
    client.on_message(on_message)
    client.on_connect(lambda: print("✅ WebSocket 已连接\n"))
    client.on_disconnect(lambda: print("❌ WebSocket 已断开\n"))
    client.on_error(lambda e: print(f"⚠️ 错误: {e}\n"))
    
    try:
        # 连接 WebSocket
        await client.connect()
        
        # 订阅用户频道
        await client.subscribe_user()
        
        print("📡 已订阅用户频道\n")
        
        # 运行 30 秒
        await asyncio.sleep(30)
        
    finally:
        # 断开连接
        await client.disconnect()


async def example_multiple_markets():
    """
    示例 3: 订阅多个市场
    
    同时订阅多个市场的实时数据
    """
    print("=== 示例 3: 多市场订阅 ===\n")
    
    client = PolymarketWSClient()
    
    # 消息计数器
    message_count = {}
    
    def on_message(msg):
        event_type = msg.get("event_type") or msg.get("type")
        market = msg.get("market", "unknown")
        
        # 统计消息数量
        key = f"{market}:{event_type}"
        message_count[key] = message_count.get(key, 0) + 1
        
        # 每 10 条消息打印一次统计
        total = sum(message_count.values())
        if total % 10 == 0:
            print(f"📊 消息统计 (总计: {total}):")
            for k, v in sorted(message_count.items()):
                print(f"  {k}: {v}")
            print()
    
    client.on_message(on_message)
    client.on_connect(lambda: print("✅ WebSocket 已连接\n"))
    
    try:
        await client.connect()
        
        # 订阅多个市场
        markets = [
            "0x1234567890abcdef",  # 替换为真实的市场 ID
            "0xabcdef1234567890",
            "0x9876543210fedcba",
        ]
        
        for market_id in markets:
            await client.subscribe_market(market_id)
            print(f"📡 已订阅市场: {market_id}")
        
        print()
        
        # 运行 60 秒
        await asyncio.sleep(60)
        
        # 取消订阅第一个市场
        print(f"🔕 取消订阅市场: {markets[0]}\n")
        await client.unsubscribe_market(markets[0])
        
        # 再运行 30 秒
        await asyncio.sleep(30)
        
    finally:
        await client.disconnect()


async def example_asset_subscription():
    """
    示例 4: 订阅资产（Token ID）
    
    直接订阅特定资产的实时数据
    """
    print("=== 示例 4: 资产订阅 ===\n")
    
    client = PolymarketWSClient()
    
    def on_message(msg):
        event_type = msg.get("event_type") or msg.get("type")
        asset_id = msg.get("asset_id", "unknown")
        print(f"📦 资产 {asset_id} - {event_type}")
    
    client.on_message(on_message)
    client.on_connect(lambda: print("✅ WebSocket 已连接\n"))
    
    try:
        await client.connect()
        
        # 订阅资产
        asset_id = "123456789"  # 替换为真实的 Token ID
        await client.subscribe_asset(asset_id, ChannelType.MARKET)
        
        print(f"📡 已订阅资产: {asset_id}\n")
        
        # 运行 30 秒
        await asyncio.sleep(30)
        
    finally:
        await client.disconnect()


async def main():
    """主函数 - 运行所有示例"""
    print("\n" + "="*60)
    print("Polymarket WebSocket 客户端使用示例")
    print("="*60 + "\n")
    
    # 选择要运行的示例
    print("请选择示例:")
    print("1. 市场频道订阅（无需认证）")
    print("2. 用户频道订阅（需要认证）")
    print("3. 多市场订阅")
    print("4. 资产订阅")
    print()
    
    choice = input("请输入选项 (1-4): ").strip()
    
    if choice == "1":
        await example_market_channel()
    elif choice == "2":
        await example_user_channel()
    elif choice == "3":
        await example_multiple_markets()
    elif choice == "4":
        await example_asset_subscription()
    else:
        print("无效选项")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())

