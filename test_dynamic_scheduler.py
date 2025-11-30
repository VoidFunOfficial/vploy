"""
动态调度器测试脚本

测试动态调度器的功能，包括任务执行、动态修改调度配置等。
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.task_manager import (
    init_task_manager,
    get_scheduler,
    TaskDatabase,
    add_scheduled_task,
    update_scheduled_task,
    list_scheduled_tasks
)
from backend.vlogger import get_logger


logger = get_logger("test_dynamic_scheduler")


def test_scheduler_init():
    """测试调度器初始化"""
    print("\n" + "="*60)
    print("测试1: 调度器初始化")
    print("="*60)
    
    # 初始化任务管理器（会自动启动动态调度器）
    init_task_manager()
    
    # 获取调度器实例
    scheduler = get_scheduler()
    
    print(f"调度器运行状态: {scheduler.running}")
    print(f"检查间隔: {scheduler.check_interval}秒")
    print(f"已注册的任务执行器: {list(scheduler.task_executors.keys())}")
    
    return scheduler


def test_list_tasks():
    """测试列出所有任务"""
    print("\n" + "="*60)
    print("测试2: 列出所有定时任务")
    print("="*60)
    
    tasks = list_scheduled_tasks()
    
    print(f"共有 {len(tasks)} 个定时任务:\n")
    for task in tasks:
        print(f"任务名称: {task['name']}")
        print(f"  类型: {task['task_type']}")
        print(f"  调度配置: {task['schedule']}")
        print(f"  状态: {'启用' if task['enabled'] else '禁用'}")
        print(f"  上次运行: {task['last_run'] or '未运行'}")
        print(f"  下次运行: {task['next_run'] or '未计算'}")
        print(f"  描述: {task['metadata'].get('description', '无')}")
        print()
    
    return tasks


def test_create_test_task():
    """测试创建测试任务"""
    print("\n" + "="*60)
    print("测试3: 创建测试任务")
    print("="*60)
    
    # 创建一个每分钟执行的测试任务
    task_id = add_scheduled_task(
        name="test_task_1min",
        task_type="interval",
        schedule="60",  # 每60秒
        enabled=True,
        metadata={
            "description": "测试任务 - 每分钟执行一次",
            "test": True
        }
    )
    
    print(f"创建测试任务成功，ID: {task_id}")
    
    # 查看任务信息
    db = TaskDatabase()
    task = db.get_scheduled_task(task_id)
    print(f"任务名称: {task.name}")
    print(f"调度配置: {task.schedule}")
    print(f"下次运行: {task.next_run}")
    
    return task_id


def test_update_task_schedule():
    """测试动态修改任务调度配置"""
    print("\n" + "="*60)
    print("测试4: 动态修改任务调度配置")
    print("="*60)
    
    # 修改 health_report 任务的执行时间
    print("修改 health_report 任务的执行时间...")
    
    db = TaskDatabase()
    task = db.get_scheduled_task_by_name("health_report")
    
    if task:
        print(f"原调度配置: {task.schedule}")
        print(f"原下次运行: {task.next_run}")
        
        # 修改为每天晚上10点
        new_schedule = "0 22 * * *"
        update_scheduled_task(
            name="health_report",
            schedule=new_schedule
        )
        
        # 重新获取任务
        task = db.get_scheduled_task_by_name("health_report")
        print(f"新调度配置: {task.schedule}")
        print(f"新下次运行: {task.next_run}")
        print("✓ 修改成功！调度器会在下次检查时使用新配置")
    else:
        print("✗ 未找到 health_report 任务")


def test_toggle_task():
    """测试启用/禁用任务"""
    print("\n" + "="*60)
    print("测试5: 启用/禁用任务")
    print("="*60)
    
    db = TaskDatabase()
    task = db.get_scheduled_task_by_name("profit_email")
    
    if task:
        original_status = task.enabled
        print(f"原状态: {'启用' if original_status else '禁用'}")
        
        # 切换状态
        update_scheduled_task(
            name="profit_email",
            enabled=not original_status
        )
        
        # 重新获取任务
        task = db.get_scheduled_task_by_name("profit_email")
        print(f"新状态: {'启用' if task.enabled else '禁用'}")
        
        # 恢复原状态
        update_scheduled_task(
            name="profit_email",
            enabled=original_status
        )
        print(f"已恢复原状态: {'启用' if original_status else '禁用'}")
    else:
        print("✗ 未找到 profit_email 任务")


def test_scheduler_execution():
    """测试调度器执行（等待一段时间观察）"""
    print("\n" + "="*60)
    print("测试6: 调度器执行测试")
    print("="*60)
    
    print("调度器正在后台运行...")
    print("等待60秒观察任务执行情况...")
    print("(可以查看日志文件了解详细执行情况)")
    
    # 等待60秒
    for i in range(60, 0, -10):
        print(f"剩余 {i} 秒...")
        time.sleep(10)
    
    print("✓ 观察完成")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("动态调度器功能测试")
    print("="*60)
    
    try:
        # 测试1: 初始化调度器
        scheduler = test_scheduler_init()
        
        # 测试2: 列出所有任务
        test_list_tasks()
        
        # 测试3: 创建测试任务
        # test_create_test_task()
        
        # 测试4: 动态修改任务调度配置
        test_update_task_schedule()
        
        # 测试5: 启用/禁用任务
        test_toggle_task()
        
        # 测试6: 调度器执行测试（可选）
        # test_scheduler_execution()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        print("\n提示:")
        print("1. 动态调度器已在后台运行")
        print("2. 可以通过前端界面修改任务配置，修改会立即生效")
        print("3. 查看日志文件了解任务执行详情")
        print("4. 按 Ctrl+C 退出测试")
        
        # 保持运行以观察调度器
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n正在停止调度器...")
            scheduler.stop()
            print("调度器已停止")
        
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

