"""
配置迁移测试脚本

测试统一配置管理系统的功能：
1. 初始化统一配置数据库
2. 测试 VLogger 配置读写
3. 测试邮件配置读写
4. 测试 Filter 黑名单配置
5. 测试已处理事件管理
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sys_configs import (
    init_config_database,
    get_vlogger_config,
    save_vlogger_config,
    get_email_config,
    save_email_config,
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    is_market_processed,
    mark_market_as_processed,
    clear_processed_markets,
)


def test_database_init():
    """测试数据库初始化"""
    print("\n" + "="*60)
    print("测试 1: 数据库初始化")
    print("="*60)
    
    success = init_config_database()
    if success:
        print("✓ 统一配置数据库初始化成功")
    else:
        print("✗ 统一配置数据库初始化失败")
    
    return success


def test_vlogger_config():
    """测试 VLogger 配置读写"""
    print("\n" + "="*60)
    print("测试 2: VLogger 配置读写")
    print("="*60)
    
    # 读取配置
    config = get_vlogger_config()
    print(f"✓ 读取 VLogger 配置成功，共 {len(config)} 项")
    print(f"  - service_name: {config.get('service_name')}")
    print(f"  - log_dir: {config.get('log_dir')}")
    print(f"  - min_level: {config.get('min_level')}")
    print(f"  - enable_console: {config.get('enable_console')}")
    
    # 修改配置
    test_config = {
        'service_name': 'test_service',
        'min_level': 'DEBUG',
    }
    success = save_vlogger_config(test_config)
    if success:
        print("✓ 保存 VLogger 配置成功")
    else:
        print("✗ 保存 VLogger 配置失败")
    
    # 验证修改
    updated_config = get_vlogger_config()
    if updated_config.get('service_name') == 'test_service':
        print("✓ 配置修改验证成功")
    else:
        print("✗ 配置修改验证失败")
    
    return success


def test_email_config():
    """测试邮件配置读写"""
    print("\n" + "="*60)
    print("测试 3: 邮件配置读写")
    print("="*60)
    
    # 读取配置
    config = get_email_config()
    print(f"✓ 读取邮件配置成功，共 {len(config)} 项")
    print(f"  - smtp_server: {config.get('smtp_server')}")
    print(f"  - smtp_port: {config.get('smtp_port')}")
    print(f"  - username: {config.get('username')}")
    print(f"  - use_ssl: {config.get('use_ssl')}")
    
    # 修改配置
    test_config = {
        'from_name': 'Test Alert System',
    }
    success = save_email_config(test_config)
    if success:
        print("✓ 保存邮件配置成功")
    else:
        print("✗ 保存邮件配置失败")
    
    # 验证修改
    updated_config = get_email_config()
    if updated_config.get('from_name') == 'Test Alert System':
        print("✓ 配置修改验证成功")
    else:
        print("✗ 配置修改验证失败")
    
    return success


def test_blacklist_config():
    """测试黑名单配置"""
    print("\n" + "="*60)
    print("测试 4: Filter 黑名单配置")
    print("="*60)
    
    # 读取黑名单
    blacklist = get_blacklist()
    print(f"✓ 读取黑名单配置成功")
    for bl_type, values in blacklist.items():
        print(f"  - {bl_type}: {values}")
    
    # 添加黑名单项
    success = add_blacklist_item('tag', 'test_tag')
    if success:
        print("✓ 添加黑名单项成功: tag = test_tag")
    else:
        print("✗ 添加黑名单项失败")
    
    # 验证添加
    updated_blacklist = get_blacklist('tag')
    if 'test_tag' in updated_blacklist.get('tag', []):
        print("✓ 黑名单项添加验证成功")
    else:
        print("✗ 黑名单项添加验证失败")
    
    # 删除黑名单项
    success = remove_blacklist_item('tag', 'test_tag')
    if success:
        print("✓ 删除黑名单项成功: tag = test_tag")
    else:
        print("✗ 删除黑名单项失败")
    
    # 验证删除
    updated_blacklist = get_blacklist('tag')
    if 'test_tag' not in updated_blacklist.get('tag', []):
        print("✓ 黑名单项删除验证成功")
    else:
        print("✗ 黑名单项删除验证失败")
    
    return True


def test_processed_markets():
    """测试已处理事件管理"""
    print("\n" + "="*60)
    print("测试 5: 已处理事件管理")
    print("="*60)
    
    test_market_id = "test_market_123"
    
    # 检查是否已处理
    is_processed = is_market_processed(test_market_id)
    print(f"✓ 检查市场处理状态: {is_processed}")
    
    # 标记为已处理
    success = mark_market_as_processed(test_market_id)
    if success:
        print(f"✓ 标记市场为已处理: {test_market_id}")
    else:
        print(f"✗ 标记市场失败")
    
    # 验证标记
    is_processed = is_market_processed(test_market_id)
    if is_processed:
        print("✓ 市场处理状态验证成功")
    else:
        print("✗ 市场处理状态验证失败")
    
    # 清理测试数据
    count = clear_processed_markets()
    print(f"✓ 清理已处理市场记录: {count} 条")
    
    return success


def test_vlogger_integration():
    """测试 VLogger 集成"""
    print("\n" + "="*60)
    print("测试 6: VLogger 集成测试")
    print("="*60)
    
    try:
        from backend.vlogger import get_logger, LogConfig
        
        # 测试从数据库加载配置
        config = LogConfig.from_database()
        print(f"✓ 从数据库加载 LogConfig 成功")
        print(f"  - service_name: {config.service_name}")
        print(f"  - log_dir: {config.log_dir}")
        print(f"  - min_level: {config.min_level}")
        
        # 测试保存配置到数据库
        config.service_name = "integration_test"
        success = config.save_to_database()
        if success:
            print("✓ 保存 LogConfig 到数据库成功")
        else:
            print("✗ 保存 LogConfig 到数据库失败")
        
        # 测试 get_logger 使用数据库配置
        logger = get_logger("test_service", use_db_config=True)
        print("✓ 使用数据库配置创建 logger 成功")
        
        return True
    except Exception as e:
        print(f"✗ VLogger 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_integration():
    """测试 Filter 集成"""
    print("\n" + "="*60)
    print("测试 7: Filter 集成测试")
    print("="*60)
    
    try:
        from backend.filter import EventFilter, MarketFilter
        
        # 测试 EventFilter 使用统一配置
        event_filter = EventFilter()
        print(f"✓ 创建 EventFilter 成功，使用数据库: {event_filter.db_path}")
        
        # 测试 MarketFilter 使用统一配置
        market_filter = MarketFilter()
        print(f"✓ 创建 MarketFilter 成功，使用数据库: {market_filter.db_path}")
        
        return True
    except Exception as e:
        print(f"✗ Filter 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("统一配置管理系统测试")
    print("="*60)
    
    try:
        # 测试 1: 数据库初始化
        if not test_database_init():
            print("\n✗ 数据库初始化失败，终止测试")
            return
        
        # 测试 2: VLogger 配置读写
        test_vlogger_config()
        
        # 测试 3: 邮件配置读写
        test_email_config()
        
        # 测试 4: 黑名单配置
        test_blacklist_config()
        
        # 测试 5: 已处理事件管理
        test_processed_markets()
        
        # 测试 6: VLogger 集成
        test_vlogger_integration()
        
        # 测试 7: Filter 集成
        test_filter_integration()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

