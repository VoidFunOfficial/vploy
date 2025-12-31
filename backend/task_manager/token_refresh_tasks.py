"""
Token 自动刷新任务模块

使用 Huey 实现定期自动刷新 auth_token 和 access_token，
并支持手动触发刷新机制。
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from huey import crontab
from pathlib import Path

from .tasks import huey, logger
from ..sys_configs.token_refresher import get_token_refresher, TokenType
from ..vlogger import TraceContext


# ==================== 手动触发监控 ====================

class TokenExpirationMonitor:
    """
    Token 手动过期监控器

    监控 token_refresher.py 中的手动过期事件，
    当检测到手动过期时立即触发刷新任务
    """

    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_check_time = datetime.now()
        self.db_path = "backend/sys_configs/system_config.db"

    def start(self):
        """启动监控线程"""
        if self.running:
            logger.warn(
                "TOKEN.MONITOR.ALREADY_RUNNING",
                msg="Token 过期监控器已在运行中"
            )
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            name="TokenExpirationMonitor",
            daemon=True
        )
        self.thread.start()

        logger.info(
            "TOKEN.MONITOR.STARTED",
            msg="Token 过期监控器已启动"
        )

    def stop(self):
        """停止监控线程"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

        logger.info(
            "TOKEN.MONITOR.STOPPED",
            msg="Token 过期监控器已停止"
        )

    def _monitor_loop(self):
        """监控循环"""
        logger.info(
            "TOKEN.MONITOR.LOOP_START",
            msg="Token 过期监控循环已启动"
        )

        while self.running:
            try:
                # 检查是否有手动过期事件
                self._check_manual_expiration()

                # 每 10 秒检查一次
                time.sleep(10)

            except Exception as e:
                logger.error(
                    "TOKEN.MONITOR.LOOP_ERROR",
                    msg=f"监控循环发生错误: {str(e)}",
                    error_code="E-TOKEN-005",
                    extra={"exception": str(e)}
                )
                time.sleep(30)

    def _check_manual_expiration(self):
        """检查手动过期事件"""
        try:
            refresher = get_token_refresher()

            # 检查 auth_token 和 access_token 的状态
            auth_status = refresher.get_token_status(TokenType.AUTH_TOKEN.value)
            access_status = refresher.get_token_status(TokenType.ACCESS_TOKEN.value)

            # 检查是否有新的手动过期事件
            current_time = datetime.now()

            if auth_status and auth_status['is_expired']:
                expires_at = datetime.fromisoformat(auth_status['expires_at'])
                # 如果过期时间在最近 1 分钟内，认为是手动过期
                if expires_at > self.last_check_time and (current_time - expires_at).total_seconds() < 60:
                    logger.warn(
                        "TOKEN.MONITOR.MANUAL_EXPIRE_DETECTED",
                        msg="检测到 auth_token 手动过期，触发立即刷新",
                        extra={"token_type": "auth_token"}
                    )
                    # 触发立即刷新
                    trigger_immediate_refresh()

            if access_status and access_status['is_expired']:
                expires_at = datetime.fromisoformat(access_status['expires_at'])
                # 如果过期时间在最近 1 分钟内，认为是手动过期
                if expires_at > self.last_check_time and (current_time - expires_at).total_seconds() < 60:
                    logger.warn(
                        "TOKEN.MONITOR.MANUAL_EXPIRE_DETECTED",
                        msg="检测到 access_token 手动过期，触发立即刷新",
                        extra={"token_type": "access_token"}
                    )
                    # 触发立即刷新
                    trigger_immediate_refresh()

            self.last_check_time = current_time

        except Exception as e:
            logger.error(
                "TOKEN.MONITOR.CHECK_ERROR",
                msg=f"检查手动过期事件时发生错误: {str(e)}",
                error_code="E-TOKEN-006",
                extra={"exception": str(e)}
            )


# 全局监控器实例
_monitor: Optional[TokenExpirationMonitor] = None


