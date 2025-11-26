"""
持仓监听功能测试脚本
"""

from backend.position_listen import add_position_to_listen
from backend.sys_configs import (
    get_position_listen_list,
    update_position_listen,
    remove_position_listen,
    deactivate_position_listen,
    clear_position_listen_list,
    init_config_database
)


def test_position_listen():
    """测试持仓监听功能"""
    
    print("=" * 60)
    print("持仓监听功能测试")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n1. 初始化数据库...")
    success = init_config_database()
    print(f"   数据库初始化: {'成功' if success else '失败'}")
    
    # 2. 添加持仓监听
    print("\n2. 添加持仓监听...")
    test_cases = [
        {
            "market_id": "0x1234567890abcdef",
            "buy_price": 0.65,
            "buy_side": "YES",
            "marks": "AI预测概率0.75, Kelly建议投入$500"
        },
        {
            "market_id": "0xabcdef1234567890",
            "buy_price": 0.42,
            "buy_side": "NO",
            "marks": "低风险市场, 预期收益15%"
        },
        {
            "market_id": "0x9876543210fedcba",
            "buy_price": 0.58,
            "buy_side": "YES",
            "marks": "高流动性市场"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        success = add_position_to_listen(**case)
        print(f"   测试用例 {i}: {'成功' if success else '失败'}")
        print(f"      - market_id: {case['market_id']}")
        print(f"      - buy_price: {case['buy_price']}")
        print(f"      - buy_side: {case['buy_side']}")
        print(f"      - marks: {case['marks']}")
    
    # 3. 查询所有监听记录
    print("\n3. 查询所有监听记录...")
    all_records = get_position_listen_list()
    print(f"   共找到 {len(all_records)} 条记录")
    for record in all_records:
        print(f"   - ID: {record['id']}, Market: {record['market_id'][:16]}..., "
              f"Price: {record['buy_price']}, Side: {record['buy_side']}")
    
    # 4. 查询特定市场的监听记录
    print("\n4. 查询特定市场的监听记录...")
    market_records = get_position_listen_list(market_id="0x1234567890abcdef")
    print(f"   找到 {len(market_records)} 条记录")
    for record in market_records:
        print(f"   - Marks: {record['marks']}")
    
    # 5. 更新监听记录
    if all_records:
        print("\n5. 更新监听记录...")
        first_id = all_records[0]['id']
        success = update_position_listen(
            listen_id=first_id,
            marks="已更新: 价格调整为0.70",
            buy_price=0.70
        )
        print(f"   更新记录 ID {first_id}: {'成功' if success else '失败'}")
        
        # 验证更新
        updated_records = get_position_listen_list()
        updated_record = next((r for r in updated_records if r['id'] == first_id), None)
        if updated_record:
            print(f"   更新后的价格: {updated_record['buy_price']}")
            print(f"   更新后的备注: {updated_record['marks']}")
    
    # 6. 停用监听记录
    if len(all_records) >= 2:
        print("\n6. 停用监听记录...")
        second_id = all_records[1]['id']
        success = deactivate_position_listen(second_id)
        print(f"   停用记录 ID {second_id}: {'成功' if success else '失败'}")
        
        # 查询激活的记录
        active_records = get_position_listen_list(is_active=True)
        print(f"   当前激活的记录数: {len(active_records)}")
    
    # 7. 删除监听记录
    if len(all_records) >= 3:
        print("\n7. 删除监听记录...")
        third_id = all_records[2]['id']
        success = remove_position_listen(third_id)
        print(f"   删除记录 ID {third_id}: {'成功' if success else '失败'}")
        
        # 验证删除
        remaining_records = get_position_listen_list()
        print(f"   剩余记录数: {len(remaining_records)}")
    
    # 8. 参数验证测试
    print("\n8. 参数验证测试...")
    
    # 测试无效的buy_side
    print("   测试无效的buy_side...")
    success = add_position_to_listen(
        market_id="0xtest",
        buy_price=0.5,
        buy_side="INVALID",
        marks="应该失败"
    )
    print(f"   无效buy_side测试: {'失败(符合预期)' if not success else '成功(不符合预期)'}")
    
    # 测试无效的buy_price
    print("   测试无效的buy_price...")
    success = add_position_to_listen(
        market_id="0xtest",
        buy_price=1.5,
        buy_side="YES",
        marks="应该失败"
    )
    print(f"   无效buy_price测试: {'失败(符合预期)' if not success else '成功(不符合预期)'}")
    
    # 测试空market_id
    print("   测试空market_id...")
    success = add_position_to_listen(
        market_id="",
        buy_price=0.5,
        buy_side="YES",
        marks="应该失败"
    )
    print(f"   空market_id测试: {'失败(符合预期)' if not success else '成功(不符合预期)'}")
    
    # 9. 最终统计
    print("\n9. 最终统计...")
    final_records = get_position_listen_list()
    active_count = len(get_position_listen_list(is_active=True))
    inactive_count = len(get_position_listen_list(is_active=False))
    
    print(f"   总记录数: {len(final_records)}")
    print(f"   激活记录数: {active_count}")
    print(f"   停用记录数: {inactive_count}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_position_listen()

