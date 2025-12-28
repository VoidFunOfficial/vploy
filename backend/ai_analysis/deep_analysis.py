"""
深度分析模块 - 基于Huey的异步分析任务管理系统

基于 Huey 任务队列和 GPT API 实现的异步分析任务管理系统，支持：
- Huey异步任务队列集成
- 任务状态追踪和查询
- 结果获取和验证
- 错误处理和重试
- VLogger 日志集成
- AI 自动从 event_summary 中解析 market_id

使用示例:
    >>> from backend.ai_analysis.deep_analysis import AnalysisTaskManager
    >>> from backend.task_manager.models import AsyncTask, TaskStage, TaskStatus
    >>>
    >>> # 创建AsyncTask
    >>> task = AsyncTask(
    >>>     stage=TaskStage.ANALYSIS,
    >>>     status=TaskStatus.PROCESSING,
    >>>     metadata={"event_id": "event_123"}
    >>> )
    >>>
    >>> # 提交分析任务
    >>> manager = AnalysisTaskManager()
    >>> success = manager.submit_analysis(task.id, event_summary_text)
    >>>
    >>> # 查询任务状态
    >>> status = manager.get_analysis_status(task.id)
    >>>
    >>> # 获取分析结果
    >>> result = manager.get_analysis_result(task.id)
    >>> # 结果格式：{"68095": {"p": 0.6, "a": 0.3, ...}, "68096": {"p": 0.7, "a": 0.2, ...}}
"""

from typing import Dict, Any, Optional

# 导入任务管理模块
from ..task_manager.models import TaskDatabase, AsyncTask
from .analysis_tasks import (
    submit_analysis_task,
    retry_analysis_task,
    submit_info_sniff_task,
    retry_info_sniff_task,
    AnalysisStatus
)

# 导入全局 VLogger 实例
from ..sys_configs.global_event_reg import vlogger


# ==================== 初始化 ====================

# 初始化数据库
db = TaskDatabase()

# 初始化日志系统
logger = vlogger


# ==================== 分析任务管理器 ====================