def get_monitor() -> TokenExpirationMonitor:
    """获取全局监控器实例"""
    global _monitor
    if _monitor is None:
        _monitor = TokenExpirationMonitor()
    return _monitor


def start_token_monitor():
    """启动 Token 过期监控器"""
    monitor = get_monitor()
    monitor.start()


def stop_token_monitor():
    """停止 Token 过期监控器"""
    monitor = get_monitor()
    monitor.stop()


# ==================== 定期刷新任务 ====================

def refresh_access_token_scheduled():
    """
    定期刷新 access_token

    每 1 天执行一次，自动刷新 access_token 并更新到数据库
    """
    with TraceContext() as trace_id:
        logger.info(
            "TOKEN.REFRESH.ACCESS.START",
            msg="开始定期刷新 access_token",
            trace_id=trace_id
        )

        try:
            # 延迟导入，避免循环依赖
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from utils.auto_token_refresher import refresh_access_token

            # 执行刷新
            new_token = refresh_access_token()

            if new_token:
                # 更新到数据库
                refresher = get_token_refresher()
                success = refresher.update_token(
                    token_type=TokenType.ACCESS_TOKEN.value,
                    token_value=new_token
                )

                if success:
                    logger.info(
                        "TOKEN.REFRESH.ACCESS.SUCCESS",
                        msg="access_token 刷新成功",
                        extra={"token_length": len(new_token)},
                        trace_id=trace_id
                    )
                else:
                    logger.error(
                        "TOKEN.REFRESH.ACCESS.DB_ERROR",
                        msg="access_token 刷新成功但保存到数据库失败",
                        error_code="E-TOKEN-002",
                        trace_id=trace_id
                    )
            else:
                logger.error(
                    "TOKEN.REFRESH.ACCESS.FAILED",
                    msg="access_token 刷新失败",
                    error_code="E-TOKEN-003",
                    trace_id=trace_id
                )

        except Exception as e:
            logger.error(
                "TOKEN.REFRESH.ACCESS.EXCEPTION",
                msg=f"刷新 access_token 时发生异常: {str(e)}",
                error_code="E-TOKEN-004",
                extra={"exception": str(e)},
                trace_id=trace_id
            )


def refresh_auth_token_scheduled():
    """
    定期刷新 auth_token

    每 7 天执行一次，自动刷新 auth_token 并更新到数据库
    """
    with TraceContext() as trace_id:
        logger.info(
            "TOKEN.REFRESH.AUTH.START",
            msg="开始定期刷新 auth_token",
            trace_id=trace_id
        )

        try:
            # 延迟导入，避免循环依赖
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from utils.auto_token_refresher import refresh_auth_token

            # 执行刷新
            new_token = refresh_auth_token()

            if new_token:
                # 更新到数据库
                refresher = get_token_refresher()
                success = refresher.update_token(
                    token_type=TokenType.AUTH_TOKEN.value,
                    token_value=new_token
                )

                if success:
                    logger.info(
                        "TOKEN.REFRESH.AUTH.SUCCESS",
                        msg="auth_token 刷新成功",
                        extra={"token_length": len(new_token)},
                        trace_id=trace_id
                    )
                else:
                    logger.error(
                        "TOKEN.REFRESH.AUTH.DB_ERROR",
                        msg="auth_token 刷新成功但保存到数据库失败",
                        error_code="E-TOKEN-002",
                        trace_id=trace_id
                    )
            else:
                logger.error(
                    "TOKEN.REFRESH.AUTH.FAILED",
                    msg="auth_token 刷新失败",
                    error_code="E-TOKEN-003",
                    trace_id=trace_id
                )

        except Exception as e:
            logger.error(
                "TOKEN.REFRESH.AUTH.EXCEPTION",
                msg=f"刷新 auth_token 时发生异常: {str(e)}",
                error_code="E-TOKEN-004",
                extra={"exception": str(e)},
                trace_id=trace_id
            )


# ==================== 手动触发任务 ====================

