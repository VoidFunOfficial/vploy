"""
自动交易配置管理工具

提供命令行界面来查看、修改和管理自动交易模块的配置参数。
所有配置都存储在 SQLite 数据库中，支持动态更新。
"""

import argparse
from typing import Dict, Any

from ..sys_configs.auto_trade_config import (
    AutoTradeConfigManager,
    get_auto_trade_config,
    update_auto_trade_config
)
from ..sys_configs.global_event_reg import vlogger


def show_config():
    """显示当前配置"""
    print("=" * 80)
    print("自动交易模块当前配置")
    print("=" * 80)
    
    try:
        config = get_auto_trade_config()
        
        print("\n📊 滑点控制参数:")
        print(f"  最大滑点百分比: {config.max_slippage_percent}%")
        print(f"  流动性阈值: ${config.liquidity_threshold}")
        
        print("\n💰 订单大小限制:")
        print(f"  最小订单金额: ${config.min_order_size}")
        print(f"  最大订单金额: ${config.max_order_size}")
        
        print("\n💡 价格策略参数:")
        print(f"  价格改善因子: {config.price_improvement_factor}")
        print(f"  安全边距: {config.safety_margin}")
        
        print("\n🔄 重试机制参数:")
        print(f"  最大重试次数: {config.max_retries}")
        print(f"  重试延迟: {config.retry_delay}秒")
        
        print("\n⚠️ 风险评估阈值:")
        print(f"  低风险滑点阈值: {config.low_risk_slippage_threshold}%")
        print(f"  高风险滑点阈值: {config.high_risk_slippage_threshold}%")
        print(f"  低风险流动性阈值: {config.low_risk_liquidity_threshold}")
        print(f"  高风险流动性阈值: {config.high_risk_liquidity_threshold}")
        
        print("\n🛡️ 执行控制参数:")
        print(f"  启用滑点保护: {'是' if config.enable_slippage_protection else '否'}")
        print(f"  启用流动性检查: {'是' if config.enable_liquidity_check else '否'}")
        print(f"  启用订单大小验证: {'是' if config.enable_size_validation else '否'}")
        
        print("\n📝 调试和监控参数:")
        print(f"  记录订单簿分析日志: {'是' if config.log_orderbook_analysis else '否'}")
        print(f"  记录滑点计算日志: {'是' if config.log_slippage_calculation else '否'}")
        print(f"  记录执行详情日志: {'是' if config.log_execution_details else '否'}")
        
    except Exception as e:
        print(f"❌ 获取配置失败: {e}")


def update_config(updates: Dict[str, Any]):
    """更新配置"""
    print("=" * 80)
    print("更新自动交易配置")
    print("=" * 80)
    
    try:
        # 显示要更新的配置
        print("\n📝 要更新的配置项:")
        for key, value in updates.items():
            print(f"  {key}: {value}")
        
        # 执行更新
        success = update_auto_trade_config(**updates)
        
        if success:
            print("\n✅ 配置更新成功！")
            print("\n📊 更新后的配置:")
            show_config()
        else:
            print("\n❌ 配置更新失败！")
            
    except Exception as e:
        print(f"❌ 更新配置时发生错误: {e}")


def reset_config():
    """重置为默认配置"""
    print("=" * 80)
    print("重置自动交易配置")
    print("=" * 80)
    
    try:
        from backend.sys_configs.auto_trade_config import AutoTradeConfig
        
        # 创建默认配置
        default_config = AutoTradeConfig()
        
        # 保存默认配置
        manager = AutoTradeConfigManager()
        success = manager.save_config(default_config)
        
        if success:
            print("\n✅ 配置已重置为默认值！")
            print("\n📊 默认配置:")
            show_config()
        else:
            print("\n❌ 重置配置失败！")
            
    except Exception as e:
        print(f"❌ 重置配置时发生错误: {e}")


