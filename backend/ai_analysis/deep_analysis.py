"""
深度分析模块 - 简化版异步分析任务管理系统

基于 GPT API 实现的异步分析任务管理系统，支持：
- 任务队列管理
- 异步任务提交和轮询
- 任务状态追踪
- 超时和错误处理
- VLogger 日志集成
- AI 自动从 event_summary 中解析 market_id

使用示例:
    >>> from backend.ai_analysis.deep_analysis import AnalysisTaskManager
    >>>
    >>> # 创建任务管理器
    >>> manager = AnalysisTaskManager(cookie_string="your_cookie_string")
    >>>
    >>> # 提交分析任务（传入事件摘要字符串，AI 会自动解析 market_id）
    >>> task_id = await manager.submit_analysis_task(event_summary_text)
    >>>
    >>> # 等待任务完成
    >>> result = await manager.wait_for_task_completion(task_id)
    >>>
    >>> # 结果格式：{"68095": {"p": 0.6, "a": 0.3, ...}, "68096": {"p": 0.7, "a": 0.2, ...}}
"""

import asyncio
import uuid
import time
import json
import re
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 GPT API 客户端
from ai_analysis.gpt_api import send_request, process_result, get_result, parse_cookie_string

# 导入全局 VLogger 实例
from backend.sys_configs.global_event_reg import vlogger
from backend.vlogger import LogLevel


# ==================== JSON 结构验证 ====================

