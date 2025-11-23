"""
自动交易模块使用示例

演示如何使用 auto_trade 模块执行自动交易：
1. 获取市场数据
2. 进行AI分析（模拟）
3. 执行自动交易
4. 查看执行结果
"""

from typing import Dict, Any, List

from .auto_trade import (
    AutoTrader,
    execute_auto_trading,
    get_execution_summary
)
from ..polymarket_api.gamma_markets import GammaMarketsAPI
from ..sys_configs.global_event_reg import vlogger


def simulate_ai_analysis(markets: List[Any]) -> Dict[str, Any]:
    """
    模拟AI分析结果
    
    在实际应用中，这里应该是真实的AI分析逻辑
    
    参数:
        markets: 市场数据列表
    
    返回:
        Dict[str, Any]: AI分析结果
    """
    analysis = {}
    
    for market in markets:
        market_id = str(market.id)
        
        # 模拟AI分析结果
        # 在实际应用中，这些值应该来自真实的AI模型
        analysis[market_id] = {
            "p": 0.6,  # AI预测的YES概率
            "a": 0.3,  # 风险因子
            "reasons_p": ["正面因素1", "正面因素2"],
            "reasons_n": ["负面因素1"]
        }
    
    return analysis


def example_basic_usage():
    """基础使用示例"""
    print("=" * 80)
    print("自动交易模块 - 基础使用示例")
    print("=" * 80)
    
    try:
        # 步骤1：获取市场数据
        print("\n1. 获取市场数据...")
        with GammaMarketsAPI() as api:
            markets = api.get_active_markets(limit=5)
        
        if not markets:
            print("未获取到市场数据")
            return
        
        print(f"获取到 {len(markets)} 个市场")
        for market in markets:
            print(f"  - {market.question[:50]}...")
        
        # 步骤2：模拟AI分析
        print("\n2. 进行AI分析（模拟）...")
        ai_analysis = simulate_ai_analysis(markets)
        print(f"完成 {len(ai_analysis)} 个市场的分析")
        
        # 步骤3：执行自动交易
        print("\n3. 执行自动交易...")
        result = execute_auto_trading(
            gamma_markets=markets,
            ai_analysis=ai_analysis,
            M_cents=50000,  # 500美元
            kappa=0.7,      # 70%最大锁定比例
            xi=0.5          # 50% Kelly分数
        )
        
        # 步骤4：查看结果
        print("\n4. 交易结果:")
        if result["success"]:
            summary = result["summary"]
            print(f"  总指令数: {summary['total_instructions']}")
            print(f"  成功执行: {summary['successful_executions']}")
            print(f"  失败执行: {summary['failed_executions']}")
            print(f"  执行率: {summary['execution_rate']:.1f}%")
            print(f"  计划投入: ${summary['total_allocated_dollars']:.2f}")
            print(f"  实际执行: ${summary['total_executed_dollars']:.2f}")
            
            # 显示详细执行摘要
            if result["executions"]:
                print("\n详细执行摘要:")
                print(get_execution_summary(result["executions"]))
        else:
            print(f"  交易失败: {result['error']}")
    
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        vlogger.error("EXAMPLE.BASIC_USAGE_ERROR", msg="基础使用示例失败", extra={
            "error": str(e)
        })


