"""
自动止盈系统使用示例

演示如何使用止盈系统的各个功能模块。
"""

from datetime import datetime, timedelta
from backend.surplus_dog.easy_info import (
    get_market_realtime_data,
    get_market_history_data,
    prepare_decision_data
)
from backend.surplus_dog.surplus_cal import decide_hold_or_sell
from backend.surplus_dog.auto_surplus import (
    auto_surplus_decision,
    auto_surplus_all_positions,
    determine_strategy_tag
)
from backend.surplus_dog.surplus_monitor import SurplusMonitor


def example_1_get_realtime_data():
    """示例1: 获取实时市场数据"""
    print("\n=== 示例1: 获取实时市场数据 ===")
    
    token_id = "21742633143463906290569050155826241533067272736897614950488156847949938836455"
    
    try:
        data = get_market_realtime_data(token_id=token_id, side="YES")
        print(f"当前价格: {data['current_price']}")
        print(f"买单深度: {data['bid_depth']}")
        print(f"卖单深度: {data['ask_depth']}")
        print(f"点差: {data['spread']}")
        print(f"中间价: {data['mid_price']}")
    except Exception as e:
        print(f"错误: {e}")


def example_2_get_history_data():
    """示例2: 获取历史市场数据"""
    print("\n=== 示例2: 获取历史市场数据 ===")
    
    token_id = "21742633143463906290569050155826241533067272736897614950488156847949938836455"
    
    try:
        history = get_market_history_data(
            token_id=token_id,
            interval="1d",  # 最近1天
            fidelity=60     # 1小时分辨率
        )
        print(f"数据点数量: {len(history['prices'])}")
        print(f"价格范围: {min(history['prices']):.4f} - {max(history['prices']):.4f}")
        print(f"最新价格: {history['prices'][-1]:.4f}")
    except Exception as e:
        print(f"错误: {e}")


def example_3_manual_decision():
    """示例3: 手动调用决策算法"""
    print("\n=== 示例3: 手动调用决策算法 ===")
    
    # 模拟数据
    entry_price = 0.45
    entry_index = 0
    prices = [0.45, 0.47, 0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.65]
    volumes = [100, 120, 150, 180, 200, 220, 250, 280, 300]
    
    try:
        decision = decide_hold_or_sell(
            tag="short-term",
            entry_price=entry_price,
            entry_index=entry_index,
            prices=prices,
            volumes=volumes,
            current_price=0.65,
            current_volume=300,
            tau=5.0  # 5天
        )
        
        print(f"决策: {decision['action']}")
        print(f"评分: {decision['score']:.3f}")
        print(f"阈值: {decision['threshold']:.3f}")
        print(f"建议卖出比例: {decision['suggested_sell_fraction']:.2f}")
        print(f"原因: {decision['reason']}")
        print(f"\n因子详情:")
        for factor, value in decision['factors'].items():
            print(f"  {factor}: {value:.3f}")
    except Exception as e:
        print(f"错误: {e}")


def example_4_determine_tag():
    """示例4: 自动确定策略标签"""
    print("\n=== 示例4: 自动确定策略标签 ===")
    
    test_cases = [
        (0.25, 5),    # 低价 + 短期 -> speculation
        (0.25, 15),   # 低价 + 长期 -> speculation
        (0.75, 5),    # 高价 + 短期 -> short-term
        (0.75, 15),   # 高价 + 长期 -> long-term
        (0.50, 5),    # 中价 + 短期 -> short-term
        (0.50, 15),   # 中价 + 长期 -> long-term
    ]
    
    for entry_price, tau_days in test_cases:
        tag = determine_strategy_tag(entry_price, tau_days)
        print(f"入场价={entry_price:.2f}, tau={tau_days}天 -> 策略={tag}")


def example_5_auto_decision_single():
    """示例5: 单个持仓自动决策（仅检查）"""
    print("\n=== 示例5: 单个持仓自动决策 ===")
    
    position_id = 1  # 替换为实际的持仓ID
    token_id = "your_token_id"  # 替换为实际的token_id
    
    try:
        result = auto_surplus_decision(
            position_id=position_id,
            token_id=token_id,
            tag="short-term",  # 可选，会自动推断
            execute=False      # 仅检查，不执行
        )
        
        if result['success']:
            decision = result['decision']
            print(f"持仓ID: {result['position_id']}")
            print(f"策略标签: {result['tag']}")
            print(f"决策: {decision['action']}")
            print(f"评分: {decision['score']:.3f}")
            print(f"原因: {decision['reason']}")
        else:
            print(f"失败: {result['message']}")
    except Exception as e:
        print(f"错误: {e}")


def example_6_monitor_all():
    """示例6: 监控所有持仓（仅检查）"""
    print("\n=== 示例6: 监控所有持仓 ===")
    
    try:
        monitor = SurplusMonitor()
        result = monitor.monitor_all_positions_with_surplus(
            execute_sell=False  # 仅检查，不执行
        )
        
        if result['success']:
            print(f"总持仓数: {result['total_positions']}")
            print(f"已检查: {result['checked']}")
            print(f"卖出信号: {result['sell_signals']}")
            
            # 显示前3个结果
            for i, res in enumerate(result['results'][:3]):
                if res.get('surplus_decision'):
                    decision = res['surplus_decision'].get('decision', {})
                    print(f"\n持仓 {i+1}:")
                    print(f"  决策: {decision.get('action')}")
                    print(f"  评分: {decision.get('score', 0):.3f}")
        else:
            print(f"失败: {result['message']}")
    except Exception as e:
        print(f"错误: {e}")


def example_7_execute_sell():
    """示例7: 执行自动卖出（谨慎使用！）"""
    print("\n=== 示例7: 执行自动卖出 ===")
    print("警告: 此示例会实际执行卖出操作！")
    print("请确认后再运行此函数。")
    
    # 取消注释以下代码来执行
    # position_id = 1
    # token_id = "your_token_id"
    # 
    # result = auto_surplus_decision(
    #     position_id=position_id,
    #     token_id=token_id,
    #     execute=True  # 执行卖出
    # )
    # 
    # if result['success'] and result['executed']:
    #     sell_result = result['sell_result']
    #     print(f"卖单已提交:")
    #     print(f"  订单ID: {sell_result['order_id']}")
    #     print(f"  卖出数量: {sell_result['sell_size']}")
    #     print(f"  卖出价格: {sell_result['sell_price']}")


if __name__ == "__main__":
    print("自动止盈系统使用示例")
    print("=" * 50)
    
    # 运行示例（根据需要注释/取消注释）
    # example_1_get_realtime_data()
    # example_2_get_history_data()
    example_3_manual_decision()
    example_4_determine_tag()
    # example_5_auto_decision_single()
    # example_6_monitor_all()
    # example_7_execute_sell()  # 谨慎使用！