def validate_analysis_result(result_text: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    验证分析结果是否符合预期的 JSON 结构

    预期结构（AI 自动从 event_summary 中解析 market_id）:
    {
        "68095": {
            "p": 0.3,
            "a": 0.5,
            "reasons_p": ["..."],
            "reasons_n": ["..."]
        },
        "68096": {
            "p": 0.7,
            "a": 0.2,
            "reasons_p": ["..."],
            "reasons_n": ["..."]
        }
    }

    参数:
        result_text: GPT 返回的文本结果

    返回:
        tuple[bool, Optional[Dict]]: (是否有效, 解析后的 JSON 对象)
    """
    if not result_text or not result_text.strip():
        return False, None

    try:
        # 尝试提取 JSON 内容（可能被包裹在 markdown 代码块中）
        json_text = result_text.strip()

        # 移除可能的 markdown 代码块标记
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        elif json_text.startswith("```"):
            json_text = json_text[3:]

        if json_text.endswith("```"):
            json_text = json_text[:-3]

        json_text = json_text.strip()

        # 解析 JSON
        data = json.loads(json_text)

        # 验证结构
        if not isinstance(data, dict):
            return False, None

        # 检查是否至少有一个市场数据
        if len(data) == 0:
            return False, None

        # 验证每个市场的结构
        for market_id, market_data in data.items():
            # 检查必需字段
            if not isinstance(market_data, dict):
                return False, None

            required_fields = ["p", "a", "reasons_p", "reasons_n"]
            for field in required_fields:
                if field not in market_data:
                    return False, None

            # 验证字段类型
            if not isinstance(market_data["p"], (int, float)):
                return False, None

            if not isinstance(market_data["a"], (int, float)):
                return False, None

            if not isinstance(market_data["reasons_p"], list):
                return False, None

            if not isinstance(market_data["reasons_n"], list):
                return False, None

            # 验证概率值范围 (0-1)
            if not (0 <= market_data["p"] <= 1):
                return False, None

            if not (0 <= market_data["a"] <= 1):
                return False, None

        return True, data

    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        return False, None


# ==================== 任务状态枚举 ====================

class TaskStatus(str, Enum):
    """
    任务状态枚举

    状态流转:
        PENDING -> PROCESSING -> SUCCESS
                             -> FAILED
                             -> TIMEOUT
    """
    PENDING = "PENDING"           # 待处理：任务已提交，等待首次轮询
    PROCESSING = "PROCESSING"     # 处理中：正在轮询任务状态
    SUCCESS = "SUCCESS"           # 成功：任务已完成
    FAILED = "FAILED"             # 失败：任务执行失败
    TIMEOUT = "TIMEOUT"           # 超时：任务执行超时


# ==================== 任务数据结构 ====================

@dataclass
class AnalysisTask:
    """
    分析任务数据结构

    属性:
        task_id: 任务唯一标识符
        event_summary: 事件摘要文本（已经过 event_summary_readableforai 处理）
        conversation_id: GPT API 返回的对话 ID
        status: 任务状态
        result: 分析结果（成功时填充）
        result_json: 解析后的 JSON 结果（AI 自动解析的多个市场数据）
        error: 错误信息（失败时填充）
        created_at: 任务创建时间
        updated_at: 任务更新时间
        retry_count: 重试次数
        validation_retry_count: 验证失败重试次数
        metadata: 额外元数据
    """
    task_id: str
    event_summary: str
    conversation_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    result_json: Optional[Dict[str, Any]] = None  # 格式: {"market_id": {"p": ..., "a": ..., ...}, ...}
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    retry_count: int = 0
    validation_retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_status(self, status: TaskStatus, error: Optional[str] = None):
        """
        更新任务状态

        参数:
            status: 新状态
            error: 错误信息（可选）
        """
        self.status = status
        self.updated_at = time.time()
        if error:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "conversation_id": self.conversation_id,
            "status": self.status.value,
            "result": self.result,
            "result_json": self.result_json,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "retry_count": self.retry_count,
            "validation_retry_count": self.validation_retry_count,
            "metadata": self.metadata,
            "market_ids": list(self.result_json.keys()) if self.result_json else []
        }


# ==================== 异步任务管理器 ====================

class AnalysisTaskManager:
    """
    异步分析任务管理器

    功能:
        - 管理多个并发的分析任务
        - 自动轮询任务状态
        - 超时和错误处理
        - 日志记录
    """

    def __init__(
        self,
        cookie_string: str,
        initial_delay: int = 300,          # 首次轮询延迟（秒），默认 5 分钟
        polling_interval: int = 60,        # 轮询间隔（秒），默认 1 分钟
        max_timeout: int = 3600,           # 最大超时时间（秒），默认 1 小时
        max_retries: int = 3,              # 最大重试次数
        max_validation_retries: int = 3,   # 最大验证失败重试次数
        max_concurrent_tasks: int = 10     # 最大并发任务数
    ):
        """
        初始化任务管理器

        参数:
            cookie_string: GPT API 的 Cookie 字符串
            initial_delay: 首次轮询延迟（秒）
            polling_interval: 轮询间隔（秒）
            max_timeout: 最大超时时间（秒）
            max_retries: 最大重试次数
            max_validation_retries: 最大验证失败重试次数
            max_concurrent_tasks: 最大并发任务数
        """
        self.cookie_string = cookie_string
        self.cookies_dict = parse_cookie_string(cookie_string)
        self.initial_delay = initial_delay
        self.polling_interval = polling_interval
        self.max_timeout = max_timeout
        self.max_retries = max_retries
        self.max_validation_retries = max_validation_retries
        self.max_concurrent_tasks = max_concurrent_tasks

        # 任务队列和存储
        self.tasks: Dict[str, AnalysisTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: int = 0

        # 加载分析提示词
        prompt_path = os.path.join(os.path.dirname(__file__), 'analysis.md')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_analysis = f.read()
        except FileNotFoundError:
            logger.error(f"提示词文件未找到: {prompt_path}")
            raise

        # 初始化日志系统
        self.logger = vlogger
        self.logger.info("ANALYSIS.INIT", msg="分析任务管理器初始化完成", extra={
            "initial_delay": initial_delay,
            "polling_interval": polling_interval,
            "max_timeout": max_timeout,
            "max_retries": max_retries,
            "max_validation_retries": max_validation_retries,
            "max_concurrent_tasks": max_concurrent_tasks
        })

    def update_cookie(self, cookie_string: str):
        """更新 GPT API 的 Cookie 字符串"""
        self.cookie_string = cookie_string
        self.cookies_dict = parse_cookie_string(cookie_string)

    def generate_task_id(self) -> str:
        """生成唯一的任务 ID"""
        return f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


    async def submit_analysis_task(
        self,
        event_summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交分析任务

        参数:
            event_summary: 事件摘要文本（已经过 event_summary_readableforai 处理）
                          AI 会自动从中解析出所有市场的 ID
            metadata: 额外元数据（可选）

        返回:
            str: 任务 ID
        """
        # 生成任务 ID
        task_id = self.generate_task_id()

        # 创建任务对象
        task = AnalysisTask(
            task_id=task_id,
            event_summary=event_summary,
            metadata=metadata or {}
        )

        # 存储任务
        self.tasks[task_id] = task

        # 添加到队列
        await self.task_queue.put(task_id)

        self.logger.info("ANALYSIS.TASK.SUBMIT", msg="提交分析任务", extra={
            "task_id": task_id,
            "queue_size": self.task_queue.qsize()
        })

        return task_id

    async def _send_gpt_request(self, task: AnalysisTask) -> bool:
        """
        发送 GPT 分析请求

        参数:
            task: 任务对象

        返回:
            bool: 是否成功发送请求
        """
        try:
            # 构建提示词（直接使用传入的事件摘要）
            prompt = f"{self.prompt_analysis}\n\n请对以下事件进行深度分析：\n\n{task.event_summary}"

            self.logger.info("ANALYSIS.GPT.REQUEST", msg="发送 GPT 分析请求", extra={
                "task_id": task.task_id,
                "prompt_length": len(prompt)
            })

            # 发送请求（同步调用，在异步环境中运行）
            result = await asyncio.to_thread(
                send_request,
                prompt=prompt,
                cookies=self.cookies_dict,
                model="gpt-5-1"
            )

            # 检查请求结果
            if result.get("success"):
                # 提取 conversation_id
                conversation_id = process_result(result)
                task.conversation_id = conversation_id
                task.update_status(TaskStatus.PROCESSING)

                self.logger.info("ANALYSIS.GPT.SUCCESS", msg="GPT 请求成功", extra={
                    "task_id": task.task_id,
                    "conversation_id": conversation_id
                })

                return True
            else:
                # 请求失败
                error_msg = result.get("error", "未知错误")
                task.update_status(TaskStatus.FAILED, error=f"GPT 请求失败: {error_msg}")

                self.logger.error("ANALYSIS.GPT.FAILED", msg="GPT 请求失败",
                                error_code="E-ANALYSIS-001", extra={
                    "task_id": task.task_id,
                    "error": error_msg,
                    "status_code": result.get("status_code"),
                    "response_text": result.get("response_text", "")[:200]
                })

                return False

        except Exception as e:
            task.update_status(TaskStatus.FAILED, error=f"发送请求异常: {str(e)}")

            self.logger.error("ANALYSIS.GPT.EXCEPTION", msg="发送 GPT 请求异常",
                            error_code="E-ANALYSIS-002", extra={
                "task_id": task.task_id,
                "exception": str(e)
            })

            return False

    async def _poll_task_status(self, task: AnalysisTask) -> bool:
        """
        轮询任务状态

        参数:
            task: 任务对象

        返回:
            bool: 任务是否完成（成功或失败）
        """
        if not task.conversation_id:
            task.update_status(TaskStatus.FAILED, error="缺少 conversation_id")
            return True

        try:
            self.logger.debug("ANALYSIS.POLL.START", msg="开始轮询任务状态", extra={
                "task_id": task.task_id,
                "conversation_id": task.conversation_id,
                "retry_count": task.retry_count
            })

            # 查询结果（同步调用，在异步环境中运行）
            result = await asyncio.to_thread(
                get_result,
                conversation_id=task.conversation_id,
                cookies=self.cookies_dict
            )

            # 检查结果
            if result.get("success"):
                # 任务成功完成，验证结果格式
                ai_response = result.get("ai_response", "")
                task.result = ai_response

                # 验证 JSON 结构（AI 自动解析 market_id）
                is_valid, parsed_json = validate_analysis_result(ai_response)

                if is_valid:
                    # 结果格式正确
                    task.result_json = parsed_json
                    task.update_status(TaskStatus.SUCCESS)

                    self.logger.info("ANALYSIS.POLL.SUCCESS", msg="任务完成，结果验证通过", extra={
                        "task_id": task.task_id,
                        "conversation_id": task.conversation_id,
                        "result_length": len(ai_response),
                        "market_count": len(parsed_json.keys()),
                        "market_ids": list(parsed_json.keys()),
                        "elapsed_time": time.time() - task.created_at
                    })

                    return True
                else:
                    # 结果格式不正确，检查是否需要重试
                    task.validation_retry_count += 1

                    if task.validation_retry_count >= self.max_validation_retries:
                        # 超过最大重试次数，标记为失败
                        task.update_status(TaskStatus.FAILED,
                                         error=f"结果验证失败（已重试 {task.validation_retry_count} 次）：返回的结果不符合预期的 JSON 结构")

                        self.logger.error("ANALYSIS.VALIDATION.FAILED", msg="结果验证失败，超过最大重试次数",
                                        error_code="E-ANALYSIS-010", extra={
                                "task_id": task.task_id,
                                "conversation_id": task.conversation_id,
                                "validation_retry_count": task.validation_retry_count,
                                "result_preview": ai_response[:200]
                            })

                        return True
                    else:
                        # 需要重新请求
                        self.logger.warn("ANALYSIS.VALIDATION.RETRY", msg="结果验证失败，将重新请求", extra={
                            "task_id": task.task_id,
                            "conversation_id": task.conversation_id,
                            "validation_retry_count": task.validation_retry_count,
                            "max_validation_retries": self.max_validation_retries,
                            "result_preview": ai_response[:200]
                        })

                        # 重置状态，准备重新发送请求
                        task.conversation_id = None
                        task.update_status(TaskStatus.PENDING)

                        # 重新发送请求
                        success = await self._send_gpt_request(task)
                        if not success:
                            return True  # 发送失败，任务结束

                        # 等待初始延迟后继续轮询
                        await asyncio.sleep(self.initial_delay)
                        return False  # 继续轮询新的请求

            elif result.get("error") == "AI is thinking":
                # AI 仍在思考，继续轮询
                self.logger.debug("ANALYSIS.POLL.THINKING", msg="AI 仍在思考", extra={
                    "task_id": task.task_id,
                    "elapsed_time": time.time() - task.created_at
                })

                return False

            else:
                # 查询失败
                error_msg = result.get("error", "未知错误")
                task.retry_count += 1

                if task.retry_count >= self.max_retries:
                    task.update_status(TaskStatus.FAILED, error=f"查询失败（已重试 {task.retry_count} 次）: {error_msg}")

                    self.logger.error("ANALYSIS.POLL.FAILED", msg="任务查询失败",
                                        error_code="E-ANALYSIS-003", extra={
                            "task_id": task.task_id,
                            "error": error_msg,
                            "retry_count": task.retry_count
                        })

                    return True
                else:
                    self.logger.warn("ANALYSIS.POLL.RETRY", msg="查询失败，将重试", extra={
                        "task_id": task.task_id,
                        "error": error_msg,
                        "retry_count": task.retry_count,
                        "max_retries": self.max_retries
                    })

                    return False

        except Exception as e:
            task.retry_count += 1

            if task.retry_count >= self.max_retries:
                task.update_status(TaskStatus.FAILED, error=f"轮询异常（已重试 {task.retry_count} 次）: {str(e)}")

                self.logger.error("ANALYSIS.POLL.EXCEPTION", msg="轮询任务状态异常",
                                error_code="E-ANALYSIS-004", extra={
                        "task_id": task.task_id,
                        "exception": str(e),
                        "retry_count": task.retry_count
                    })

                return True
            else:
                self.logger.warn("ANALYSIS.POLL.EXCEPTION_RETRY", msg="轮询异常，将重试", extra={
                    "task_id": task.task_id,
                    "exception": str(e),
                    "retry_count": task.retry_count
                })

                return False


    async def _process_single_task(self, task_id: str):
        """
        处理单个任务的完整流程

        参数:
            task_id: 任务 ID
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error("ANALYSIS.TASK.NOT_FOUND", msg="任务不存在",
                            error_code="E-ANALYSIS-005", extra={
                "task_id": task_id
            })
            return

        try:
            self.active_tasks += 1

            # 步骤 1: 发送 GPT 请求
            success = await self._send_gpt_request(task)
            if not success:
                return

            # 步骤 2: 等待初始延迟
            self.logger.info("ANALYSIS.TASK.WAITING", msg="等待初始延迟", extra={
                "task_id": task_id,
                "delay_seconds": self.initial_delay
            })

            await asyncio.sleep(self.initial_delay)

            # 步骤 3: 轮询任务状态
            start_time = time.time()
            while True:
                # 检查超时
                elapsed_time = time.time() - start_time
                if elapsed_time > self.max_timeout:
                    task.update_status(TaskStatus.TIMEOUT, error=f"任务超时（{self.max_timeout} 秒）")

                    self.logger.error("ANALYSIS.TASK.TIMEOUT", msg="任务执行超时",
                                    error_code="E-ANALYSIS-006", extra={
                            "task_id": task_id,
                            "elapsed_time": elapsed_time,
                            "max_timeout": self.max_timeout
                        })

                    break

                # 轮询状态
                is_completed = await self._poll_task_status(task)

                if is_completed:
                    break

                # 等待下次轮询
                await asyncio.sleep(self.polling_interval)

        except Exception as e:
            task.update_status(TaskStatus.FAILED, error=f"任务处理异常: {str(e)}")

            self.logger.error("ANALYSIS.TASK.EXCEPTION", msg="任务处理异常",
                                error_code="E-ANALYSIS-007", extra={
                    "task_id": task_id,
                    "exception": str(e)
                })

        finally:
            self.active_tasks -= 1

    async def _task_worker(self):
        """
        任务工作协程，从队列中获取任务并处理
        """
        while True:
            try:
                # 从队列获取任务
                task_id = await self.task_queue.get()

                # 检查并发限制
                while self.active_tasks >= self.max_concurrent_tasks:
                    await asyncio.sleep(1)

                # 处理任务
                await self._process_single_task(task_id)

                # 标记任务完成
                self.task_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("ANALYSIS.WORKER.EXCEPTION", msg="工作协程异常",
                                    error_code="E-ANALYSIS-008", extra={
                        "exception": str(e)
                    })

    async def start_workers(self, num_workers: int = 3):
        """
        启动工作协程

        参数:
            num_workers: 工作协程数量
        """
        self.logger.info("ANALYSIS.WORKERS.START", msg="启动工作协程", extra={
            "num_workers": num_workers
        })

        self.workers = [
            asyncio.create_task(self._task_worker())
            for _ in range(num_workers)
        ]

    async def stop_workers(self):
        """停止所有工作协程"""
        self.logger.info("ANALYSIS.WORKERS.STOP", msg="停止工作协程")

        if hasattr(self, 'workers'):
            for worker in self.workers:
                worker.cancel()

            await asyncio.gather(*self.workers, return_exceptions=True)

    async def wait_for_task_completion(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        等待任务完成

        参数:
            task_id: 任务 ID
            timeout: 超时时间（秒），None 表示无限等待

        返回:
            Optional[Dict[str, Any]]: 任务结果字典，如果超时则返回 None
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error("ANALYSIS.WAIT.NOT_FOUND", msg="任务不存在",
                            error_code="E-ANALYSIS-009", extra={
                "task_id": task_id
            })
            return None

        start_time = time.time()

        while task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warn("ANALYSIS.WAIT.TIMEOUT", msg="等待任务超时", extra={
                    "task_id": task_id,
                    "timeout": timeout
                })
                return None

            await asyncio.sleep(1)

        return task.to_dict()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        参数:
            task_id: 任务 ID

        返回:
            Optional[Dict[str, Any]]: 任务状态字典
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        return task.to_dict()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务状态

        返回:
            List[Dict[str, Any]]: 所有任务的状态列表
        """
        return [task.to_dict() for task in self.tasks.values()]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Dict[str, Any]]:
        """
        根据状态获取任务列表

        参数:
            status: 任务状态

        返回:
            List[Dict[str, Any]]: 符合状态的任务列表
        """
        return [
            task.to_dict()
            for task in self.tasks.values()
            if task.status == status
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息

        返回:
            Dict[str, Any]: 统计信息字典
        """
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        success = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        timeout = sum(1 for t in self.tasks.values() if t.status == TaskStatus.TIMEOUT)

        return {
            "total": total,
            "pending": pending,
            "processing": processing,
            "success": success,
            "failed": failed,
            "timeout": timeout,
            "active_tasks": self.active_tasks,
            "queue_size": self.task_queue.qsize(),
            "success_rate": f"{success / total * 100:.2f}%" if total > 0 else "0%"
        }



