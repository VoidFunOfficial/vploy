"""
Purse钱包管理模块测试脚本

演示Purse模块的各项功能
"""

from backend.purse import Purse, get_purse


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}")


def print_status(purse):
    """打印钱包状态"""
    status = purse.get_status()
    print(f"\n【钱包状态】")
    print(f"  总资金: {status['total_fund']:.2f}")
    print(f"  锁定资金: {status['locked_fund']:.2f}")
    print(f"  可用现金: {status['available_cash']:.2f}")
    print(f"  总亏损: {status['loss']:.2f}")
    print(f"  预期盈利: {status['expect_profit']:.2f}")
    print(f"  实际盈利: {status['real_profit']:.2f}")
    print(f"  成功市场: {status['success_market']}")
    print(f"  失败市场: {status['lost_market']}")
    print(f"  更新时间: {status['updated_at']}")


def print_summary(purse):
    """打印盈亏汇总"""
    summary = purse.get_profit_loss_summary()
    print(f"\n【盈亏汇总】")
    print(f"  总亏损: {summary['loss']:.2f}")
    print(f"  预期盈利: {summary['expect_profit']:.2f}")
    print(f"  实际盈利: {summary['real_profit']:.2f}")
    print(f"  净盈利: {summary['net_profit']:.2f}")
    print(f"  成功市场: {summary['success_market']}")
    print(f"  失败市场: {summary['lost_market']}")
    print(f"  总市场数: {summary['total_market']}")
    print(f"  胜率: {summary['win_rate']:.2f}%")


def test_basic_operations():
    """测试基础操作"""
    print_separator("测试1: 基础操作")
    
    # 获取钱包实例
    purse = get_purse()
    
    # 重置钱包
    print("\n1. 重置钱包...")
    purse.reset()
    
    # 初始化钱包
    print("\n2. 初始化钱包，投入10000元...")
    purse.initialize(total_fund=10000.0)
    print_status(purse)
    
    # 锁定资金
    print("\n3. 锁定100元用于下注...")
    purse.lock_fund(100.0)
    print_status(purse)
    
    # 解锁资金
    print("\n4. 解锁100元（取消订单）...")
    purse.unlock_fund(100.0)
    print_status(purse)


def test_profit_scenario():
    """测试盈利场景"""
    print_separator("测试2: 盈利场景")
    
    purse = get_purse()
    purse.reset()
    purse.initialize(total_fund=10000.0)
    
    print("\n场景: 下注100元，盈利50元")
    print("\n1. 锁定100元...")
    purse.lock_fund(100.0)
    print_status(purse)
    
    print("\n2. 设置预期盈利50元...")
    purse.set_expect_profit(50.0)
    print_status(purse)
    
    print("\n3. 订单结算，记录盈利...")
    purse.record_profit(amount=50.0, unlock_amount=100.0)
    purse.set_expect_profit(0.0)
    print_status(purse)
    print_summary(purse)


def test_loss_scenario():
    """测试亏损场景"""
    print_separator("测试3: 亏损场景")
    
    purse = get_purse()
    purse.reset()
    purse.initialize(total_fund=10000.0)
    
    print("\n场景: 下注100元，亏损30元，收回70元")
    print("\n1. 锁定100元...")
    purse.lock_fund(100.0)
    print_status(purse)
    
    print("\n2. 设置预期盈利40元...")
    purse.set_expect_profit(40.0)
    print_status(purse)
    
    print("\n3. 订单结算，记录亏损...")
    purse.record_loss(amount=30.0, unlock_amount=70.0)
    purse.set_expect_profit(0.0)
    print_status(purse)
    print_summary(purse)


def test_multiple_trades():
    """测试多笔交易"""
    print_separator("测试4: 多笔交易场景")
    
    purse = get_purse()
    purse.reset()
    purse.initialize(total_fund=10000.0)
    
    print("\n模拟10笔交易（7胜3负）...")
    
    # 7笔盈利交易
    for i in range(7):
        purse.lock_fund(100.0)
        purse.record_profit(amount=50.0, unlock_amount=100.0)
        print(f"  交易{i+1}: 盈利50元")
    
    # 3笔亏损交易
    for i in range(3):
        purse.lock_fund(100.0)
        purse.record_loss(amount=30.0, unlock_amount=70.0)
        print(f"  交易{i+8}: 亏损30元")
    
    print_status(purse)
    print_summary(purse)


def test_fund_management():
    """测试资金管理"""
    print_separator("测试5: 资金管理")
    
    purse = get_purse()
    purse.reset()
    purse.initialize(total_fund=10000.0)
    
    print("\n1. 初始状态...")
    print_status(purse)
    
    print("\n2. 追加5000元...")
    purse.add_fund(5000.0)
    print_status(purse)
    
    print("\n3. 提取2000元...")
    purse.withdraw_fund(2000.0)
    print_status(purse)


def test_error_handling():
    """测试错误处理"""
    print_separator("测试6: 错误处理")
    
    purse = get_purse()
    purse.reset()
    purse.initialize(total_fund=1000.0)
    
    print("\n1. 尝试锁定超过可用资金的金额...")
    result = purse.lock_fund(2000.0)
    print(f"  结果: {'成功' if result else '失败（预期）'}")
    
    print("\n2. 尝试解锁超过锁定资金的金额...")
    purse.lock_fund(100.0)
    result = purse.unlock_fund(200.0)
    print(f"  结果: {'成功' if result else '失败（预期）'}")
    
    print("\n3. 尝试提取超过可用资金的金额...")
    result = purse.withdraw_fund(2000.0)
    print(f"  结果: {'成功' if result else '失败（预期）'}")
    
    print("\n4. 尝试设置负数资金...")
    result = purse.initialize(total_fund=-1000.0)
    print(f"  结果: {'成功' if result else '失败（预期）'}")


def test_concurrent_access():
    """测试并发访问（单例模式）"""
    print_separator("测试7: 并发访问（单例模式）")
    
    print("\n1. 创建多个实例...")
    purse1 = get_purse()
    purse2 = Purse.get_instance()
    purse3 = get_purse()
    
    print(f"  purse1 id: {id(purse1)}")
    print(f"  purse2 id: {id(purse2)}")
    print(f"  purse3 id: {id(purse3)}")
    print(f"  是否为同一实例: {purse1 is purse2 is purse3}")
    
    print("\n2. 通过purse1修改数据...")
    purse1.reset()
    purse1.initialize(total_fund=5000.0)
    
    print("\n3. 通过purse2读取数据...")
    status = purse2.get_status()
    print(f"  总资金: {status['total_fund']:.2f}")
    
    print("\n4. 通过purse3读取数据...")
    total = purse3.get_total_fund()
    print(f"  总资金: {total:.2f}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Purse钱包管理模块测试")
    print("="*60)
    
    try:
        # 运行所有测试
        test_basic_operations()
        test_profit_scenario()
        test_loss_scenario()
        test_multiple_trades()
        test_fund_management()
        test_error_handling()
        test_concurrent_access()
        
        print_separator("所有测试完成")
        print("\n✅ 所有测试执行完毕！")
        print("\n提示: 查看 logs/vlogger.log 文件可以看到详细的日志记录")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

