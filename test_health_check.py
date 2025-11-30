"""
健康检查功能测试脚本

测试节点延迟检测、数据库存储、统计分析和邮件报告功能。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.task_manager.health_check import (
    check_node,
    check_all_nodes,
    get_health_report,
    get_db,
    API_NODES
)
from backend.task_manager.email_report import (
    generate_health_report_html,
    generate_plain_text_report
)
from backend.vlogger import get_logger


logger = get_logger("test_health_check")


def test_single_node_check():
    """测试单个节点检测"""
    print("\n" + "="*60)
    print("测试1: 单个节点检测")
    print("="*60)
    
    node_url = API_NODES[0]
    print(f"检测节点: {node_url}")
    
    result = check_node(node_url)
    
    print(f"状态: {result.status}")
    print(f"延迟: {result.latency_ms:.2f} ms" if result.latency_ms else "延迟: N/A")
    print(f"错误信息: {result.error_msg}" if result.error_msg else "错误信息: 无")
    print(f"检测时间: {result.check_time}")
    
    return result


def test_all_nodes_check():
    """测试所有节点检测"""
    print("\n" + "="*60)
    print("测试2: 所有节点检测")
    print("="*60)
    
    results = check_all_nodes()
    
    print(f"检测节点数: {len(results)}")
    print(f"成功: {sum(1 for r in results if r.status == 'success')}")
    print(f"超时: {sum(1 for r in results if r.status == 'timeout')}")
    print(f"失败: {sum(1 for r in results if r.status == 'failed')}")
    
    print("\n详细结果:")
    for result in results:
        node_name = result.node_url.replace("https://", "").replace("http://", "").rstrip("/")
        status_icon = "✓" if result.status == "success" else "✗"
        latency_str = f"{result.latency_ms:.2f}ms" if result.latency_ms else "N/A"
        print(f"  {status_icon} {node_name}: {result.status} ({latency_str})")
    
    return results


def test_statistics():
    """测试统计分析"""
    print("\n" + "="*60)
    print("测试3: 统计分析")
    print("="*60)
    
    db = get_db()
    
    # 获取近24小时统计
    stats_24h = db.get_stats(hours=24)
    
    print(f"近24小时统计 (共 {len(stats_24h)} 个节点):")
    for stat in stats_24h:
        node_name = stat.node_url.replace("https://", "").replace("http://", "").rstrip("/")
        print(f"\n  节点: {node_name}")
        print(f"    平均延迟: {stat.avg_latency:.2f} ms")
        print(f"    最大延迟: {stat.max_latency:.2f} ms")
        print(f"    最小延迟: {stat.min_latency:.2f} ms")
        print(f"    成功率: {stat.success_rate * 100:.1f}%")
        print(f"    检测次数: {stat.successful_checks}/{stat.total_checks}")
    
    return stats_24h


def test_report_generation():
    """测试报告生成"""
    print("\n" + "="*60)
    print("测试4: 报告生成")
    print("="*60)
    
    # 获取报告数据
    report_data = get_health_report(hours_12=True, hours_72=True)
    
    print("报告数据:")
    if "12_hours" in report_data:
        print(f"  近12小时: {len(report_data['12_hours']['nodes'])} 个节点")
    if "72_hours" in report_data:
        print(f"  近3天: {len(report_data['72_hours']['nodes'])} 个节点")
    
    # 生成HTML报告
    html_content = generate_health_report_html(report_data)
    print(f"\nHTML报告长度: {len(html_content)} 字符")
    
    # 生成纯文本报告
    text_content = generate_plain_text_report(report_data)
    print(f"纯文本报告长度: {len(text_content)} 字符")
    
    # 保存HTML报告到文件
    output_file = "health_check_report.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nHTML报告已保存到: {output_file}")
    
    # 打印纯文本报告
    print("\n纯文本报告预览:")
    print("-" * 60)
    print(text_content)
    print("-" * 60)
    
    return report_data, html_content, text_content


def test_email_sending():
    """测试邮件发送（可选）"""
    print("\n" + "="*60)
    print("测试5: 邮件发送（可选）")
    print("="*60)
    
    
    from backend.vlogger.email_helper import email_send_with_db_config
    
    # 获取报告数据
    report_data = get_health_report(hours_12=True, hours_72=True)
    html_content = generate_health_report_html(report_data)
    text_content = generate_plain_text_report(report_data)
    
    # 发送邮件
    print("正在发送邮件...")
    success = email_send_with_db_config(
        subject="🏥 API节点健康检查测试报告",
        body_text=text_content,
        body_html=html_content
    )
    
    if success:
        print("✓ 邮件发送成功")
    else:
        print("✗ 邮件发送失败")
    
    return success


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("健康检查功能测试")
    print("="*60)
    
    try:
        # 测试1: 单个节点检测
        test_single_node_check()
        
        # 测试2: 所有节点检测
        test_all_nodes_check()
        
        # 测试3: 统计分析
        test_statistics()
        
        # 测试4: 报告生成
        test_report_generation()
        
        # 测试5: 邮件发送（可选）
        test_email_sending()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        
    except Exception as e:
        logger.error(
            "TEST.FAILED",
            msg="测试执行失败",
            error_code="E-TEST-001",
            extra={"error": str(e)}
        )
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

