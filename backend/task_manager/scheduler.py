"""
定时任务调度模块

实现基于Huey的定时任务管理和调度功能。
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from huey import crontab

from .tasks import huey, logger
from .models import ScheduledTask, TaskDatabase
from .health_check import check_all_nodes, get_health_report, get_db as get_health_db
from .email_report import generate_health_report_html, generate_plain_text_report
from ..vlogger.email_helper import email_send_with_db_config
from ..vlogger import TraceContext


# 初始化数据库
db = TaskDatabase()


# ==================== 定时任务管理 ====================

def add_scheduled_task(
    name: str,
    task_type: str = "interval",
    schedule: str = "3600",
    enabled: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    添加定时任务
    
    参数:
        name: 任务名称（唯一标识）
        task_type: 任务类型，可选值: "interval"（间隔秒数）或 "cron"（cron表达式）
        schedule: 调度配置
            - 如果task_type="interval"，则为间隔秒数（字符串），如 "3600" 表示每小时
            - 如果task_type="cron"，则为cron表达式，如 "0 9 * * *" 表示每天9点
        enabled: 是否启用
        metadata: 任务元数据
        
    返回:
        int: 任务ID
    """
    # 检查任务是否已存在
    existing_task = db.get_scheduled_task_by_name(name)
    if existing_task:
        logger.warn(
            "SCHEDULER.TASK.EXISTS",
            msg=f"定时任务已存在: {name}",
            extra={"name": name}
        )
        return existing_task.id
    
    # 创建任务
    task = ScheduledTask(
        name=name,
        task_type=task_type,
        schedule=schedule,
        enabled=enabled,
        metadata=metadata or {}
    )
    
    task_id = db.create_scheduled_task(task)
    
    logger.info(
        "SCHEDULER.TASK.ADDED",
        msg=f"添加定时任务: {name}",
        extra={
            "task_id": task_id,
            "name": name,
            "task_type": task_type,
            "schedule": schedule,
            "enabled": enabled
        }
    )
    
    return task_id


