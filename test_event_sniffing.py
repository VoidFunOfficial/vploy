"""
测试事件嗅探任务

用于测试和立即执行event_sniffing任务
"""

from backend.task_manager import (
    TaskDatabase,
    get_scheduler,
    list_scheduled_tasks,
    init_task_manager
)
from backend.vlogger import get_logger

logger = get_logger("test_event_sniffing")


def show_task_info():
    """显示任务信息"""
    print("\n" + "="*60)
    print("定时任务列表")
    print("="*60)
    
    tasks = list_scheduled_tasks(enabled_only=False)
    
    for task in tasks:
        print(f"\n任务名称: {task['name']}")
        print(f"  类型: {task['task_type']}")
        print(f"  调度: {task['schedule']}")
        print(f"  启用: {task['enabled']}")
        print(f"  上次运行: {task['last_run']}")
        print(f"  下次运行: {task['next_run']}")
        print(f"  描述: {task['metadata'].get('description', 'N/A')}")


def run_event_sniffing_now():
    """立即执行事件嗅探任务"""
    print("\n" + "="*60)
    print("立即执行事件嗅探任务")
    print("="*60)
    
    # 获取数据库实例
    db = TaskDatabase()
    
    # 查找event_sniffing任务
    task = db.get_scheduled_task_by_name("event_sniffing")
    
    if not task:
        print("❌ 未找到event_sniffing任务")
        return
    
    print(f"\n找到任务: {task.name}")
    print(f"  下次运行时间: {task.next_run}")
    
    # 获取调度器并执行任务
    scheduler = get_scheduler()
    
    print("\n开始执行任务...")
    try:
        scheduler._execute_task(task)
        print("✅ 任务执行完成")
        
        # 更新最后运行时间
        from datetime import datetime
        task.last_run = datetime.now()
        db.update_scheduled_task(task)
        
    except Exception as e:
        print(f"❌ 任务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


def reset_next_run():
    """重置event_sniffing的下次运行时间为立即执行"""
    print("\n" + "="*60)
    print("重置下次运行时间")
    print("="*60)
    
    from datetime import datetime
    
    db = TaskDatabase()
    task = db.get_scheduled_task_by_name("event_sniffing")
    
    if not task:
        print("❌ 未找到event_sniffing任务")
        return
    
    # 设置为当前时间,让调度器立即执行
    task.next_run = datetime.now()
    db.update_scheduled_task(task)
    
    print(f"✅ 已重置下次运行时间为: {task.next_run}")
    print("调度器将在下一次检查时执行此任务(默认60秒检查间隔)")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("事件嗅探任务测试工具")
    print("="*60)
    
    # 初始化任务管理器
    print("\n初始化任务管理器...")
    try:
        init_task_manager()
        print("✅ 任务管理器初始化完成")
    except Exception as e:
        print(f"⚠️  任务管理器可能已初始化: {str(e)}")
    
    while True:
        print("\n" + "="*60)
        print("请选择操作:")
        print("="*60)
        print("1. 查看所有定时任务")
        print("2. 立即执行事件嗅探任务")
        print("3. 重置下次运行时间(让调度器自动执行)")
        print("4. 查看异步任务队列")
        print("0. 退出")
        print("="*60)
        
        choice = input("\n请输入选项 (0-4): ").strip()
        
        if choice == "1":
            show_task_info()
        elif choice == "2":
            run_event_sniffing_now()
        elif choice == "3":
            reset_next_run()
        elif choice == "4":
            show_async_tasks()
        elif choice == "0":
            print("\n再见!")
            break
        else:
            print("\n❌ 无效选项,请重新选择")


def show_async_tasks():
    """显示异步任务队列"""
    print("\n" + "="*60)
    print("异步任务队列 (最近20条)")
    print("="*60)
    
    db = TaskDatabase()
    
    # 查询最近的任务
    from backend.task_manager import TaskStage, TaskStatus
    
    tasks = db.query_async_tasks(limit=20)
    
    if not tasks:
        print("\n暂无任务")
        return
    
    for task in tasks:
        print(f"\n任务ID: {task.id}")
        print(f"  阶段: {task.stage.value}")
        print(f"  状态: {task.status.value}")
        print(f"  创建时间: {task.create_time}")
        print(f"  元数据: {task.metadata}")
        if task.error_msg:
            print(f"  错误: {task.error_msg}")


if __name__ == "__main__":
    main()