@huey.task()
def refresh_both_tokens_immediate():
    """
    立即刷新两个 token

    当检测到手动过期事件时，立即刷新 auth_token 和 access_token
    """
    with TraceContext() as trace_id:
        logger.info(
            "TOKEN.REFRESH.IMMEDIATE.START",
            msg="开始立即刷新所有 token",
            trace_id=trace_id
        )

        success_count = 0

        # 刷新 auth_token
        try:
            # 延迟导入，避免循环依赖
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from utils.auto_token_refresher import refresh_auth_token

            auth_token = refresh_auth_token()
            if auth_token:
                refresher = get_token_refresher()
                if refresher.update_token(
                    token_type=TokenType.AUTH_TOKEN.value,
                    token_value=auth_token
                ):
                    success_count += 1
                    logger.info(
                        "TOKEN.REFRESH.IMMEDIATE.AUTH_SUCCESS",
                        msg="立即刷新 auth_token 成功",
                        trace_id=trace_id
                    )
            else:
                logger.error(
                    "TOKEN.REFRESH.IMMEDIATE.AUTH_FAILED",
                    msg="立即刷新 auth_token 失败",
                    error_code="E-TOKEN-007",
                    trace_id=trace_id
                )
        except Exception as e:
            logger.error(
                "TOKEN.REFRESH.IMMEDIATE.AUTH_EXCEPTION",
                msg=f"立即刷新 auth_token 时发生异常: {str(e)}",
                error_code="E-TOKEN-008",
                extra={"exception": str(e)},
                trace_id=trace_id
            )

        # 刷新 access_token
        try:
            # 延迟导入，避免循环依赖
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from utils.auto_token_refresher import refresh_access_token

            access_token = refresh_access_token()
            if access_token:
                refresher = get_token_refresher()
                if refresher.update_token(
                    token_type=TokenType.ACCESS_TOKEN.value,
                    token_value=access_token
                ):
                    success_count += 1
                    logger.info(
                        "TOKEN.REFRESH.IMMEDIATE.ACCESS_SUCCESS",
                        msg="立即刷新 access_token 成功",
                        trace_id=trace_id
                    )
            else:
                logger.error(
                    "TOKEN.REFRESH.IMMEDIATE.ACCESS_FAILED",
                    msg="立即刷新 access_token 失败",
                    error_code="E-TOKEN-007",
                    trace_id=trace_id
                )
        except Exception as e:
            logger.error(
                "TOKEN.REFRESH.IMMEDIATE.ACCESS_EXCEPTION",
                msg=f"立即刷新 access_token 时发生异常: {str(e)}",
                error_code="E-TOKEN-008",
                extra={"exception": str(e)},
                trace_id=trace_id
            )

        logger.info(
            "TOKEN.REFRESH.IMMEDIATE.COMPLETE",
            msg=f"立即刷新完成，成功刷新 {success_count}/2 个 token",
            extra={"success_count": success_count},
            trace_id=trace_id
        )


def trigger_immediate_refresh():
    """
    触发立即刷新任务

    将刷新任务提交到 Huey 队列立即执行
    """
    logger.info(
        "TOKEN.REFRESH.TRIGGER",
        msg="触发立即刷新任务"
    )

    # 提交到 Huey 队列
    refresh_both_tokens_immediate()


# ==================== 初始化函数 ====================

def init_token_refresh_tasks():
    """
    初始化 Token 刷新任务系统

    在应用启动时调用，启动监控器
    """
    logger.info(
        "TOKEN.REFRESH.INIT.START",
        msg="初始化 Token 刷新任务系统"
    )

    try:
        # 启动监控器
        start_token_monitor()

        logger.info(
            "TOKEN.REFRESH.INIT.SUCCESS",
            msg="Token 刷新任务系统初始化完成"
        )

    except Exception as e:
        logger.error(
            "TOKEN.REFRESH.INIT.FAILED",
            msg=f"Token 刷新任务系统初始化失败: {str(e)}",
            error_code="E-TOKEN-009",
            extra={"exception": str(e)}
        )
        raise

