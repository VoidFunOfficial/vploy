"""
任务管理器模块

基于Huey和SQLite实现的异步任务和定时任务管理系统。

主要功能:
- 异步任务队列：支持多阶段任务处理（mark, analysis, decision, trade, listen）
- 任务路由机制：根据stage和status自动路由到对应的处理函数
- 定时任务调度：支持cron表达式和间隔时间的定时任务
- 数据持久化：使用SQLite存储任务数据和状态
- 日志集成：集成VLogger日志系统进行全链路追踪

使用示例:
    # 提交异步任务
    >>> from backend.task_manager import submit_task, AsyncTask, TaskStage, TaskStatus
    >>> task = AsyncTask(stage=TaskStage.MARK, status=TaskStatus.WAITING, metadata={"event_id": "123"})
    >>> task_id = submit_task(task)
    
    # 添加定时任务
    >>> from backend.task_manager import add_scheduled_task
    >>> task_id = add_scheduled_task(
    ...     name="my_task",
    ...     task_type="interval",
    ...     schedule="3600",  # 每小时执行一次
    ...     enabled=True
    ... )
    
    # 启动Huey消费者
    >>> from backend.task_manager import huey
    >>> # 在命令行运行: huey_consumer backend.task_manager.huey
"""

from .config import TaskManagerConfig, get_config, set_config
from .models import (
    AsyncTask,
    ScheduledTask,
    TaskStage,
    TaskStatus,
    TaskDatabase
)
from .tasks import (
    huey,
    submit_task,
    process_async_task,
    register_handler,
    get_handler,
    execute_split_analysis_task,
    execute_scheduled_task,
    execute_poll_analysis_once
)
from .scheduler import (
    add_scheduled_task,
    update_scheduled_task,
    get_scheduled_task_info,
    list_scheduled_tasks,
    init_default_scheduled_tasks,
    health_check_email,
    health_report,
    profit_email
)
from .dynamic_scheduler import (
    DynamicScheduler,
    get_scheduler,
    start_dynamic_scheduler,
    stop_dynamic_scheduler
)

__all__ = [
    # 配置
    "TaskManagerConfig",
    "get_config",
    "set_config",

    # 模型
    "AsyncTask",
    "ScheduledTask",
    "TaskStage",
    "TaskStatus",
    "TaskDatabase",

    # 异步任务
    "huey",
    "submit_task",
    "process_async_task",
    "register_handler",
    "get_handler",
    "execute_split_analysis_task",
    "execute_scheduled_task",
    "execute_poll_analysis_once",

    # 定时任务
    "add_scheduled_task",
    "update_scheduled_task",
    "get_scheduled_task_info",
    "list_scheduled_tasks",
    "init_default_scheduled_tasks",
    "health_check_email",
    "health_report",
    "profit_email",

    # 动态调度器
    "DynamicScheduler",
    "get_scheduler",
    "start_dynamic_scheduler",
    "stop_dynamic_scheduler",
]


# 模块初始化
def init_task_manager():
    """
    初始化任务管理器

    在应用启动时调用，执行以下操作：
    1. 初始化数据库
    2. 初始化预定义的定时任务
    3. 启动动态调度器
    """
    from ..vlogger import get_logger

    logger = get_logger("task_manager")
    logger.info(
        "TASK_MANAGER.INIT.START",
        msg="初始化任务管理器"
    )

    try:
        # 初始化数据库
        db = TaskDatabase()
        logger.info(
            "TASK_MANAGER.INIT.DB",
            msg="数据库初始化完成"
        )

        # 初始化预定义定时任务
        init_default_scheduled_tasks()

        # 启动动态调度器
        start_dynamic_scheduler()
        logger.info(
            "TASK_MANAGER.INIT.SCHEDULER",
            msg="动态调度器已启动"
        )

        logger.info(
            "TASK_MANAGER.INIT.SUCCESS",
            msg="任务管理器初始化完成"
        )

    except Exception as e:
        logger.error(
            "TASK_MANAGER.INIT.FAILED",
            msg="任务管理器初始化失败",
            error_code="E-TASK-MANAGER-001",
            extra={"error": str(e)}
        )
        raise

