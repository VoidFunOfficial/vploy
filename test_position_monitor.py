"""
仓位监听功能测试脚本
"""

import json
from backend.position_listener import get_db, monitor_all_positions


def test_add_position():
    """测试添加仓位监听"""
    print("\n=== 测试添加仓位监听 ===")

    # 获取数据库实例
    db = get_db()

    # 添加测试仓位
    threshold_config = json.dumps({
        "percent": 0.1,  # 价格变动10%触发
        "absolute": 0.05  # 价格绝对变动0.05触发
    })

    try:
        position_id = db.add_position(
            market_id="705811",  # 测试市场ID
            buy_price=0.52,
            buy_side="YES",
            marks="测试仓位",
            shares=100.0,
            threshold_config=threshold_config
        )

        print(f"✓ 添加仓位监听成功, ID: {position_id}")
        return True
    except Exception as e:
        print(f"✗ 添加仓位监听失败: {str(e)}")
        return False


def test_get_positions():
    """测试获取仓位列表"""
    print("\n=== 测试获取仓位列表 ===")

    db = get_db()
    positions = db.get_positions(is_active=True)
    
    print(f"活跃仓位数量: {len(positions)}")
    
    for pos in positions:
        print(f"\n仓位ID: {pos['id']}")
        print(f"  市场ID: {pos['market_id']}")
        print(f"  买入方向: {pos['buy_side']}")
        print(f"  买入价格: {pos['buy_price']}")
        print(f"  当前价格: {pos.get('current_price', 'N/A')}")
        print(f"  市场状态: {'已结束' if pos.get('market_closed') else '活跃'}")
        print(f"  阈值配置: {pos.get('threshold_config', 'N/A')}")
        print(f"  备注: {pos.get('marks', 'N/A')}")
    
    return positions


def test_monitor():
    """测试仓位监听"""
    print("\n=== 测试仓位监听 ===")
    
    result = monitor_all_positions()
    
    print(f"\n监听结果:")
    print(f"  总仓位数: {result['total']}")
    print(f"  成功更新: {result['success']}")
    print(f"  更新失败: {result['failed']}")
    print(f"  已结束市场: {result['closed_markets']}")
    
    return result


def test_update_position():
    """测试手动更新仓位"""
    print("\n=== 测试手动更新仓位 ===")

    db = get_db()
    positions = db.get_positions(is_active=True)

    if not positions:
        print("没有活跃仓位可更新")
        return False

    # 更新第一个仓位
    pos = positions[0]
    try:
        success = db.update_position(
            position_id=pos['id'],
            current_price=0.55,
            market_closed=False
        )

        if success:
            print(f"✓ 更新仓位 {pos['id']} 成功")
        else:
            print(f"✗ 更新仓位 {pos['id']} 失败")

        return success
    except Exception as e:
        print(f"✗ 更新仓位失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("仓位监听功能测试")
    print("=" * 60)
    
    try:
        # 1. 添加测试仓位
        test_add_position()
        
        # 2. 获取仓位列表
        test_get_positions()
        
        # 3. 执行监听任务
        test_monitor()
        
        # 4. 再次查看更新后的仓位
        print("\n=== 监听后的仓位状态 ===")
        test_get_positions()
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