def update_scheduled_task(
    name: str,
    task_type: Optional[str] = None,
    schedule: Optional[str] = None,
    enabled: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    更新定时任务配置
    
    参数:
        name: 任务名称
        task_type: 任务类型（可选）
        schedule: 调度配置（可选）
        enabled: 是否启用（可选）
        metadata: 任务元数据（可选）
    """
    task = db.get_scheduled_task_by_name(name)
    if task is None:
        logger.error(
            "SCHEDULER.TASK.NOT_FOUND",
            msg=f"定时任务不存在: {name}",
            error_code="E-SCHEDULER-001",
            extra={"name": name}
        )
        return
    
    # 更新字段
    if task_type is not None:
        task.task_type = task_type
    if schedule is not None:
        task.schedule = schedule
    if enabled is not None:
        task.enabled = enabled
    if metadata is not None:
        task.metadata = metadata
    
    db.update_scheduled_task(task)
    
    logger.info(
        "SCHEDULER.TASK.UPDATED",
        msg=f"更新定时任务: {name}",
        extra={
            "name": name,
            "task_type": task.task_type,
            "schedule": task.schedule,
            "enabled": task.enabled
        }
    )


def get_scheduled_task_info(name: str) -> Optional[Dict[str, Any]]:
    """
    获取定时任务信息
    
    参数:
        name: 任务名称
        
    返回:
        Dict[str, Any]: 任务信息，如果不存在则返回None
    """
    task = db.get_scheduled_task_by_name(name)
    if task is None:
        return None
    
    return task.to_dict()


def list_scheduled_tasks(enabled_only: bool = False) -> list:
    """
    列出所有定时任务
    
    参数:
        enabled_only: 是否只返回启用的任务
        
    返回:
        list: 任务列表
    """
    tasks = db.get_all_scheduled_tasks(enabled_only=enabled_only)
    return [task.to_dict() for task in tasks]


# ==================== 预定义定时任务 ====================

@huey.periodic_task(crontab(minute='*/5'))
def periodic_health_check():
    """
    定时健康检查任务

    每5分钟执行一次节点健康检查。
    """
    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULER.PERIODIC_CHECK.START",
            msg="开始执行定时健康检查",
            trace_id=trace_id
        )

        try:
            # 执行健康检查
            results = check_all_nodes()

            # 清理旧数据
            health_db = get_health_db()
            health_db.cleanup_old_data(days=7)

            logger.info(
                "SCHEDULER.PERIODIC_CHECK.SUCCESS",
                msg="定时健康检查执行成功",
                extra={
                    "total": len(results),
                    "success": sum(1 for r in results if r.status == "success"),
                    "timeout": sum(1 for r in results if r.status == "timeout"),
                    "failed": sum(1 for r in results if r.status == "failed")
                },
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "SCHEDULER.PERIODIC_CHECK.FAILED",
                msg="定时健康检查执行失败",
                error_code="E-SCHEDULER-004",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.periodic_task(crontab(hour='9', minute='0'))
def health_check_email():
    """
    健康检查邮件任务

    每天早上9点发送系统健康检查邮件。
    """
    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULER.HEALTH_CHECK.START",
            msg="开始执行健康检查邮件任务",
            trace_id=trace_id
        )

        try:
            # 更新任务运行时间
            task = db.get_scheduled_task_by_name("health_check_email")
            if task:
                task.last_run = datetime.now()
                task.next_run = datetime.now() + timedelta(days=1)
                db.update_scheduled_task(task)

            # 获取健康检查报告数据
            report_data = get_health_report(hours_12=True, hours_72=True)

            # 生成HTML和纯文本报告
            html_content = generate_health_report_html(report_data)
            text_content = generate_plain_text_report(report_data)

            # 发送邮件
            success = email_send_with_db_config(
                subject="🏥 API节点健康检查日报",
                body_text=text_content,
                body_html=html_content
            )

            if success:
                logger.info(
                    "SCHEDULER.HEALTH_CHECK.SUCCESS",
                    msg="健康检查邮件任务执行成功",
                    trace_id=trace_id
                )
            else:
                logger.error(
                    "SCHEDULER.HEALTH_CHECK.EMAIL_FAILED",
                    msg="健康检查邮件发送失败",
                    error_code="E-SCHEDULER-005",
                    trace_id=trace_id
                )

        except Exception as e:
            logger.error(
                "SCHEDULER.HEALTH_CHECK.FAILED",
                msg="健康检查邮件任务执行失败",
                error_code="E-SCHEDULER-002",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.periodic_task(crontab(hour='21', minute='0'))
def health_report():
    """
    健康报告定时任务

    每天晚上9点发送包含3天+12小时延迟统计的网页形式报告。
    """
    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULER.HEALTH_REPORT.START",
            msg="开始执行健康报告任务",
            trace_id=trace_id
        )

        try:
            # 更新任务运行时间
            task = db.get_scheduled_task_by_name("health_report")
            if task:
                task.last_run = datetime.now()
                task.next_run = datetime.now() + timedelta(days=1)
                db.update_scheduled_task(task)

            # 获取健康检查报告数据（3天 + 12小时）
            report_data = get_health_report(hours_12=True, hours_72=True)

            # 生成HTML和纯文本报告
            html_content = generate_health_report_html(report_data)
            text_content = generate_plain_text_report(report_data)

            # 发送邮件
            success = email_send_with_db_config(
                subject="📊 API节点健康统计报告 (3天+12小时)",
                body_text=text_content,
                body_html=html_content
            )

            if success:
                logger.info(
                    "SCHEDULER.HEALTH_REPORT.SUCCESS",
                    msg="健康报告任务执行成功",
                    trace_id=trace_id
                )
            else:
                logger.error(
                    "SCHEDULER.HEALTH_REPORT.EMAIL_FAILED",
                    msg="健康报告邮件发送失败",
                    error_code="E-SCHEDULER-006",
                    trace_id=trace_id
                )

        except Exception as e:
            logger.error(
                "SCHEDULER.HEALTH_REPORT.FAILED",
                msg="健康报告任务执行失败",
                error_code="E-SCHEDULER-007",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.periodic_task(crontab(hour='18', minute='0'))
def profit_email():
    """
    收益报告邮件任务

    每天下午6点发送收益报告邮件。
    """
    logger.info(
        "SCHEDULER.PROFIT.START",
        msg="开始执行收益报告邮件任务"
    )
    
    try:
        # 更新任务运行时间
        task = db.get_scheduled_task_by_name("profit_email")
        if task:
            task.last_run = datetime.now()
            task.next_run = datetime.now() + timedelta(days=1)
            db.update_scheduled_task(task)
        
        # TODO: 实现收益报告逻辑
        # 1. 统计当日交易数据
        # 2. 计算收益和损失
        # 3. 生成收益报告
        # 4. 发送邮件
        
        logger.info(
            "SCHEDULER.PROFIT.SUCCESS",
            msg="收益报告邮件任务执行成功"
        )
        
    except Exception as e:
        logger.error(
            "SCHEDULER.PROFIT.FAILED",
            msg="收益报告邮件任务执行失败",
            error_code="E-SCHEDULER-003",
            extra={"error": str(e)}
        )


# ==================== 初始化预定义任务 ====================

def init_default_scheduled_tasks():
    """
    初始化预定义的定时任务

    在系统启动时调用，确保预定义任务存在于数据库中，并计算下次运行时间。
    """
    logger.info(
        "SCHEDULER.INIT.START",
        msg="初始化预定义定时任务"
    )

    from datetime import datetime, timedelta
    from croniter import croniter

    now = datetime.now()

    # 定期健康检查任务（每5分钟）
    periodic_check_cron = "*/5 * * * *"  # 每5分钟
    periodic_check_next = croniter(periodic_check_cron, now).get_next(datetime)

    task_id = add_scheduled_task(
        name="periodic_health_check",
        task_type="cron",
        schedule=periodic_check_cron,
        enabled=True,
        metadata={
            "description": "定期健康检查 - 每5分钟检测所有API节点",
            "recipients": [],
            "auto_created": True,
            "huey_task": False  # 由动态调度器执行
        }
    )

    # 更新下次运行时间
    task = db.get_scheduled_task(task_id)
    if task and not task.next_run:
        task.next_run = periodic_check_next
        db.update_scheduled_task(task)
        logger.info(
            "SCHEDULER.INIT.PERIODIC_CHECK",
            msg=f"定期健康检查任务已初始化，下次运行: {periodic_check_next}",
            extra={"task_id": task_id, "next_run": periodic_check_next.isoformat()}
        )

    # 健康检查邮件任务
    health_check_cron = "0 9 * * *"  # 每天早上9点
    health_check_next = croniter(health_check_cron, now).get_next(datetime)

    task_id = add_scheduled_task(
        name="health_check_email",
        task_type="cron",
        schedule=health_check_cron,
        enabled=True,
        metadata={
            "description": "系统健康检查邮件 - 每天早上9点发送",
            "recipients": [],
            "auto_created": True,
            "huey_task": False  # 由动态调度器执行
        }
    )

    # 更新下次运行时间
    task = db.get_scheduled_task(task_id)
    if task and not task.next_run:
        task.next_run = health_check_next
        db.update_scheduled_task(task)
        logger.info(
            "SCHEDULER.INIT.HEALTH_CHECK",
            msg=f"健康检查任务已初始化，下次运行: {health_check_next}",
            extra={"task_id": task_id, "next_run": health_check_next.isoformat()}
        )

    # 健康报告任务（3天+12小时统计）
    health_report_cron = "0 21 * * *"  # 每天晚上9点
    health_report_next = croniter(health_report_cron, now).get_next(datetime)

    task_id = add_scheduled_task(
        name="health_report",
        task_type="cron",
        schedule=health_report_cron,
        enabled=True,
        metadata={
            "description": "健康统计报告 - 每天晚上9点发送3天+12小时延迟统计",
            "recipients": [],
            "auto_created": True,
            "huey_task": False  # 由动态调度器执行
        }
    )

    # 更新下次运行时间
    task = db.get_scheduled_task(task_id)
    if task and not task.next_run:
        task.next_run = health_report_next
        db.update_scheduled_task(task)
        logger.info(
            "SCHEDULER.INIT.HEALTH_REPORT",
            msg=f"健康报告任务已初始化，下次运行: {health_report_next}",
            extra={"task_id": task_id, "next_run": health_report_next.isoformat()}
        )

    # 收益报告邮件任务
    profit_cron = "0 18 * * *"  # 每天下午6点
    profit_next = croniter(profit_cron, now).get_next(datetime)

    task_id = add_scheduled_task(
        name="profit_email",
        task_type="cron",
        schedule=profit_cron,
        enabled=True,
        metadata={
            "description": "每日收益报告邮件 - 每天下午6点发送",
            "recipients": [],
            "auto_created": True,
            "huey_task": False  # 由动态调度器执行
        }
    )

    # 更新下次运行时间
    task = db.get_scheduled_task(task_id)
    if task and not task.next_run:
        task.next_run = profit_next
        db.update_scheduled_task(task)
        logger.info(
            "SCHEDULER.INIT.PROFIT",
            msg=f"收益报告任务已初始化，下次运行: {profit_next}",
            extra={"task_id": task_id, "next_run": profit_next.isoformat()}
        )

    # 事件嗅探任务（每30分钟）
    event_sniffing_cron = "*/30 * * * *"  # 每30分钟
    event_sniffing_next = croniter(event_sniffing_cron, now).get_next(datetime)

    task_id = add_scheduled_task(
        name="event_sniffing",
        task_type="cron",
        schedule=event_sniffing_cron,
        enabled=True,
        metadata={
            "description": "事件嗅探任务 - 每30分钟获取并过滤优质事件",
            "auto_created": True,
            "huey_task": False  # 由动态调度器执行
        }
    )

    # 更新下次运行时间
    task = db.get_scheduled_task(task_id)
    if task and not task.next_run:
        task.next_run = event_sniffing_next
        db.update_scheduled_task(task)
        logger.info(
            "SCHEDULER.INIT.EVENT_SNIFFING",
            msg=f"事件嗅探任务已初始化，下次运行: {event_sniffing_next}",
            extra={"task_id": task_id, "next_run": event_sniffing_next.isoformat()}
        )

    logger.info(
        "SCHEDULER.INIT.SUCCESS",
        msg="预定义定时任务初始化完成"
    )

