# -*- coding: utf-8 -*-
"""
测试 position_listener 模块的增强功能

测试内容:
1. 订单监控 - 自动删除不存在的订单
2. 市场监控 - 价格涨幅检测
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.position_listener import (
    OrderMonitor,
    MarketMonitor,
    PositionDatabase,
    TradeRecorder,
    record_trade,
    create_order_record
)
from backend.types import TradeAllocation
from backend.position_listener.models import Position, PositionStatus


def test_order_auto_delete():
    """测试订单自动删除功能"""
    print("\n" + "="*60)
    print("测试1: 订单监控 - 自动删除不存在的订单")
    print("="*60)
    
    # 创建一个不存在的订单ID
    fake_order_id = "0xFAKE_ORDER_ID_12345"
    
    # 先在数据库中创建一个订单记录
    db = PositionDatabase()
    
    # 创建一个测试持仓
    allocation = TradeAllocation(
        id="test_market_001",
        side="YES",
        price=0.55,
        p=0.60,
        b=1.82,
        f=0.05,
        invest=100.0,
        shares=181.82,
        settle_day=30
    )
    
    position_id = record_trade(allocation)
    print(f"✓ 创建测试持仓: position_id={position_id}")
    
    # 创建订单记录
    create_order_record(
        order_id=fake_order_id,
        position_id=position_id,
        market_id="test_market_001",
        token_id="test_token_001"
    )
    print(f"✓ 创建测试订单记录: order_id={fake_order_id}")
    
    # 验证订单存在
    order = db.get_order_by_id(fake_order_id)
    if order:
        print(f"✓ 订单记录已创建: {order.order_id}")
    
    # 模拟监控不存在的订单（API会返回None）
    print(f"\n开始监控订单（模拟API返回空结果）...")
    monitor = OrderMonitor(db)
    
    # 注意: 这里会实际调用API，如果订单不存在，会触发自动删除
    # 在实际测试中，由于fake_order_id不存在，API会返回None
    result = monitor.monitor_order(fake_order_id)
    
    print(f"监控结果: {result}")
    
    # 验证订单是否被删除
    order_after = db.get_order_by_id(fake_order_id)
    if order_after is None:
        print(f"✓ 订单记录已自动删除")
    else:
        print(f"✗ 订单记录仍然存在")
    
    print("\n测试1完成!")


def test_price_surge_detection():
    """测试价格涨幅检测功能"""
    print("\n" + "="*60)
    print("测试2: 市场监控 - 价格涨幅检测")
    print("="*60)
    
    db = PositionDatabase()
    recorder = TradeRecorder(db)
    monitor = MarketMonitor(db, recorder)
    
    # 创建一个测试持仓
    allocation = TradeAllocation(
        id="test_market_002",
        side="YES",
        price=0.50,  # 入场价格 0.50
        p=0.60,
        b=1.82,
        f=0.05,
        invest=100.0,
        shares=200.0,
        settle_day=30
    )
    
    position_id = record_trade(allocation)
    print(f"✓ 创建测试持仓: position_id={position_id}")
    
    position = db.get_position(position_id)
    print(f"  入场价格: {position.entry_price}")
    print(f"  持仓数量: {position.shares}")
    
    # 模拟价格上涨超过10%
    print(f"\n模拟价格变化...")
    
    # 测试1: 价格上涨5% (不触发)
    new_price_1 = 0.525  # 上涨5%
    recorder.update_position_price(position_id, new_price_1)
    position = db.get_position(position_id)
    price_change_pct_1 = (new_price_1 - position.entry_price) / position.entry_price
    print(f"  价格更新到 {new_price_1} (涨幅 {price_change_pct_1*100:.2f}%) - 不触发预警")
    
    # 测试2: 价格上涨15% (触发)
    new_price_2 = 0.575  # 上涨15%
    print(f"\n  价格更新到 {new_price_2}...")
    recorder.update_position_price(position_id, new_price_2)
    position = db.get_position(position_id)
    price_change_pct_2 = (new_price_2 - position.entry_price) / position.entry_price
    
    # 手动触发涨幅检测
    if abs(price_change_pct_2) > monitor.PRICE_SURGE_THRESHOLD:
        print(f"  ✓ 检测到价格涨幅超过阈值: {price_change_pct_2*100:.2f}% > {monitor.PRICE_SURGE_THRESHOLD*100:.2f}%")
        monitor._handle_price_surge(position, price_change_pct_2)
    
    # 测试3: 价格下跌12% (触发)
    new_price_3 = 0.44  # 下跌12%
    print(f"\n  价格更新到 {new_price_3}...")
    recorder.update_position_price(position_id, new_price_3)
    position = db.get_position(position_id)
    price_change_pct_3 = (new_price_3 - position.entry_price) / position.entry_price
    
    if abs(price_change_pct_3) > monitor.PRICE_SURGE_THRESHOLD:
        print(f"  ✓ 检测到价格跌幅超过阈值: {price_change_pct_3*100:.2f}% > {monitor.PRICE_SURGE_THRESHOLD*100:.2f}%")
        monitor._handle_price_surge(position, price_change_pct_3)
    
    print("\n测试2完成!")


if __name__ == "__main__":
    print("\n开始测试 position_listener 模块增强功能...")
    
    try:
        # 测试1: 订单自动删除
        # 注意: 这个测试会实际调用Polymarket API
        # test_order_auto_delete()
        print("\n提示: test_order_auto_delete() 已注释，因为会调用实际API")
        
        # 测试2: 价格涨幅检测
        test_price_surge_detection()
        
        print("\n" + "="*60)
        print("所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

