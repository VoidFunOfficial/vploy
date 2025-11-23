"""
仓位分配 Pro 版本使用示例

演示如何使用 allocate_optimal_positions_pro 函数进行仓位分配：
1. 从 Gamma API 获取市场数据
2. 使用 AI 分析结果
3. 调用 Pro 版本进行仓位分配
4. 输出交易指令
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from position_manager import (
    allocate_optimal_positions_pro,
    get_trade_instructions_summary,
    export_instructions_to_json
)
from polymarket_api.gamma_markets import GammaMarketsAPI


def example_with_mock_data():
    """
    使用模拟数据演示 Pro 版本的使用
    """
    print("=" * 80)
    print("示例 1: 使用模拟数据")
    print("=" * 80)
    
    # 模拟 Gamma Markets 数据
    # 注意：这里使用简化的数据结构，实际使用时应该从 API 获取
    from dataclasses import dataclass
    from typing import Optional, List, Dict, Any
    
    @dataclass
    class MockMarket:
        id: str
        question: str
        slug: str
        outcome_prices: str
        end_date: str
        volume: Optional[str] = None
        liquidity: Optional[str] = None
    
    mock_markets = [
        MockMarket(
            id="market_001",
            question="Will Bitcoin reach $100,000 by end of 2025?",
            slug="btc-100k-2025",
            outcome_prices='["0.42", "0.58"]',
            end_date="2025-12-31T23:59:59Z",
            volume="1000000",
            liquidity="500000"
        ),
        MockMarket(
            id="market_002",
            question="Will Ethereum merge to PoS succeed?",
            slug="eth-pos-merge",
            outcome_prices='["0.75", "0.25"]',
            end_date="2025-06-30T23:59:59Z",
            volume="500000",
            liquidity="250000"
        ),
        MockMarket(
            id="market_003",
            question="Will Trump win 2024 election?",
            slug="trump-2024",
            outcome_prices='["0.51", "0.49"]',
            end_date="2024-11-05T23:59:59Z",
            volume="2000000",
            liquidity="1000000"
        )
    ]
    
    # 模拟 AI 分析结果
    # 注意：现在使用 market_id 作为键，而不是 "Market #1", "Market #2" 等
    ai_analysis = {
        "market_001": {  # 使用实际的 market_id
            "p": 0.55,  # AI 预测 YES 的概率为 55%
            "a": 0.3,   # 风险因子 0.3（较低风险）
            "reasons_p": [
                "比特币历史趋势显示长期上涨",
                "机构投资者持续增持",
                "减半效应可能推动价格上涨"
            ],
            "reasons_n": [
                "监管风险仍然存在",
                "宏观经济不确定性"
            ]
        },
        "market_002": {  # 使用实际的 market_id
            "p": 0.80,  # AI 预测 YES 的概率为 80%
            "a": 0.2,   # 风险因子 0.2（低风险）
            "reasons_p": [
                "技术准备充分",
                "社区支持度高",
                "测试网表现良好"
            ],
            "reasons_n": [
                "技术复杂度高，可能延期"
            ]
        },
        "market_003": {  # 使用实际的 market_id
            "p": 0.48,  # AI 预测 YES 的概率为 48%
            "a": 0.6,   # 风险因子 0.6（较高风险）
            "reasons_p": [
                "部分民调显示支持率上升"
            ],
            "reasons_n": [
                "政治环境复杂",
                "对手竞争力强",
                "历史数据显示不确定性高"
            ]
        }
    }
    
    # 调用 Pro 版本进行仓位分配
    result = allocate_optimal_positions_pro(
        gamma_markets=mock_markets,
        ai_analysis_result=ai_analysis,
        M_cents=100_000,  # 1000 美元可用资金
        kappa=0.7,        # 最多锁定 70% 的资金
        locked_cents=0,   # 当前没有锁定资金
        xi=0.5,           # 使用 50% Kelly（半 Kelly）
        shrink_with_a=True
    )
    
    # 输出结果
    if result["success"]:
        print("\n✓ 仓位分配成功！\n")
        
        # 输出元数据
        print("元数据:")
        meta = result["meta"]
        print(f"  基准财富: ${meta['B_cents'] / 100.0:.2f}")
        print(f"  可用预算: ${meta['budget_cents'] / 100.0:.2f}")
        print(f"  实际使用: ${meta['used_cents'] / 100.0:.2f}")
        print(f"  Kappa: {meta['kappa']}")
        print(f"  Xi (分数Kelly): {meta['xi']}")
        
        # 输出汇总信息
        print("\n汇总信息:")
        summary = result["summary"]
        print(f"  总市场数: {summary['total_markets']}")
        print(f"  有效市场数: {summary['valid_markets']}")
        print(f"  可交易市场数: {summary['tradable_markets']}")
        print(f"  总投入金额: ${summary['total_alloc_dollars']:.2f}")
        print(f"  预期总收益: ${summary['total_expected_profit_dollars']:.2f}")
        print(f"  预期 ROI: {summary['expected_roi']:.2f}%")
        print(f"  预算使用率: {summary['budget_utilization']:.2f}%")
        
        # 输出交易指令
        print("\n" + get_trade_instructions_summary(result["instructions"]))
        
        # 导出到 JSON 文件
        output_file = "trade_instructions_example.json"
        if export_instructions_to_json(result["instructions"], output_file):
            print(f"\n✓ 交易指令已导出到: {output_file}")
        
    else:
        print(f"\n✗ 仓位分配失败: {result['error']}")


def example_with_real_api():
    """
    使用真实 API 数据演示 Pro 版本的使用
    
    注意：需要有效的 AI 分析结果
    """
    print("\n" + "=" * 80)
    print("示例 2: 使用真实 API 数据")
    print("=" * 80)
    
    # 获取真实市场数据
    with GammaMarketsAPI() as api:
        markets = api.get_active_markets(limit=3)
    
    if not markets:
        print("未找到活跃市场")
        return
    
    print(f"\n获取到 {len(markets)} 个活跃市场")
    
    # 这里需要真实的 AI 分析结果
    # 在实际使用中，应该调用 deep_analysis 模块获取分析结果
    print("\n注意：此示例需要真实的 AI 分析结果")
    print("请参考 backend/ai_analysis/deep_analysis.py 获取分析结果")
    
    # 示例 AI 分析结果格式（使用实际的 market_id）
    # 注意：需要使用真实市场的 ID
    if markets:
        example_ai_analysis = {}
        for market in markets:
            example_ai_analysis[market.id] = {
                "p": 0.6,
                "a": 0.3,
                "reasons_p": ["示例理由1", "示例理由2"],
                "reasons_n": ["示例反对理由"]
            }
    else:
        example_ai_analysis = {
            "market_id_1": {"p": 0.6, "a": 0.3, "reasons_p": ["..."], "reasons_n": ["..."]},
            "market_id_2": {"p": 0.7, "a": 0.2, "reasons_p": ["..."], "reasons_n": ["..."]},
            "market_id_3": {"p": 0.5, "a": 0.4, "reasons_p": ["..."], "reasons_n": ["..."]}
        }
    
    print("\nAI 分析结果格式示例:")
    import json
    print(json.dumps(example_ai_analysis, indent=2, ensure_ascii=False))


def example_integration_workflow():
    """
    完整的集成工作流示例
    
    演示从获取市场数据、AI 分析到仓位分配的完整流程
    """
    print("\n" + "=" * 80)
    print("示例 3: 完整集成工作流")
    print("=" * 80)
    
    print("\n完整工作流步骤:")
    print("1. 从 Gamma API 获取活跃市场列表")
    print("2. 对每个市场进行 AI 深度分析（使用 deep_analysis 模块）")
    print("3. 调用 allocate_optimal_positions_pro 进行仓位分配")
    print("4. 生成交易指令")
    print("5. 执行交易（可选）")
    
    print("\n代码示例:")
    print("""
    # 步骤 1: 获取市场数据
    from polymarket_api.gamma_markets import GammaMarketsAPI
    with GammaMarketsAPI() as api:
        markets = api.get_active_markets(limit=10)
    
    # 步骤 2: AI 分析（需要异步执行）
    from ai_analysis.deep_analysis import AnalysisTaskManager
    import asyncio
    
    async def analyze_markets():
        manager = AnalysisTaskManager(cookie_string="your_cookie")
        await manager.start_workers(num_workers=3)
        
        # 提交分析任务
        task_ids = []
        for market in markets:
            task_id = await manager.submit_analysis_task(market)
            task_ids.append(task_id)
        
        # 等待完成
        results = []
        for task_id in task_ids:
            result = await manager.wait_for_task_completion(task_id)
            results.append(result)
        
        await manager.stop_workers()
        return results
    
    # 运行分析
    analysis_results = asyncio.run(analyze_markets())
    
    # 步骤 3: 仓位分配
    from position_manager import allocate_optimal_positions_pro
    
    allocation_result = allocate_optimal_positions_pro(
        gamma_markets=markets,
        ai_analysis_result=analysis_results[0]['result_json'],  # 使用第一个分析结果
        M_cents=None,  # 自动获取账户余额
        kappa=0.7,
        xi=0.5
    )
    
    # 步骤 4: 输出交易指令
    if allocation_result['success']:
        for instruction in allocation_result['instructions']:
            print(f"市场: {instruction.market_question}")
            print(f"方向: {instruction.side}")
            print(f"金额: ${instruction.alloc_cents / 100.0:.2f}")
    """)


if __name__ == "__main__":
    # 运行示例
    example_with_mock_data()
    example_with_real_api()
    example_integration_workflow()

