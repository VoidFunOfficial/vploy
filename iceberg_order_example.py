"""
冰山订单使用示例

演示如何使用 iceberg_order 函数执行大额订单分批交易
"""

import asyncio
from backend.polymarket_api import (
    iceberg_order,
    IcebergOrderManager,
    IcebergOrderStatus,
    BUY,
    SELL
)
from backend.sys_configs.global_event_reg import vlogger


async def example_basic_iceberg_order():
    """
    示例 1: 基础冰山订单
    
    使用便捷函数执行冰山订单
    """
    print("=" * 80)
    print("示例 1: 基础冰山订单")
    print("=" * 80)
    
    try:
        # 执行冰山订单
        order = await iceberg_order(
            token_id="21742633143463906290569050155826241533067272736897614950488156847949938836455",
            price=0.55,              # 挂单价格 0.55
            total_size=1000.0,       # 总共买入 1000 份
            display_size=100.0,      # 每次显示 100 份
            side=BUY                 # 买入方向
        )
        
        # 打印结果
        print(f"\n订单执行完成:")
        print(f"  状态: {order.status.value}")
        print(f"  总数量: {order.total_size}")
        print(f"  已成交: {order.total_filled}")
        print(f"  成交率: {order.fill_percentage:.2f}%")
        print(f"  订单片段数: {len(order.slices)}")
        
        # 打印每个片段的详情
        print(f"\n订单片段详情:")
        for slice in order.slices:
            print(f"  片段 {slice.slice_id}:")
            print(f"    数量: {slice.size}")
            print(f"    已成交: {slice.filled_size}")
            print(f"    状态: {slice.status.value}")
            print(f"    订单ID: {slice.order_id}")
        
        if order.status == IcebergOrderStatus.COMPLETED:
            duration = order.completed_at - order.started_at
            print(f"\n✅ 订单完全成交! 耗时: {duration:.2f} 秒")
        elif order.status == IcebergOrderStatus.PARTIALLY_FILLED:
            print(f"\n⚠️ 订单部分成交: {order.total_filled}/{order.total_size}")
        else:
            print(f"\n❌ 订单执行失败: {order.error_message}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")


async def example_advanced_iceberg_order():
    """
    示例 2: 高级冰山订单
    
    使用 IcebergOrderManager 进行更精细的控制
    """
    print("\n" + "=" * 80)
    print("示例 2: 高级冰山订单 (使用管理器)")
    print("=" * 80)
    
    # 创建管理器
    manager = IcebergOrderManager(
        api_key="your_api_key",
        api_secret="your_api_secret",
        api_passphrase="your_api_passphrase"
    )
    
    try:
        # 执行多个冰山订单
        orders = []
        
        # 订单 1: 买入
        print("\n执行订单 1: 买入...")
        order1 = await manager.execute_iceberg_order(
            token_id="token_id_1",
            price=0.45,
            total_size=500.0,
            display_size=50.0,
            side=BUY
        )
        orders.append(order1)
        
        # 订单 2: 卖出
        print("执行订单 2: 卖出...")
        order2 = await manager.execute_iceberg_order(
            token_id="token_id_2",
            price=0.65,
            total_size=800.0,
            display_size=80.0,
            side=SELL
        )
        orders.append(order2)
        
        # 打印汇总
        print("\n" + "=" * 80)
        print("订单执行汇总:")
        print("=" * 80)
        
        for i, order in enumerate(orders, 1):
            print(f"\n订单 {i}:")
            print(f"  Token ID: {order.token_id}")
            print(f"  方向: {order.side}")
            print(f"  价格: {order.price}")
            print(f"  状态: {order.status.value}")
            print(f"  成交: {order.total_filled}/{order.total_size} ({order.fill_percentage:.2f}%)")
            print(f"  片段数: {len(order.slices)}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
    
    finally:
        # 关闭管理器
        await manager.close()


async def example_cancel_iceberg_order():
    """
    示例 3: 取消冰山订单
    
    演示如何在执行过程中取消订单
    """
    print("\n" + "=" * 80)
    print("示例 3: 取消冰山订单")
    print("=" * 80)
    
    manager = IcebergOrderManager()
    
    try:
        # 创建一个异步任务执行订单
        async def execute_order():
            return await manager.execute_iceberg_order(
                token_id="token_id",
                price=0.50,
                total_size=2000.0,
                display_size=100.0,
                side=BUY
            )
        
        # 启动订单执行
        order_task = asyncio.create_task(execute_order())
        
        # 等待 5 秒后取消订单
        print("\n等待 5 秒后取消订单...")
        await asyncio.sleep(5)
        
        # 取消订单
        print("正在取消订单...")
        # 注意: 这里需要获取订单对象,实际使用中可以通过其他方式获取
        # success = await manager.cancel_iceberg_order(order)
        
        # 等待订单任务完成
        order = await order_task
        
        print(f"\n订单状态: {order.status.value}")
        print(f"已成交: {order.total_filled}/{order.total_size}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
    
    finally:
        await manager.close()


async def example_monitor_progress():
    """
    示例 4: 监控订单进度
    
    演示如何实时监控订单执行进度
    """
    print("\n" + "=" * 80)
    print("示例 4: 监控订单进度")
    print("=" * 80)
    
    manager = IcebergOrderManager()
    
    try:
        # 创建订单执行任务
        async def execute_with_monitoring():
            order = await manager.execute_iceberg_order(
                token_id="11252134445999290342676692020255334525474769662550801951216703014683639810411",
                price=0.99,
                total_size=30,
                display_size=3,
                side=SELL
            )
            return order
        
        # 创建进度监控任务
        async def monitor_progress():
            while True:
                await asyncio.sleep(2)  # 每 2 秒检查一次
                
                # 这里可以通过管理器获取活跃订单的进度
                # 实际实现中需要添加相应的接口
                print(".", end="", flush=True)
        
        # 并行执行订单和监控
        order_task = asyncio.create_task(execute_with_monitoring())
        monitor_task = asyncio.create_task(monitor_progress())
        
        # 等待订单完成
        order = await order_task
        
        # 取消监控任务
        monitor_task.cancel()
        
        print(f"\n\n订单执行完成!")
        print(f"  状态: {order.status.value}")
        print(f"  成交: {order.total_filled}/{order.total_size}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
    
    finally:
        await manager.close()


async def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 80)
    print("冰山订单使用示例")
    print("=" * 80)
    
    # 选择要运行的示例
    print("\n请选择示例:")
    print("1. 基础冰山订单")
    print("2. 高级冰山订单 (使用管理器)")
    print("3. 取消冰山订单")
    print("4. 监控订单进度")
    print("5. 运行所有示例")
    print()
    
    choice = input("请输入选项 (1-5): ").strip()
    
    if choice == "1":
        await example_basic_iceberg_order()
    elif choice == "2":
        await example_advanced_iceberg_order()
    elif choice == "3":
        await example_cancel_iceberg_order()
    elif choice == "4":
        await example_monitor_progress()
    elif choice == "5":
        await example_basic_iceberg_order()
        await example_advanced_iceberg_order()
        await example_cancel_iceberg_order()
        await example_monitor_progress()
    else:
        print("无效选项")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())

