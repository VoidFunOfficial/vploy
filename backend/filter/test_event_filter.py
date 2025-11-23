"""
事件过滤器测试脚本

测试事件过滤器的各项功能：
1. 数据库初始化
2. 黑名单配置管理
3. 事件过滤流程
4. 已处理事件管理
"""

from . import (
    init_database,
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    filter_events,
    is_market_processed,
    clear_processed_markets,
)

from ..polymarket_api import Event


def test_database_init():
    """测试数据库初始化"""
    print("\n" + "="*60)
    print("测试 1: 数据库初始化")
    print("="*60)
    
    success = init_database()
    if success:
        print("✓ 数据库初始化成功")
    else:
        print("✗ 数据库初始化失败")
    
    return success


def test_blacklist_management():
    """测试黑名单配置管理"""
    print("\n" + "="*60)
    print("测试 2: 黑名单配置管理")
    print("="*60)
    
    # 获取所有黑名单
    print("\n2.1 获取所有黑名单配置:")
    blacklist = get_blacklist()
    for bl_type, values in blacklist.items():
        print(f"  {bl_type}: {values}")
    
    # 添加新的黑名单项
    print("\n2.2 添加新的黑名单项:")
    success = add_blacklist_item('tag', 'test_tag')
    if success:
        print("  ✓ 添加成功: tag = test_tag")
    else:
        print("  ✗ 添加失败或已存在")
    
    # 再次获取黑名单验证
    print("\n2.3 验证添加结果:")
    blacklist = get_blacklist('tag')
    print(f"  Tag 黑名单: {blacklist.get('tag', [])}")
    
    # 删除测试黑名单项
    print("\n2.4 删除测试黑名单项:")
    success = remove_blacklist_item('tag', 'test_tag')
    if success:
        print("  ✓ 删除成功")
    else:
        print("  ✗ 删除失败")
    
    return True


def test_event_filtering():
    """测试事件过滤流程"""
    print("\n" + "="*60)
    print("测试 3: 事件过滤流程")
    print("="*60)
    
    # 创建测试事件数据
    test_events = [
        Event(
            id="event_001",
            title="Bitcoin Price Prediction Market",
            slug="bitcoin-price-2024",
            description="Will Bitcoin reach $100,000 by end of 2024?",
            tags=[{"label": "crypto", "slug": "crypto"}],
        ),
        Event(
            id="event_002",
            title="US Presidential Election 2024",
            slug="us-election-2024",
            description="Who will win the 2024 US Presidential Election?",
            tags=[{"label": "elections", "slug": "elections"}],  # 应该被 tag 黑名单过滤
        ),
        Event(
            id="event_003",
            title="China Economic Growth",
            slug="china-gdp-2024",
            description="Will China's GDP growth exceed 5% in 2024?",
            tags=[{"label": "china", "slug": "china"}],  # 应该被 tag 黑名单过滤
        ),
        Event(
            id="event_004",
            title="Gold Price Market",
            slug="gold-price-2024",
            description="Will gold prices reach new highs?",
            tags=[{"label": "commodities", "slug": "commodities"}],
        ),
        Event(
            id="event_005",
            title="Ethereum Market",
            slug="ethereum-2024",
            description="Ethereum price predictions for 2024",
            tags=[{"label": "ethereum", "slug": "ethereum"}],
        ),
    ]
    
    print(f"\n3.1 输入事件数量: {len(test_events)}")
    for i, event in enumerate(test_events, 1):
        print(f"  {i}. {event.id}: {event.title}")
        print(f"     Tags: {[t.get('label', '') for t in (event.tags or [])]}")
    
    # 执行过滤
    print("\n3.2 执行过滤流程...")
    filtered_events = filter_events(test_events)
    
    print(f"\n3.3 过滤后事件数量: {len(filtered_events)}")
    for i, event in enumerate(filtered_events, 1):
        print(f"  {i}. {event.id}: {event.title}")
    
    # 验证过滤结果
    print("\n3.4 验证过滤结果:")
    expected_pass = ["event_001", "event_004", "event_005"]
    actual_pass = [e.id for e in filtered_events]
    
    print(f"  预期通过的事件: {', '.join(expected_pass)}")
    print(f"  实际通过的事件: {', '.join(actual_pass)}")
    
    if set(actual_pass) == set(expected_pass):
        print("  ✓ 过滤结果正确")
    else:
        print("  ✗ 过滤结果不符合预期")
    
    return True


def test_processed_events():
    """测试已处理事件管理"""
    print("\n" + "="*60)
    print("测试 4: 已处理事件管理")
    print("="*60)
    
    # 检查事件是否已处理
    print("\n4.1 检查事件处理状态:")
    test_event_id = "event_001"
    is_processed = is_market_processed(test_event_id)
    print(f"  {test_event_id} 是否已处理: {is_processed}")
    
    # 清理已处理事件记录
    print("\n4.2 清理已处理事件记录:")
    count = clear_processed_markets()
    print(f"  清理了 {count} 条记录")
    
    # 再次检查
    print("\n4.3 清理后再次检查:")
    is_processed = is_market_processed(test_event_id)
    print(f"  {test_event_id} 是否已处理: {is_processed}")
    
    return True


def test_with_real_data():
    """测试使用真实数据"""
    print("\n" + "="*60)
    print("测试 5: 使用真实 API 数据")
    print("="*60)
    
    try:
        from polymarket_api import PolymarketGammaClient
        
        # 创建客户端
        client = PolymarketGammaClient()
        
        # 获取最新事件
        print("\n5.1 获取最新事件...")
        events = client.get_new_events(limit=10)
        print(f"  获取到 {len(events)} 个事件")
        
        # 显示前3个事件
        print("\n5.2 前3个事件:")
        for i, event in enumerate(events[:3], 1):
            print(f"  {i}. {event.title}")
            print(f"     ID: {event.id}")
            tags = event.tags or []
            tag_labels = [t.get('label', '') for t in tags if isinstance(t, dict)]
            print(f"     Tags: {tag_labels}")
        
        # 执行过滤
        print("\n5.3 执行过滤...")
        filtered_events = filter_events(events)
        
        print(f"\n5.4 过滤结果:")
        print(f"  输入: {len(events)} 个事件")
        print(f"  输出: {len(filtered_events)} 个事件")
        print(f"  过滤率: {(1 - len(filtered_events)/len(events))*100:.1f}%")
        
        # 显示通过过滤的事件
        if filtered_events:
            print("\n5.5 通过过滤的事件:")
            for i, event in enumerate(filtered_events[:3], 1):
                print(f"  {i}. {event.title}")
        
        return True
        
    except Exception as e:
        print(f"\n  ⚠ 无法获取真实数据: {str(e)}")
        print("  （这是正常的，如果 API 不可用）")
        return True


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("事件过滤器模块测试")
    print("="*60)
    
    try:
        # 测试 1: 数据库初始化
        if not test_database_init():
            print("\n✗ 数据库初始化失败，终止测试")
            return
        
        # 测试 2: 黑名单配置管理
        test_blacklist_management()
        
        # 测试 3: 事件过滤流程
        test_event_filtering()
        
        # 测试 4: 已处理事件管理
        test_processed_events()
        
        # 测试 5: 使用真实数据
        test_with_real_data()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

