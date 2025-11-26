"""
TokenRefresher 使用示例

演示如何使用 TokenRefresher 管理和监控 token 过期状态。
"""

from datetime import datetime, timedelta
from token_refresher import TokenRefresher, TokenType, get_token_refresher


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)
    
    # 获取 TokenRefresher 实例（单例模式）
    refresher = get_token_refresher(
        check_interval_minutes=10,  # 每 10 分钟检查一次
        auto_start=True  # 自动启动后台检查线程
    )
    
    # 更新 coze_token（自动计算过期时间：30天后）
    refresher.update_token(
        token_type=TokenType.COZE_TOKEN.value,
        token_value="pat_7WIJOd6lO8cDox7ciTFaL4CX2dJdBrb0P5qMZLRdng2IvjgKSpJtobzmlIEtJ8D"
    )
    
    # 更新 auth_token（自动计算过期时间：7天后）
    refresher.update_token(
        token_type=TokenType.AUTH_TOKEN.value,
        token_value="auth_token_example_value"
    )
    
    # 更新 access_token（自动计算过期时间：1天后）
    refresher.update_token(
        token_type=TokenType.ACCESS_TOKEN.value,
        token_value="access_token_example_value"
    )
    
    print("✓ 已更新所有 token")
    print()


def example_custom_expiry():
    """自定义过期时间示例"""
    print("=" * 60)
    print("示例 2: 自定义过期时间")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 手动指定过期时间（3天后）
    custom_expiry = datetime.now() + timedelta(days=3)
    refresher.update_token(
        token_type=TokenType.COZE_TOKEN.value,
        token_value="custom_token_value",
        expires_at=custom_expiry
    )
    
    print(f"✓ 已设置 coze_token 过期时间为: {custom_expiry.isoformat()}")
    print()


def example_add_custom_token_type():
    """添加自定义 token 类型示例"""
    print("=" * 60)
    print("示例 3: 添加自定义 token 类型")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 添加新的 token 类型
    refresher.add_token_type(
        token_type="api_key",
        validity_days=90,  # 90天有效期
        description="第三方 API 密钥"
    )
    
    # 更新新类型的 token
    refresher.update_token(
        token_type="api_key",
        token_value="sk-1234567890abcdef"
    )
    
    print("✓ 已添加自定义 token 类型: api_key (90天有效期)")
    print()


def example_check_status():
    """检查 token 状态示例"""
    print("=" * 60)
    print("示例 4: 检查 token 状态")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 获取单个 token 状态
    status = refresher.get_token_status(TokenType.COZE_TOKEN.value)
    if status:
        print(f"Token 类型: {status['token_type']}")
        print(f"过期时间: {status['expires_at']}")
        print(f"是否过期: {'是' if status['is_expired'] else '否'}")
        print(f"最后检查: {status['last_checked_at']}")
    
    print()
    
    # 获取所有 token 状态
    all_status = refresher.get_all_token_status()
    print(f"共有 {len(all_status)} 个 token:")
    for token_type, info in all_status.items():
        print(f"  - {token_type}: {'已过期' if info['is_expired'] else '有效'} "
              f"(过期时间: {info['expires_at']})")
    
    print()


def example_manual_check():
    """手动检查所有 token 示例"""
    print("=" * 60)
    print("示例 5: 手动检查所有 token")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 手动触发检查
    result = refresher.check_all_tokens()
    
    print("检查结果:")
    for token_type, is_expired in result.items():
        status = "已过期 ⚠️" if is_expired else "有效 ✓"
        print(f"  - {token_type}: {status}")
    
    print()


def example_set_expired():
    """手动标记 token 为过期示例"""
    print("=" * 60)
    print("示例 6: 手动标记 token 为过期")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 手动将 access_token 标记为过期
    # 这将立即触发邮件告警
    refresher.set_expired_immediate(TokenType.ACCESS_TOKEN.value)
    
    print("✓ 已将 access_token 标记为过期")
    print("⚠️  已发送邮件告警")
    print()


def example_change_check_interval():
    """修改检查间隔示例"""
    print("=" * 60)
    print("示例 7: 修改检查间隔")
    print("=" * 60)
    
    refresher = get_token_refresher()
    
    # 修改检查间隔为 5 分钟
    refresher.set_check_interval(5)
    
    print("✓ 已将检查间隔修改为 5 分钟")
    print()


def example_start_stop():
    """启动和停止后台检查线程示例"""
    print("=" * 60)
    print("示例 8: 启动和停止后台检查线程")
    print("=" * 60)
    
    # 创建实例但不自动启动
    refresher = get_token_refresher(auto_start=False)
    
    print(f"线程运行状态: {refresher.is_running()}")
    
    # 手动启动
    refresher.start()
    print(f"启动后状态: {refresher.is_running()}")
    
    # 停止线程
    refresher.stop()
    print(f"停止后状态: {refresher.is_running()}")
    
    print()


def example_complete_workflow():
    """完整工作流示例"""
    print("=" * 60)
    print("示例 9: 完整工作流")
    print("=" * 60)
    
    # 1. 初始化 TokenRefresher
    refresher = get_token_refresher(
        check_interval_minutes=10,
        auto_start=True
    )
    
    # 2. 更新所有默认 token
    tokens = {
        TokenType.COZE_TOKEN.value: "pat_7WIJOd6lO8cDox7ciTFaL4CX2dJdBrb0P5qMZLRdng2IvjgKSpJtobzmlIEtJ8D",
        TokenType.AUTH_TOKEN.value: "auth_token_value",
        TokenType.ACCESS_TOKEN.value: "access_token_value",
    }
    
    for token_type, token_value in tokens.items():
        refresher.update_token(token_type, token_value)
    
    print("✓ 已更新所有 token")
    
    # 3. 添加自定义 token 类型
    refresher.add_token_type(
        token_type="refresh_token",
        validity_days=14,
        description="刷新令牌"
    )
    refresher.update_token(
        token_type="refresh_token",
        token_value="refresh_token_value"
    )
    
    print("✓ 已添加自定义 token 类型")
    
    # 4. 查看所有 token 状态
    all_status = refresher.get_all_token_status()
    print(f"\n当前共有 {len(all_status)} 个 token:")
    for token_type, info in all_status.items():
        print(f"  - {info['description']} ({token_type})")
        print(f"    有效期: {info['validity_days']} 天")
        print(f"    过期时间: {info['expires_at']}")
        print(f"    状态: {'已过期' if info['is_expired'] else '有效'}")
    
    # 5. 后台线程会自动每 10 分钟检查一次
    print(f"\n✓ 后台检查线程运行中: {refresher.is_running()}")
    print("  每 10 分钟自动检查一次，发现过期会发送邮件告警")
    
    print()


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_custom_expiry()
    example_add_custom_token_type()
    example_check_status()
    example_manual_check()
    example_set_expired()
    example_change_check_interval()
    example_start_stop()
    example_complete_workflow()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