class AnalysisTaskManager:
    """
    分析任务管理器（基于Huey）

    功能:
        - 提交分析任务到Huey队列
        - 查询任务状态和结果
        - 重试失败的任务
        - 日志记录
    """

    def __init__(self):
        """初始化任务管理器"""
        self.db = db
        self.logger = logger

        self.logger.info("ANALYSIS.MANAGER.INIT", msg="分析任务管理器初始化完成")

    def submit_analysis(
        self,
        async_task_id: int,
        event_summary: str,
        initial_delay: int = 300,
        polling_interval: int = 60,
        max_timeout: int = 3600
    ) -> bool:
        """
        提交分析任务到Huey队列

        参数:
            async_task_id: AsyncTask的ID
            event_summary: 事件摘要文本
            initial_delay: 首次轮询延迟（秒）
            polling_interval: 轮询间隔（秒）
            max_timeout: 最大超时时间（秒）

        返回:
            bool: 是否成功提交
        """
        try:
            success = submit_analysis_task(
                async_task_id=async_task_id,
                event_summary=event_summary,
                initial_delay=initial_delay,
                polling_interval=polling_interval,
                max_timeout=max_timeout
            )

            if success:
                self.logger.info(
                    "ANALYSIS.MANAGER.SUBMIT",
                    msg="提交分析任务成功",
                    extra={"async_task_id": async_task_id}
                )
            else:
                self.logger.error(
                    "ANALYSIS.MANAGER.SUBMIT_FAILED",
                    msg="提交分析任务失败",
                    error_code="E-MANAGER-001",
                    extra={"async_task_id": async_task_id}
                )

            return success

        except Exception as e:
            self.logger.error(
                "ANALYSIS.MANAGER.SUBMIT_EXCEPTION",
                msg=f"提交分析任务异常: {str(e)}",
                error_code="E-MANAGER-002",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return False

    def retry_analysis(self, async_task_id: int) -> bool:
        """
        重试失败的分析任务

        参数:
            async_task_id: AsyncTask的ID

        返回:
            bool: 是否成功重试
        """
        try:
            success = retry_analysis_task(async_task_id)

            if success:
                self.logger.info(
                    "ANALYSIS.MANAGER.RETRY",
                    msg="重试分析任务成功",
                    extra={"async_task_id": async_task_id}
                )
            else:
                self.logger.error(
                    "ANALYSIS.MANAGER.RETRY_FAILED",
                    msg="重试分析任务失败",
                    error_code="E-MANAGER-003",
                    extra={"async_task_id": async_task_id}
                )

            return success

        except Exception as e:
            self.logger.error(
                "ANALYSIS.MANAGER.RETRY_EXCEPTION",
                msg=f"重试分析任务异常: {str(e)}",
                error_code="E-MANAGER-004",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return False

    def get_analysis_status(self, async_task_id: int) -> Optional[str]:
        """
        获取分析任务状态

        参数:
            async_task_id: AsyncTask的ID

        返回:
            Optional[str]: 分析状态（AnalysisStatus枚举值），如果任务不存在则返回None
        """
        try:
            task = self.db.get_async_task(async_task_id)
            if not task:
                return None

            return task.result.get("analysis_status")

        except Exception as e:
            self.logger.error(
                "ANALYSIS.MANAGER.GET_STATUS_EXCEPTION",
                msg=f"获取分析状态异常: {str(e)}",
                error_code="E-MANAGER-005",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return None

    def get_analysis_result(self, async_task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取分析结果

        参数:
            async_task_id: AsyncTask的ID

        返回:
            Optional[Dict[str, Any]]: 分析结果JSON，如果任务不存在或未完成则返回None
        """
        try:
            task = self.db.get_async_task(async_task_id)
            if not task:
                return None

            return task.result.get("analysis_result")

        except Exception as e:
            self.logger.error(
                "ANALYSIS.MANAGER.GET_RESULT_EXCEPTION",
                msg=f"获取分析结果异常: {str(e)}",
                error_code="E-MANAGER-006",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return None

    def get_task_info(self, async_task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务完整信息

        参数:
            async_task_id: AsyncTask的ID

        返回:
            Optional[Dict[str, Any]]: 任务信息字典
        """
        try:
            task = self.db.get_async_task(async_task_id)
            if not task:
                return None

            return {
                "task_id": task.id,
                "stage": task.stage.value,
                "status": task.status.value,
                "analysis_status": task.result.get("analysis_status"),
                "conversation_id": task.result.get("conversation_id"),
                "analysis_result": task.result.get("analysis_result"),
                "market_ids": task.result.get("market_ids", []),
                "error": task.error_msg or task.result.get("error"),
                "metadata": task.metadata,
                "create_time": task.create_time.isoformat() if task.create_time else None,
                "update_time": task.update_time.isoformat() if task.update_time else None
            }

        except Exception as e:
            self.logger.error(
                "ANALYSIS.MANAGER.GET_INFO_EXCEPTION",
                msg=f"获取任务信息异常: {str(e)}",
                error_code="E-MANAGER-007",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return None

    def submit_info_sniff(
        self,
        async_task_id: int,
        event_summary: str,
        initial_delay: int = 30,
        polling_interval: int = 20,
        max_timeout: int = 1800
    ) -> bool:
        """
        提交Info Sniff任务到Huey队列

        参数:
            async_task_id: AsyncTask的ID
            event_summary: 事件摘要文本
            initial_delay: 首次轮询延迟（秒，默认30秒）
            polling_interval: 轮询间隔（秒，默认20秒）
            max_timeout: 最大超时时间（秒，默认1800秒=30分钟）

        返回:
            bool: 是否成功提交
        """
        try:
            success = submit_info_sniff_task(
                async_task_id=async_task_id,
                event_summary=event_summary,
                initial_delay=initial_delay,
                polling_interval=polling_interval,
                max_timeout=max_timeout
            )

            if success:
                self.logger.info(
                    "INFO_SNIFF.MANAGER.SUBMIT",
                    msg="提交Info Sniff任务成功",
                    extra={"async_task_id": async_task_id}
                )
            else:
                self.logger.error(
                    "INFO_SNIFF.MANAGER.SUBMIT_FAILED",
                    msg="提交Info Sniff任务失败",
                    error_code="E-MANAGER-SNIFF-001",
                    extra={"async_task_id": async_task_id}
                )

            return success

        except Exception as e:
            self.logger.error(
                "INFO_SNIFF.MANAGER.SUBMIT_EXCEPTION",
                msg=f"提交Info Sniff任务异常: {str(e)}",
                error_code="E-MANAGER-SNIFF-002",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return False

    def retry_info_sniff(self, async_task_id: int) -> bool:
        """
        重试失败的Info Sniff任务

        参数:
            async_task_id: AsyncTask的ID

        返回:
            bool: 是否成功重试
        """
        try:
            success = retry_info_sniff_task(async_task_id)

            if success:
                self.logger.info(
                    "INFO_SNIFF.MANAGER.RETRY",
                    msg="重试Info Sniff任务成功",
                    extra={"async_task_id": async_task_id}
                )
            else:
                self.logger.error(
                    "INFO_SNIFF.MANAGER.RETRY_FAILED",
                    msg="重试Info Sniff任务失败",
                    error_code="E-MANAGER-SNIFF-003",
                    extra={"async_task_id": async_task_id}
                )

            return success

        except Exception as e:
            self.logger.error(
                "INFO_SNIFF.MANAGER.RETRY_EXCEPTION",
                msg=f"重试Info Sniff任务异常: {str(e)}",
                error_code="E-MANAGER-SNIFF-004",
                extra={"async_task_id": async_task_id, "exception": str(e)}
            )
            return False


