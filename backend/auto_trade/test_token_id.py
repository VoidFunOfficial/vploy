"""
测试 token_id 获取功能

验证从 Gamma Market 对象中正确获取 clobTokenIds
"""

from .auto_trade import AutoTrader
from ..polymarket_api.gamma_markets import GammaMarketsAPI
from ..sys_configs.global_event_reg import vlogger, register_all_events


def test_token_id_extraction():
    """测试从 Gamma Market 获取 token_id"""
    print("=" * 80)
    print("测试 Token ID 获取功能")
    print("=" * 80)
    
    try:
        # 注册事件
        register_all_events()
        
        # 获取市场数据
        print("\n1. 获取市场数据...")
        with GammaMarketsAPI() as api:
            markets = api.get_active_markets(limit=3)
        
        if not markets:
            print("❌ 未获取到市场数据")
            return
        
        print(f"✅ 获取到 {len(markets)} 个市场")
        
        # 创建 AutoTrader
        print("\n2. 创建 AutoTrader...")
        trader = AutoTrader()
        print("✅ AutoTrader 创建成功")
        
        # 测试每个市场的 token_id 获取
        print("\n3. 测试 token_id 获取...")
        for i, market in enumerate(markets, 1):
            print(f"\n市场 {i}:")
            print(f"  ID: {market.id}")
            print(f"  问题: {market.question[:60]}...")
            
            # 检查 clobTokenIds
            if hasattr(market, 'clobTokenIds') and market.clobTokenIds:
                print(f"  ✅ clobTokenIds: {market.clobTokenIds}")
                
                # 测试获取 YES token
                yes_token = trader._get_token_id_from_market(market, "BUY_YES")
                if yes_token:
                    print(f"  ✅ YES Token ID: {yes_token}")
                else:
                    print(f"  ❌ 无法获取 YES Token ID")
                
                # 测试获取 NO token
                no_token = trader._get_token_id_from_market(market, "BUY_NO")
                if no_token:
                    print(f"  ✅ NO Token ID: {no_token}")
                else:
                    print(f"  ❌ 无法获取 NO Token ID")
                
                # 验证 token_id 不同
                if yes_token and no_token and yes_token != no_token:
                    print(f"  ✅ YES 和 NO token_id 不同")
                elif yes_token and no_token:
                    print(f"  ⚠️ YES 和 NO token_id 相同（可能有问题）")
                    
            else:
                print(f"  ❌ 缺少 clobTokenIds")
        
        print("\n" + "=" * 80)
        print("✅ Token ID 获取功能测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_config_system():
    """测试配置系统"""
    print("\n" + "=" * 80)
    print("测试配置系统")
    print("=" * 80)
    
    try:
        from backend.sys_configs.auto_trade_config import get_auto_trade_config
        
        print("\n1. 加载配置...")
        config = get_auto_trade_config()
        print("✅ 配置加载成功")
        
        print("\n2. 配置参数:")
        print(f"  最大滑点: {config.max_slippage_percent}%")
        print(f"  流动性阈值: ${config.liquidity_threshold}")
        print(f"  最小订单: ${config.min_order_size}")
        print(f"  最大订单: ${config.max_order_size}")
        print(f"  价格改善因子: {config.price_improvement_factor}")
        print(f"  最大重试次数: {config.max_retries}")
        
        print("\n3. 风险控制:")
        print(f"  启用滑点保护: {config.enable_slippage_protection}")
        print(f"  启用流动性检查: {config.enable_liquidity_check}")
        print(f"  启用订单大小验证: {config.enable_size_validation}")
        
        print("\n✅ 配置系统测试通过")
        
    except Exception as e:
        print(f"\n❌ 配置系统测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("自动交易模块功能测试\n")
    
    # 测试 token_id 获取
    test_token_id_extraction()
    
    # 测试配置系统
    test_config_system()
    
    print("\n" + "=" * 80)
    print("所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