def example_advanced_usage():
    """高级使用示例"""
    print("=" * 80)
    print("自动交易模块 - 高级使用示例")
    print("=" * 80)
    
    try:
        # 使用AutoTrader类进行更精细的控制
        print("\n使用 AutoTrader 类进行精细控制...")
        
        with GammaMarketsAPI() as api:
            markets = api.get_active_markets(limit=3)
        
        if not markets:
            print("未获取到市场数据")
            return
        
        ai_analysis = simulate_ai_analysis(markets)
        
        with AutoTrader() as trader:
            # 步骤1：获取交易指令
            print("\n1. 获取交易指令...")
            instructions = trader.get_trade_instructions(
                gamma_markets=markets,
                ai_analysis=ai_analysis,
                M_cents=30000,  # 300美元
                kappa=0.6,
                xi=0.4
            )
            
            print(f"获取到 {len(instructions)} 个交易指令")
            
            if not instructions:
                print("没有可执行的交易指令")
                return
            
            # 步骤2：逐个分析和执行
            print("\n2. 逐个分析和执行交易...")
            executions = []
            
            for i, instruction in enumerate(instructions):
                print(f"\n处理指令 {i+1}/{len(instructions)}:")
                print(f"  市场: {instruction.market_question[:50]}...")
                print(f"  方向: {instruction.side}")
                print(f"  金额: ${instruction.alloc_cents/100:.2f}")
                
                # 执行单个交易
                execution = trader.execute_trade(instruction)
                executions.append(execution)
                
                if execution.success:
                    print(f"  ✓ 执行成功")
                    if execution.slippage_analysis:
                        print(f"    滑点: {execution.slippage_analysis.expected_slippage:.2f}%")
                        print(f"    风险: {execution.slippage_analysis.risk_level}")
                else:
                    print(f"  ✗ 执行失败: {execution.error_message}")
            
            # 步骤3：汇总结果
            print("\n3. 执行结果汇总:")
            successful = sum(1 for ex in executions if ex.success)
            print(f"  成功: {successful}/{len(executions)}")
            print(f"  成功率: {successful/len(executions)*100:.1f}%")
    
    except Exception as e:
        print(f"高级示例执行失败: {str(e)}")
        vlogger.error("EXAMPLE.ADVANCED_USAGE_ERROR", msg="高级使用示例失败", extra={
            "error": str(e)
        })


def example_risk_analysis():
    """风险分析示例"""
    print("=" * 80)
    print("自动交易模块 - 风险分析示例")
    print("=" * 80)
    
    try:
        print("\n演示风险分析功能...")
        
        # 获取市场数据
        with GammaMarketsAPI() as api:
            markets = api.get_active_markets(limit=2)
        
        if not markets:
            print("未获取到市场数据")
            return
        
        # 创建高风险的AI分析（高概率预测，低风险因子）
        high_risk_analysis = {}
        for market in markets:
            market_id = str(market.id)
            high_risk_analysis[market_id] = {
                "p": 0.95,  # 极高的预测概率
                "a": 0.1,   # 极低的风险因子
                "reasons_p": ["极强信号"],
                "reasons_n": []
            }
        
        print("\n使用高风险参数进行交易...")
        result = execute_auto_trading(
            gamma_markets=markets,
            ai_analysis=high_risk_analysis,
            M_cents=100000,  # 1000美元
            kappa=0.9,       # 90%最大锁定比例（激进）
            xi=0.8           # 80% Kelly分数（激进）
        )
        
        if result["success"] and result["executions"]:
            print("\n风险分析结果:")
            for execution in result["executions"]:
                if execution.slippage_analysis:
                    print(f"  市场: {execution.instruction.market_id}")
                    print(f"    预期滑点: {execution.slippage_analysis.expected_slippage:.2f}%")
                    print(f"    风险等级: {execution.slippage_analysis.risk_level}")
                    print(f"    推荐价格: ${execution.slippage_analysis.recommended_price:.4f}")
                    print(f"    最大安全量: ${execution.slippage_analysis.max_safe_size:.2f}")
                    print(f"    执行状态: {'成功' if execution.success else '失败'}")
                    if not execution.success:
                        print(f"    失败原因: {execution.error_message}")
                    print()
        else:
            print(f"风险分析失败: {result.get('error', '未知错误')}")
    
    except Exception as e:
        print(f"风险分析示例失败: {str(e)}")
        vlogger.error("EXAMPLE.RISK_ANALYSIS_ERROR", msg="风险分析示例失败", extra={
            "error": str(e)
        })


def main():
    """主函数"""
    print("自动交易模块使用示例")
    print("注意：这些示例使用模拟数据，实际使用时需要真实的API密钥和市场数据")
    
    try:
        # 注册事件码
        from backend.sys_configs.global_event_reg import register_all_events
        register_all_events()
        
        # 运行示例
        example_basic_usage()
        print("\n" + "="*80 + "\n")
        
        example_advanced_usage()
        print("\n" + "="*80 + "\n")
        
        example_risk_analysis()
        
    except Exception as e:
        print(f"示例程序执行失败: {str(e)}")
        vlogger.error("EXAMPLE.MAIN_ERROR", msg="示例程序执行失败", extra={
            "error": str(e)
        })


if __name__ == "__main__":
    main()
