from backend.polymarket_api import PolymarketWSClient, ChannelType, MessageType
import asyncio

async def main():
    client = PolymarketWSClient()
    client.on_message(lambda msg: print(msg))
    await client.subscribe_market("0x3067050fc48008adbe0cb6624d55a8112a6a5a0416180af069ea9bef6745ae03")  # 替换为真实的市场 ID

if __name__ == "__main__":
    asyncio.run(main())