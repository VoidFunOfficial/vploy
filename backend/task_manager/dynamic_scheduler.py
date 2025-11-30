"""
动态定时任务调度器

支持运行时动态修改定时任务的调度配置，无需重启服务。
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional
from croniter import croniter

from .models import TaskDatabase, ScheduledTask
from .health_check import check_all_nodes, get_health_report, get_db as get_health_db
from .email_report import generate_health_report_html, generate_plain_text_report
from ..vlogger.email_helper import email_send_with_db_config
from ..vlogger import get_logger, TraceContext


logger = get_logger("dynamic_scheduler")


class DynamicScheduler:
    """
    动态定时任务调度器
    
    支持运行时动态修改任务调度配置，无需重启服务。
    """
    
    def __init__(self, check_interval: int = 60):
        """
        初始化调度器
        
        参数:
            check_interval: 检查间隔（秒），默认60秒
        """
        self.check_interval = check_interval
        self.db = TaskDatabase()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # 注册任务执行函数
        self.task_executors: Dict[str, Callable] = {
            'health_check_email': self._execute_health_check_email,
            'health_report': self._execute_health_report,
            'profit_email': self._execute_profit_email,
            'periodic_health_check': self._execute_periodic_health_check,
        }
        
        logger.info(
            "DYNAMIC_SCHEDULER.INIT",
            msg="动态调度器初始化完成",
            extra={"check_interval": check_interval}
        )
    
    def _execute_health_check_email(self, task: ScheduledTask):
        """执行健康检查邮件任务"""
        with TraceContext() as trace_id:
            logger.info(
                "DYNAMIC_SCHEDULER.HEALTH_CHECK_EMAIL.START",
                msg="开始执行健康检查邮件任务",
                trace_id=trace_id
            )
            
            try:
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
                        "DYNAMIC_SCHEDULER.HEALTH_CHECK_EMAIL.SUCCESS",
                        msg="健康检查邮件任务执行成功",
                        trace_id=trace_id
                    )
                else:
                    logger.error(
                        "DYNAMIC_SCHEDULER.HEALTH_CHECK_EMAIL.FAILED",
                        msg="健康检查邮件发送失败",
                        error_code="E-DYNAMIC-SCHEDULER-001",
                        trace_id=trace_id
                    )
                    
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.HEALTH_CHECK_EMAIL.ERROR",
                    msg="健康检查邮件任务执行失败",
                    error_code="E-DYNAMIC-SCHEDULER-002",
                    extra={"error": str(e)},
                    trace_id=trace_id
                )
    
    def _execute_health_report(self, task: ScheduledTask):
        """执行健康报告任务"""
        with TraceContext() as trace_id:
            logger.info(
                "DYNAMIC_SCHEDULER.HEALTH_REPORT.START",
                msg="开始执行健康报告任务",
                trace_id=trace_id
            )
            
            try:
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
                        "DYNAMIC_SCHEDULER.HEALTH_REPORT.SUCCESS",
                        msg="健康报告任务执行成功",
                        trace_id=trace_id
                    )
                else:
                    logger.error(
                        "DYNAMIC_SCHEDULER.HEALTH_REPORT.FAILED",
                        msg="健康报告邮件发送失败",
                        error_code="E-DYNAMIC-SCHEDULER-003",
                        trace_id=trace_id
                    )
                    
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.HEALTH_REPORT.ERROR",
                    msg="健康报告任务执行失败",
                    error_code="E-DYNAMIC-SCHEDULER-004",
                    extra={"error": str(e)},
                    trace_id=trace_id
                )
    
    def _execute_profit_email(self, task: ScheduledTask):
        """执行收益报告邮件任务"""
        logger.info(
            "DYNAMIC_SCHEDULER.PROFIT_EMAIL.START",
            msg="开始执行收益报告邮件任务"
        )
        
        try:
            # TODO: 实现收益报告逻辑
            logger.info(
                "DYNAMIC_SCHEDULER.PROFIT_EMAIL.SUCCESS",
                msg="收益报告邮件任务执行成功（占位符）"
            )
            
        except Exception as e:
            logger.error(
                "DYNAMIC_SCHEDULER.PROFIT_EMAIL.ERROR",
                msg="收益报告邮件任务执行失败",
                error_code="E-DYNAMIC-SCHEDULER-005",
                extra={"error": str(e)}
            )
    
    def _execute_periodic_health_check(self, task: ScheduledTask):
        """执行定期健康检查任务"""
        with TraceContext() as trace_id:
            logger.info(
                "DYNAMIC_SCHEDULER.PERIODIC_CHECK.START",
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
                    "DYNAMIC_SCHEDULER.PERIODIC_CHECK.SUCCESS",
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
                    "DYNAMIC_SCHEDULER.PERIODIC_CHECK.ERROR",
                    msg="定时健康检查执行失败",
                    error_code="E-DYNAMIC-SCHEDULER-006",
                    extra={"error": str(e)},
                    trace_id=trace_id
                )
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """
        计算下次运行时间
        
        参数:
            task: 定时任务
            
        返回:
            datetime: 下次运行时间
        """
        now = datetime.now()
        
        if task.task_type == 'cron':
            # Cron表达式
            try:
                cron = croniter(task.schedule, now)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.CALC_NEXT_RUN.CRON_ERROR",
                    msg=f"解析Cron表达式失败: {task.schedule}",
                    error_code="E-DYNAMIC-SCHEDULER-007",
                    extra={"task_name": task.name, "error": str(e)}
                )
                # 默认1小时后
                return now + timedelta(hours=1)
        else:
            # 间隔时间（秒）
            try:
                interval_seconds = int(task.schedule)
                return now + timedelta(seconds=interval_seconds)
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.CALC_NEXT_RUN.INTERVAL_ERROR",
                    msg=f"解析间隔时间失败: {task.schedule}",
                    error_code="E-DYNAMIC-SCHEDULER-008",
                    extra={"task_name": task.name, "error": str(e)}
                )
                # 默认1小时后
                return now + timedelta(hours=1)

    def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        now = datetime.now()

        # 获取所有启用的任务
        tasks = self.db.get_all_scheduled_tasks(enabled_only=True)

        for task in tasks:
            # 检查是否需要执行
            if task.next_run is None or task.next_run <= now:
                # 执行任务
                self._execute_task(task)

                # 更新运行时间
                task.last_run = now
                task.next_run = self._calculate_next_run(task)
                self.db.update_scheduled_task(task)

                logger.info(
                    "DYNAMIC_SCHEDULER.TASK_EXECUTED",
                    msg=f"任务执行完成: {task.name}",
                    extra={
                        "task_name": task.name,
                        "last_run": task.last_run.isoformat(),
                        "next_run": task.next_run.isoformat()
                    }
                )

    def _execute_task(self, task: ScheduledTask):
        """
        执行任务

        参数:
            task: 定时任务
        """
        executor = self.task_executors.get(task.name)

        if executor:
            try:
                executor(task)
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.EXECUTE_ERROR",
                    msg=f"任务执行失败: {task.name}",
                    error_code="E-DYNAMIC-SCHEDULER-009",
                    extra={"task_name": task.name, "error": str(e)}
                )
        else:
            logger.warn(
                "DYNAMIC_SCHEDULER.EXECUTOR_NOT_FOUND",
                msg=f"未找到任务执行函数: {task.name}",
                extra={"task_name": task.name}
            )

    def _run(self):
        """调度器主循环"""
        logger.info(
            "DYNAMIC_SCHEDULER.START",
            msg="动态调度器启动"
        )

        while self.running:
            try:
                self._check_and_execute_tasks()
            except Exception as e:
                logger.error(
                    "DYNAMIC_SCHEDULER.RUN_ERROR",
                    msg="调度器执行出错",
                    error_code="E-DYNAMIC-SCHEDULER-010",
                    extra={"error": str(e)}
                )

            # 等待下一次检查
            time.sleep(self.check_interval)

        logger.info(
            "DYNAMIC_SCHEDULER.STOP",
            msg="动态调度器停止"
        )

    def start(self):
        """启动调度器"""
        if self.running:
            logger.warn(
                "DYNAMIC_SCHEDULER.ALREADY_RUNNING",
                msg="调度器已在运行中"
            )
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        logger.info(
            "DYNAMIC_SCHEDULER.STARTED",
            msg="动态调度器已启动"
        )

    def stop(self):
        """停止调度器"""
        if not self.running:
            logger.warn(
                "DYNAMIC_SCHEDULER.NOT_RUNNING",
                msg="调度器未在运行"
            )
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

        logger.info(
            "DYNAMIC_SCHEDULER.STOPPED",
            msg="动态调度器已停止"
        )

    def register_executor(self, task_name: str, executor: Callable):
        """
        注册任务执行函数

        参数:
            task_name: 任务名称
            executor: 执行函数
        """
        self.task_executors[task_name] = executor
        logger.info(
            "DYNAMIC_SCHEDULER.EXECUTOR_REGISTERED",
            msg=f"注册任务执行函数: {task_name}"
        )


# 全局调度器实例
_scheduler: Optional[DynamicScheduler] = None


def get_scheduler() -> DynamicScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DynamicScheduler()
    return _scheduler


def start_dynamic_scheduler():
    """启动动态调度器"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_dynamic_scheduler():
    """停止动态调度器"""
    scheduler = get_scheduler()
    scheduler.stop()