def validate_config():
    """验证配置的合理性"""
    print("=" * 80)
    print("验证自动交易配置")
    print("=" * 80)
    
    try:
        config = get_auto_trade_config()
        issues = []
        
        # 检查滑点参数
        if config.max_slippage_percent <= 0 or config.max_slippage_percent > 10:
            issues.append("最大滑点百分比应该在 0-10% 之间")
        
        if config.low_risk_slippage_threshold >= config.high_risk_slippage_threshold:
            issues.append("低风险滑点阈值应该小于高风险滑点阈值")
        
        # 检查流动性参数
        if config.liquidity_threshold <= 0:
            issues.append("流动性阈值应该大于 0")
        
        if config.low_risk_liquidity_threshold <= config.high_risk_liquidity_threshold:
            issues.append("低风险流动性阈值应该大于高风险流动性阈值")
        
        # 检查订单大小
        if config.min_order_size <= 0 or config.min_order_size >= config.max_order_size:
            issues.append("最小订单金额应该大于 0 且小于最大订单金额")
        
        # 检查价格参数
        if config.price_improvement_factor < 0 or config.price_improvement_factor > 1:
            issues.append("价格改善因子应该在 0-1 之间")
        
        if config.safety_margin < 0 or config.safety_margin > 1:
            issues.append("安全边距应该在 0-1 之间")
        
        # 检查重试参数
        if config.max_retries < 0 or config.max_retries > 10:
            issues.append("最大重试次数应该在 0-10 之间")
        
        if config.retry_delay < 0 or config.retry_delay > 60:
            issues.append("重试延迟应该在 0-60 秒之间")
        
        # 显示结果
        if issues:
            print("\n⚠️ 发现以下配置问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ 配置验证通过，所有参数都在合理范围内！")
            
    except Exception as e:
        print(f"❌ 验证配置时发生错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动交易配置管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 显示配置命令
    subparsers.add_parser('show', help='显示当前配置')
    
    # 更新配置命令
    update_parser = subparsers.add_parser('update', help='更新配置')
    update_parser.add_argument('--max-slippage', type=float, help='最大滑点百分比')
    update_parser.add_argument('--liquidity-threshold', type=float, help='流动性阈值')
    update_parser.add_argument('--min-order-size', type=float, help='最小订单金额')
    update_parser.add_argument('--max-order-size', type=float, help='最大订单金额')
    update_parser.add_argument('--price-improvement', type=float, help='价格改善因子')
    update_parser.add_argument('--safety-margin', type=float, help='安全边距')
    update_parser.add_argument('--max-retries', type=int, help='最大重试次数')
    update_parser.add_argument('--retry-delay', type=float, help='重试延迟')
    update_parser.add_argument('--enable-slippage-protection', type=bool, help='启用滑点保护')
    update_parser.add_argument('--enable-liquidity-check', type=bool, help='启用流动性检查')
    update_parser.add_argument('--enable-size-validation', type=bool, help='启用订单大小验证')
    
    # 重置配置命令
    subparsers.add_parser('reset', help='重置为默认配置')
    
    # 验证配置命令
    subparsers.add_parser('validate', help='验证配置合理性')
    
    args = parser.parse_args()
    
    if args.command == 'show':
        show_config()
    elif args.command == 'update':
        updates = {}
        if args.max_slippage is not None:
            updates['max_slippage_percent'] = args.max_slippage
        if args.liquidity_threshold is not None:
            updates['liquidity_threshold'] = args.liquidity_threshold
        if args.min_order_size is not None:
            updates['min_order_size'] = args.min_order_size
        if args.max_order_size is not None:
            updates['max_order_size'] = args.max_order_size
        if args.price_improvement is not None:
            updates['price_improvement_factor'] = args.price_improvement
        if args.safety_margin is not None:
            updates['safety_margin'] = args.safety_margin
        if args.max_retries is not None:
            updates['max_retries'] = args.max_retries
        if args.retry_delay is not None:
            updates['retry_delay'] = args.retry_delay
        if args.enable_slippage_protection is not None:
            updates['enable_slippage_protection'] = args.enable_slippage_protection
        if args.enable_liquidity_check is not None:
            updates['enable_liquidity_check'] = args.enable_liquidity_check
        if args.enable_size_validation is not None:
            updates['enable_size_validation'] = args.enable_size_validation
        
        if updates:
            update_config(updates)
        else:
            print("❌ 没有指定要更新的配置项")
            
    elif args.command == 'reset':
        confirm = input("⚠️ 确定要重置所有配置为默认值吗？(y/N): ")
        if confirm.lower() == 'y':
            reset_config()
        else:
            print("取消重置操作")
            
    elif args.command == 'validate':
        validate_config()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
