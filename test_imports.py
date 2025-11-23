"""
测试 backend 包的导入是否正常工作

验证重构后的相对导入是否正确
"""

import sys
import traceback

def test_import(module_path, description):
    """测试单个模块的导入"""
    try:
        exec(f"import {module_path}")
        print(f"✓ {description}: {module_path}")
        return True
    except Exception as e:
        print(f"✗ {description}: {module_path}")
        print(f"  错误: {e}")
        traceback.print_exc()
        return False

def main():
    """运行所有导入测试"""
    print("=" * 80)
    print("Backend 包导入测试")
    print("=" * 80)
    
    tests = [
        # 主包
        ("backend", "主包"),
        
        # VLogger
        ("backend.vlogger", "VLogger 日志系统"),
        
        # Polymarket API
        ("backend.polymarket_api", "Polymarket API"),
        ("backend.polymarket_api.gamma_markets", "Gamma Markets API"),
        ("backend.polymarket_api.clob_api", "CLOB API"),
        ("backend.polymarket_api.orderbook_api", "Orderbook API"),
        
        # 系统配置
        ("backend.sys_configs", "系统配置"),
        ("backend.sys_configs.global_event_reg", "全局事件注册"),
        
        # AI 分析
        ("backend.ai_analysis", "AI 分析模块"),
        
        # 过滤器
        ("backend.filter", "过滤器模块"),
        
        # 自动决策
        ("backend.auto_decision", "自动决策模块"),
        
        # 自动交易
        ("backend.auto_trade", "自动交易模块"),
        
        # 健康检查
        ("backend.health_checker", "健康检查系统"),
    ]
    
    passed = 0
    failed = 0
    
    for module_path, description in tests:
        if test_import(module_path, description):
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

