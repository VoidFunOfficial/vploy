"""
AI分析异步任务模块

基于Huey实现的AI深度分析异步任务系统，支持：
- GPT API集成
- 任务状态追踪
- 结果轮询和验证
- 错误处理和重试
- VLogger日志集成
"""

import time
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

from ..task_manager.tasks import huey
from ..task_manager.models import TaskDatabase, AsyncTask, TaskStage, TaskStatus
from ..vlogger import TraceContext
from .gpt_api import send_request, get_result, process_result, parse_cookie_string
from ..sys_configs.token_refresher import get_token_refresher, TokenType
from ..polymarket_api import GammaMarketsAPI
from ..core.utils.helpers import market_to_dict
from ..sys_configs.global_event_reg import vlogger


# 使用全局日志记录器
logger = vlogger

# 初始化数据库
db = TaskDatabase()


# ==================== 分析任务状态枚举 ====================

class AnalysisStatus(str, Enum):
    """分析任务状态"""
    PENDING = "pending"              # 待处理：等待发送GPT请求
    WAITING_QUOTA = "waiting_quota"  # 等待额度中：达到频率限制，等待额度恢复
    REQUESTING = "requesting"        # 请求中：正在发送GPT请求
    POLLING = "polling"              # 轮询中：等待GPT响应
    VALIDATING = "validating"        # 验证中：验证返回结果
    SUCCESS = "success"              # 成功：分析完成
    FAILED = "failed"                # 失败：分析失败


# ==================== GPT请求频率限制 ====================

class GPTRequestDatabase:
    """
    GPT请求记录数据库管理器

    用于记录每次GPT请求的时间戳，实现滑动窗口频率限制。
    """

    def __init__(self, db_path: str = "backend/ai_analysis/gpt_requests.db"):
        """
        初始化GPT请求记录数据库

        参数:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建GPT请求记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gpt_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_time TIMESTAMP NOT NULL,
                task_id INTEGER,
                conversation_id TEXT,
                success INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引以提高查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_time
            ON gpt_requests(request_time)
        """)

        conn.commit()
        conn.close()

    def record_request(self, task_id: int, conversation_id: Optional[str] = None, success: bool = True) -> int:
        """
        记录一次GPT请求

        参数:
            task_id: 任务ID
            conversation_id: 会话ID（可选）
            success: 请求是否成功

        返回:
            int: 记录ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO gpt_requests (request_time, task_id, conversation_id, success)
            VALUES (?, ?, ?, ?)
        """, (datetime.now(), task_id, conversation_id, 1 if success else 0))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_request_count_in_window(self, hours: int) -> int:
        """
        获取指定时间窗口内的请求数量

        参数:
            hours: 时间窗口（小时）

        返回:
            int: 请求数量
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        window_start = datetime.now() - timedelta(hours=hours)

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM gpt_requests
            WHERE request_time >= ? AND success = 1
        """, (window_start,))

        result = cursor.fetchone()
        conn.close()

        return result['count'] if result else 0

    def get_next_available_time(self, hours: int, max_requests: int) -> Optional[datetime]:
        """
        获取下一个可用时间点（当前窗口内请求数达到限制时）

        参数:
            hours: 时间窗口（小时）
            max_requests: 最大请求数

        返回:
            Optional[datetime]: 下一个可用时间点，如果当前可用则返回None
        """
        current_count = self.get_request_count_in_window(hours)

        if current_count < max_requests:
            return None

        # 找到窗口内最早的请求时间
        conn = self._get_connection()
        cursor = conn.cursor()

        window_start = datetime.now() - timedelta(hours=hours)

        cursor.execute("""
            SELECT request_time
            FROM gpt_requests
            WHERE request_time >= ? AND success = 1
            ORDER BY request_time ASC
            LIMIT 1
        """, (window_start,))

        result = cursor.fetchone()
        conn.close()

        if result:
            # 最早请求时间 + 窗口时长 = 下一个可用时间
            earliest_request = datetime.fromisoformat(result['request_time'])
            return earliest_request + timedelta(hours=hours)

        return None

    def cleanup_old_records(self, days: int = 30):
        """
        清理旧的请求记录

        参数:
            days: 保留天数
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(days=days)

        cursor.execute("""
            DELETE FROM gpt_requests
            WHERE request_time < ?
        """, (cutoff_time,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(
            "GPT.QUOTA.CLEANUP",
            msg=f"清理了 {deleted_count} 条旧的GPT请求记录",
            extra={"deleted_count": deleted_count, "cutoff_days": days}
        )


class GPTQuotaManager:
    """
    GPT请求额度管理器

    实现滑动窗口频率限制：
    - 6小时内最多30次请求
    - 3天内最多180次请求
    """

    # 限制规则配置
    LIMITS = [
        {"hours": 6, "max_requests": 30},    # 6小时内最多30次
        {"hours": 72, "max_requests": 180},  # 3天内最多180次
    ]

    def __init__(self):
        """初始化额度管理器"""
        self.db = GPTRequestDatabase()

    def check_quota(self) -> Dict[str, Any]:
        """
        检查当前请求额度

        返回:
            Dict[str, Any]: {
                "allowed": bool,           # 是否允许请求
                "reason": str,             # 不允许的原因
                "current_usage": Dict,     # 当前使用情况
                "next_available": datetime # 下一个可用时间（如果被限制）
            }
        """
        current_usage = {}
        next_available_times = []

        for limit in self.LIMITS:
            hours = limit["hours"]
            max_requests = limit["max_requests"]

            current_count = self.db.get_request_count_in_window(hours)
            current_usage[f"{hours}h"] = {
                "current": current_count,
                "limit": max_requests,
                "remaining": max(0, max_requests - current_count)
            }

            if current_count >= max_requests:
                next_available = self.db.get_next_available_time(hours, max_requests)
                if next_available:
                    next_available_times.append(next_available)

        if next_available_times:
            # 如果有限制，返回最晚的可用时间
            next_available = max(next_available_times)
            return {
                "allowed": False,
                "reason": "已达到GPT请求频率限制",
                "current_usage": current_usage,
                "next_available": next_available
            }

        return {
            "allowed": True,
            "reason": "",
            "current_usage": current_usage,
            "next_available": None
        }

    def record_request(self, task_id: int, conversation_id: Optional[str] = None, success: bool = True) -> int:
        """
        记录一次GPT请求

        参数:
            task_id: 任务ID
            conversation_id: 会话ID
            success: 请求是否成功

        返回:
            int: 记录ID
        """
        return self.db.record_request(task_id, conversation_id, success)

    def get_quota_status(self) -> Dict[str, Any]:
        """
        获取详细的额度状态信息

        返回:
            Dict[str, Any]: 详细的额度状态
        """
        quota_check = self.check_quota()

        return {
            "allowed": quota_check["allowed"],
            "reason": quota_check["reason"],
            "usage": quota_check["current_usage"],
            "next_available": quota_check["next_available"].isoformat() if quota_check["next_available"] else None,
            "limits": self.LIMITS
        }


# 全局额度管理器实例
quota_manager = GPTQuotaManager()


# ==================== JSON结构验证 ====================

def validate_analysis_result(result_text: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    验证分析结果是否符合预期的JSON结构（宽松模式）

    预期结构:
    {
        "705811": {  # 键必须是纯数字的market_id字符串
            "p": 0.72,
            "n": 0.28,
            "a": 0.68,
            "reasons_y": [],
            "reasons_n": []
        },
        ...
    }

    重要约束:
    - 键必须是纯数字字符串（market_id），不能是市场描述或其他文本
    - 例如: "705811" ✓  "Will Trump win?" ✗

    容错策略:
    - 尽可能多地提取有效的市场分析数据
    - 对每个市场ID独立验证，跳过无效的市场数据
    - 忽略AI返回结果中的无关文本、注释或其他杂项内容
    - 尝试从包含额外文本的响应中提取有效JSON
    - 只要有至少一个市场数据有效，就返回成功

    参数:
        result_text: GPT返回的文本结果

    返回:
        tuple[bool, Optional[Dict]]: (是否有效, 解析后的JSON对象)
    """
    import json
    import re

    if not result_text or not result_text.strip():
        logger.debug("ANALYSIS.VALIDATE.EMPTY", msg="返回结果为空")
        return False, None

    try:
        # 步骤1: 提取JSON内容（可能被包裹在markdown代码块或其他文本中）
        json_text = result_text.strip()

        # 移除markdown代码块标记
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        elif json_text.startswith("```"):
            json_text = json_text[3:]

        if json_text.endswith("```"):
            json_text = json_text[:-3]

        json_text = json_text.strip()

        # 尝试查找JSON对象（如果文本中包含其他内容）
        # 查找第一个 { 和最后一个 } 之间的内容
        first_brace = json_text.find('{')
        last_brace = json_text.rfind('}')

        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            json_text = json_text[first_brace:last_brace + 1]

        # 步骤2: 解析JSON
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warn(
                "ANALYSIS.VALIDATE.JSON_ERROR",
                msg=f"JSON解析失败: {str(e)}",
                extra={"preview": json_text[:200]}
            )
            return False, None

        # 步骤3: 验证基本结构
        if not isinstance(data, dict):
            logger.warn(
                "ANALYSIS.VALIDATE.NOT_DICT",
                msg="返回结果不是字典类型"
            )
            return False, None

        if len(data) == 0:
            logger.warn(
                "ANALYSIS.VALIDATE.EMPTY_DICT",
                msg="返回结果为空字典"
            )
            return False, None

        # 步骤4: 逐个验证市场数据，保留有效的市场
        valid_markets = {}
        invalid_markets = []

        for market_id, market_data in data.items():
            # 验证market_id必须是纯数字字符串
            if not isinstance(market_id, str) or not market_id.strip().isdigit():
                invalid_markets.append({
                    "market_id": market_id,
                    "reason": f"market_id必须是纯数字字符串，当前值: {market_id}"
                })
                continue

            # 标准化market_id（去除空格）
            market_id = market_id.strip()

            # 验证市场数据是否为字典
            if not isinstance(market_data, dict):
                invalid_markets.append({
                    "market_id": market_id,
                    "reason": "市场数据不是字典类型"
                })
                continue

            # 验证必需字段
            required_fields = ["p", "n", "a"]
            missing_fields = [f for f in required_fields if f not in market_data]

            if missing_fields:
                invalid_markets.append({
                    "market_id": market_id,
                    "reason": f"缺少必需字段: {missing_fields}"
                })
                continue

            # 验证字段类型和范围
            try:
                p_value = market_data["p"]
                n_value = market_data["n"]
                a_value = market_data["a"]

                # 类型检查
                if not isinstance(p_value, (int, float)):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段p类型错误: {type(p_value)}"
                    })
                    continue

                if not isinstance(n_value, (int, float)):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段n类型错误: {type(n_value)}"
                    })
                    continue

                if not isinstance(a_value, (int, float)):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段a类型错误: {type(a_value)}"
                    })
                    continue

                # 范围检查
                if not (0 <= p_value <= 1):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段p超出范围[0,1]: {p_value}"
                    })
                    continue

                if not (0 <= n_value <= 1):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段n超出范围[0,1]: {n_value}"
                    })
                    continue

                if not (0 <= a_value <= 1):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段a超出范围[0,1]: {a_value}"
                    })
                    continue

                # 验证可选字段（如果存在）
                reasons_y = market_data.get("reasons_y", [])
                reasons_n = market_data.get("reasons_n", [])

                if not isinstance(reasons_y, list):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段reasons_y不是列表类型: {type(reasons_y)}"
                    })
                    continue

                if not isinstance(reasons_n, list):
                    invalid_markets.append({
                        "market_id": market_id,
                        "reason": f"字段reasons_n不是列表类型: {type(reasons_n)}"
                    })
                    continue

                # 所有验证通过，添加到有效市场
                valid_markets[market_id] = {
                    "p": p_value,
                    "n": n_value,
                    "a": a_value,
                    "reasons_y": reasons_y,
                    "reasons_n": reasons_n
                }

            except Exception as e:
                invalid_markets.append({
                    "market_id": market_id,
                    "reason": f"验证异常: {str(e)}"
                })
                continue

        # 步骤5: 返回结果
        if len(valid_markets) > 0:
            # 至少有一个有效市场，返回成功
            logger.info(
                "ANALYSIS.VALIDATE.SUCCESS",
                msg=f"成功解析 {len(valid_markets)}/{len(data)} 个市场",
                extra={
                    "valid_count": len(valid_markets),
                    "invalid_count": len(invalid_markets),
                    "valid_market_ids": list(valid_markets.keys()),
                    "invalid_markets": invalid_markets[:5]  # 只记录前5个无效市场
                }
            )
            return True, valid_markets
        else:
            # 没有有效市场，返回失败
            logger.warn(
                "ANALYSIS.VALIDATE.NO_VALID_MARKETS",
                msg="没有找到有效的市场数据",
                extra={
                    "total_markets": len(data),
                    "invalid_markets": invalid_markets[:10]  # 记录前10个无效市场
                }
            )
            return False, None

    except Exception as e:
        logger.error(
            "ANALYSIS.VALIDATE.EXCEPTION",
            msg=f"验证过程异常: {str(e)}",
            error_code="E-VALIDATE-001",
            extra={"exception": str(e), "preview": result_text[:200]}
        )
        return False, None


# ==================== Huey异步任务 ====================

@huey.task()
def submit_gpt_request(
    async_task_id: int,
    event_summary: str
):
    """
    提交GPT请求任务（Huey异步任务）

    工作流程:
    1. 发送GPT请求
    2. 获取conversation_id
    3. 更新任务状态为POLLING
    4. 调度轮询任务

    参数:
        async_task_id: AsyncTask的ID
        event_summary: 事件摘要文本
    """
    with TraceContext() as trace_id:
        logger.info(
            "ANALYSIS.SUBMIT.START",
            msg=f"开始提交GPT请求",
            extra={"async_task_id": async_task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(async_task_id)
            if not task:
                logger.error(
                    "ANALYSIS.SUBMIT.NOT_FOUND",
                    msg=f"任务不存在: {async_task_id}",
                    error_code="E-SUBMIT-001",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 检查GPT请求额度
            quota_check = quota_manager.check_quota()
            if not quota_check["allowed"]:
                # 额度不足，设置任务为等待额度状态
                task.result["analysis_status"] = AnalysisStatus.WAITING_QUOTA.value
                task.result["quota_reason"] = quota_check["reason"]
                task.result["quota_usage"] = quota_check["current_usage"]
                task.result["next_available"] = quota_check["next_available"].isoformat() if quota_check["next_available"] else None
                db.update_async_task(task)

                logger.warn(
                    "ANALYSIS.SUBMIT.QUOTA_EXCEEDED",
                    msg=f"GPT请求额度不足，任务进入等待状态",
                    extra={
                        "async_task_id": async_task_id,
                        "quota_reason": quota_check["reason"],
                        "current_usage": quota_check["current_usage"],
                        "next_available": quota_check["next_available"].isoformat() if quota_check["next_available"] else None
                    },
                    trace_id=trace_id
                )

                # 调度延迟重试任务
                if quota_check["next_available"]:
                    delay_seconds = int((quota_check["next_available"] - datetime.now()).total_seconds())
                    if delay_seconds > 0:
                        # 调度在额度恢复后重新提交
                        submit_gpt_request.schedule(
                            args=(async_task_id, event_summary),
                            delay=delay_seconds
                        )
                        logger.info(
                            "ANALYSIS.SUBMIT.QUOTA_SCHEDULED",
                            msg=f"已调度任务在 {delay_seconds} 秒后重新提交",
                            extra={
                                "async_task_id": async_task_id,
                                "delay_seconds": delay_seconds,
                                "retry_time": quota_check["next_available"].isoformat()
                            },
                            trace_id=trace_id
                        )
                return

            # 获取Cookie
            token_refresher = get_token_refresher()
            access_token_status = token_refresher.get_token_status(TokenType.ACCESS_TOKEN.value)
            auth_token_status = token_refresher.get_token_status(TokenType.AUTH_TOKEN.value)

            if not access_token_status or not auth_token_status:
                error_msg = "未配置access_token或auth_token"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.SUBMIT.NO_TOKEN",
                    msg=error_msg,
                    error_code="E-SUBMIT-002",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            if access_token_status.get('is_expired') or auth_token_status.get('is_expired'):
                error_msg = "access_token或auth_token已过期"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.SUBMIT.TOKEN_EXPIRED",
                    msg=error_msg,
                    error_code="E-SUBMIT-003",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 构建cookie_string
            access_token = access_token_status.get('token_value')
            auth_token = auth_token_status.get('token_value')
            cookie_string = f"__Secure-access_token={access_token};__Secure-auth_token={auth_token}"
            cookies_dict = parse_cookie_string(cookie_string)

            # 加载分析提示词
            import os
            prompt_path = os.path.join(os.path.dirname(__file__), 'analysis.md')
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_analysis = f.read()
            except FileNotFoundError:
                error_msg = f"提示词文件未找到: {prompt_path}"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.SUBMIT.NO_PROMPT",
                    msg=error_msg,
                    error_code="E-SUBMIT-004",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 发送GPT请求
            prompt = f"{prompt_analysis}\n\n请对以下事件进行深度分析：\n\n{event_summary}"

            task.result["analysis_status"] = AnalysisStatus.REQUESTING.value
            db.update_async_task(task)

            logger.info(
                "ANALYSIS.SUBMIT.REQUEST",
                msg="发送GPT请求",
                extra={"async_task_id": async_task_id, "prompt_length": len(prompt)},
                trace_id=trace_id
            )

            result = send_request(
                prompt=prompt,
                cookies=cookies_dict,
                model="gpt-5-1"
            )

            if not result.get("success"):
                error_msg = f"GPT请求失败: {result.get('error', '未知错误')}"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)

                # 记录失败的GPT请求
                quota_manager.record_request(async_task_id, None, success=False)

                logger.error(
                    "ANALYSIS.SUBMIT.REQUEST_FAILED",
                    msg=error_msg,
                    error_code="E-SUBMIT-005",
                    extra={"async_task_id": async_task_id, "result": result},
                    trace_id=trace_id
                )
                return

            # 提取conversation_id - 提交成功的标志
            conversation_id = process_result(result)
            task.result["conversation_id"] = conversation_id
            task.result["analysis_status"] = AnalysisStatus.POLLING.value
            task.result["submit_time"] = time.time()
            db.update_async_task(task)

            # 记录成功的GPT请求
            quota_manager.record_request(async_task_id, conversation_id, success=True)

            logger.info(
                "ANALYSIS.SUBMIT.SUCCESS",
                msg="GPT请求提交成功，获取到conversation_id",
                extra={
                    "async_task_id": async_task_id,
                    "conversation_id": conversation_id
                },
                trace_id=trace_id
            )

        except Exception as e:
            task = db.get_async_task(async_task_id)
            if task:
                task.error_msg = f"提交GPT请求异常: {str(e)}"
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = str(e)
                db.update_async_task(task)

            logger.error(
                "ANALYSIS.SUBMIT.EXCEPTION",
                msg=f"提交GPT请求异常: {str(e)}",
                error_code="E-SUBMIT-006",
                extra={"async_task_id": async_task_id, "exception": str(e)},
                trace_id=trace_id
            )


@huey.task()
def poll_gpt_result(
    async_task_id: int,
    initial_delay: int = 100,
    polling_interval: int = 60,
    max_timeout: int = 3600,
    max_retries: int = 3,
    max_validation_retries: int = 3
):
    """
    轮询GPT结果任务（Huey异步任务）

    工作流程:
    1. 等待初始延迟
    2. 轮询结果直到完成或超时
    3. 验证结果格式
    4. 更新任务状态和结果

    参数:
        async_task_id: AsyncTask的ID
        initial_delay: 首次轮询延迟（秒）
        polling_interval: 轮询间隔（秒）
        max_timeout: 最大超时时间（秒）
        max_retries: 最大重试次数
        max_validation_retries: 最大验证失败重试次数
    """
    with TraceContext() as trace_id:
        logger.info(
            "ANALYSIS.POLL.START",
            msg=f"开始轮询GPT结果",
            extra={"async_task_id": async_task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(async_task_id)
            if not task:
                logger.error(
                    "ANALYSIS.POLL.NOT_FOUND",
                    msg=f"任务不存在: {async_task_id}",
                    error_code="E-POLL-001",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 获取Cookie（提前准备，避免在延迟后才发现token问题）
            token_refresher = get_token_refresher()
            access_token_status = token_refresher.get_token_status(TokenType.ACCESS_TOKEN.value)
            auth_token_status = token_refresher.get_token_status(TokenType.AUTH_TOKEN.value)

            if not access_token_status or not auth_token_status:
                error_msg = "未配置access_token或auth_token"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.POLL.NO_TOKEN",
                    msg=error_msg,
                    error_code="E-POLL-003",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            if access_token_status.get('is_expired') or auth_token_status.get('is_expired'):
                error_msg = "access_token或auth_token已过期"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.POLL.TOKEN_EXPIRED",
                    msg=error_msg,
                    error_code="E-POLL-004",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 构建cookie_string
            access_token = access_token_status.get('token_value')
            auth_token = auth_token_status.get('token_value')
            cookie_string = f"__Secure-access_token={access_token};__Secure-auth_token={auth_token}"
            cookies_dict = parse_cookie_string(cookie_string)

            # 等待初始延迟（让submit_gpt_request有时间完成）
            logger.info(
                "ANALYSIS.POLL.WAITING",
                msg=f"等待初始延迟 {initial_delay} 秒（等待GPT请求提交完成）",
                extra={"async_task_id": async_task_id, "delay": initial_delay},
                trace_id=trace_id
            )
            time.sleep(initial_delay)

            # 延迟后重新获取任务，检查conversation_id
            task = db.get_async_task(async_task_id)
            if not task:
                logger.error(
                    "ANALYSIS.POLL.NOT_FOUND_AFTER_DELAY",
                    msg=f"延迟后任务不存在: {async_task_id}",
                    error_code="E-POLL-001",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            conversation_id = task.result.get("conversation_id")
            if not conversation_id:
                error_msg = "等待初始延迟后仍缺少conversation_id，GPT请求可能失败"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)
                logger.error(
                    "ANALYSIS.POLL.NO_CONVERSATION_ID",
                    msg=error_msg,
                    error_code="E-POLL-002",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return

            # 轮询结果
            start_time = time.time()
            retry_count = 0
            validation_retry_count = 0
            
            while True:
                # 检查超时
                elapsed_time = time.time() - start_time
                if elapsed_time > max_timeout:
                    error_msg = f"任务超时（{max_timeout}秒）"
                    task.error_msg = error_msg
                    task.result["analysis_status"] = AnalysisStatus.FAILED.value
                    task.result["error"] = error_msg
                    db.update_async_task(task)
                    logger.error(
                        "ANALYSIS.POLL.TIMEOUT",
                        msg=error_msg,
                        error_code="E-POLL-005",
                        extra={"async_task_id": async_task_id, "elapsed_time": elapsed_time},
                        trace_id=trace_id
                    )
                    return
                
                # 查询结果
                logger.debug(
                    "ANALYSIS.POLL.QUERY",
                    msg="轮询GPT结果",
                    extra={"async_task_id": async_task_id, "conversation_id": conversation_id},
                    trace_id=trace_id
                )
                
                poll_result = get_result(
                    conversation_id=conversation_id,
                    cookies=cookies_dict
                )
                
                if poll_result.get("success"):
                    # 获取到结果，验证格式
                    ai_response = poll_result.get("ai_response", "")
                    task.result["analysis_status"] = AnalysisStatus.VALIDATING.value
                    task.result["raw_response"] = ai_response
                    db.update_async_task(task)
                    
                    is_valid, parsed_json = validate_analysis_result(ai_response)
                    
                    if is_valid:
                        # 验证成功
                        task.result["analysis_status"] = AnalysisStatus.SUCCESS.value
                        task.result["analysis_result"] = parsed_json
                        task.result["market_ids"] = list(parsed_json.keys())
                        task.metadata["analysis_result"] = parsed_json
                        task.metadata["market_ids"] = list(parsed_json.keys())
                        db.update_async_task(task)

                        logger.info(
                            "ANALYSIS.POLL.SUCCESS",
                            msg="分析完成,准备自动拆分为decision任务",
                            extra={
                                "async_task_id": async_task_id,
                                "market_count": len(parsed_json),
                                "market_ids": list(parsed_json.keys()),
                                "elapsed_time": elapsed_time
                            },
                            trace_id=trace_id
                        )

                        # 自动拆分为decision任务
                        try:
                            split_result = split_analysis_task(async_task_id)
                            if split_result.get("success"):
                                logger.info(
                                    "ANALYSIS.POLL.AUTO_SPLIT_SUCCESS",
                                    msg=f"自动拆分成功,创建了{split_result.get('success_count')}个decision任务",
                                    extra={
                                        "async_task_id": async_task_id,
                                        "created_tasks": split_result.get("created_tasks"),
                                        "success_count": split_result.get("success_count")
                                    },
                                    trace_id=trace_id
                                )
                            else:
                                logger.error(
                                    "ANALYSIS.POLL.AUTO_SPLIT_FAILED",
                                    msg=f"自动拆分失败: {split_result.get('message')}",
                                    error_code="E-POLL-007",
                                    extra={
                                        "async_task_id": async_task_id,
                                        "error": split_result.get("message")
                                    },
                                    trace_id=trace_id
                                )
                        except Exception as split_error:
                            logger.error(
                                "ANALYSIS.POLL.AUTO_SPLIT_EXCEPTION",
                                msg=f"自动拆分异常: {str(split_error)}",
                                error_code="E-POLL-008",
                                extra={
                                    "async_task_id": async_task_id,
                                    "exception": str(split_error)
                                },
                                trace_id=trace_id
                            )

                        return
                    else:
                        # 验证失败，直接标记为失败（不再重新请求）
                        validation_retry_count += 1
                        error_msg = f"结果验证失败: 返回的结果不符合预期的JSON结构"
                        task.error_msg = error_msg
                        task.result["analysis_status"] = AnalysisStatus.FAILED.value
                        task.result["error"] = error_msg
                        db.update_async_task(task)
                        logger.error(
                            "ANALYSIS.POLL.VALIDATION_FAILED",
                            msg=error_msg,
                            error_code="E-POLL-006",
                            extra={
                                "async_task_id": async_task_id,
                                "response_preview": ai_response[:200]
                            },
                            trace_id=trace_id
                        )
                        return
                
                elif poll_result.get("error") == "AI is thinking":
                    # AI仍在思考，继续轮询
                    logger.debug(
                        "ANALYSIS.POLL.THINKING",
                        msg="AI仍在思考",
                        extra={"async_task_id": async_task_id, "elapsed_time": elapsed_time},
                        trace_id=trace_id
                    )
                    time.sleep(polling_interval)
                    continue

                else:
                    # 查询失败
                    retry_count += 1

                    if retry_count >= max_retries:
                        error_msg = f"查询失败（已重试{retry_count}次）: {poll_result.get('error', '未知错误')}"
                        task.error_msg = error_msg
                        task.result["analysis_status"] = AnalysisStatus.FAILED.value
                        task.result["error"] = error_msg
                        db.update_async_task(task)
                        logger.error(
                            "ANALYSIS.POLL.QUERY_FAILED",
                            msg=error_msg,
                            error_code="E-POLL-007",
                            extra={"async_task_id": async_task_id, "retry_count": retry_count},
                            trace_id=trace_id
                        )
                        return
                    else:
                        logger.warn(
                            "ANALYSIS.POLL.QUERY_RETRY",
                            msg=f"查询失败，将重试（{retry_count}/{max_retries}）",
                            extra={"async_task_id": async_task_id, "retry_count": retry_count},
                            trace_id=trace_id
                        )
                        time.sleep(polling_interval)
                        continue
        
        except Exception as e:
            error_msg = f"轮询任务异常: {str(e)}"
            task = db.get_async_task(async_task_id)
            if task:
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                db.update_async_task(task)

            logger.error(
                "ANALYSIS.POLL.EXCEPTION",
                msg=error_msg,
                error_code="E-POLL-008",
                extra={"async_task_id": async_task_id, "exception": str(e)},
                trace_id=trace_id
            )


# ==================== 任务管理函数 ====================

def submit_analysis_task(
    async_task_id: int,
    event_summary: str,
    initial_delay: int = 100,
    polling_interval: int = 60,
    max_timeout: int = 3600
) -> bool:
    """
    提交分析任务到Huey队列

    工作流程:
    1. 保存event_summary到任务（用于重试）
    2. 提交GPT请求任务（立即返回）
    3. 调度轮询任务（在initial_delay后开始轮询）

    参数:
        async_task_id: AsyncTask的ID
        event_summary: 事件摘要文本
        initial_delay: 首次轮询延迟（秒）
        polling_interval: 轮询间隔（秒）
        max_timeout: 最大超时时间（秒）

    返回:
        bool: 是否成功提交（获取到conversation_id即为成功）
    """
    try:
        # 保存event_summary到任务（用于重试）
        task = db.get_async_task(async_task_id)
        if not task:
            logger.error(
                "ANALYSIS.TASK.NOT_FOUND",
                msg=f"任务不存在: {async_task_id}",
                error_code="E-TASK-002",
                extra={"async_task_id": async_task_id}
            )
            return False

        task.result["event_summary"] = event_summary
        task.result["analysis_status"] = AnalysisStatus.PENDING.value
        db.update_async_task(task)

        # 步骤1: 提交GPT请求
        submit_gpt_request(
            async_task_id=async_task_id,
            event_summary=event_summary
        )

        # 步骤2: 调度轮询任务
        poll_gpt_result(
            async_task_id=async_task_id,
            initial_delay=initial_delay,
            polling_interval=polling_interval,
            max_timeout=max_timeout
        )

        logger.info(
            "ANALYSIS.TASK.SUBMITTED",
            msg="分析任务已提交到Huey队列",
            extra={"async_task_id": async_task_id}
        )

        return True

    except Exception as e:
        logger.error(
            "ANALYSIS.TASK.SUBMIT_FAILED",
            msg=f"提交分析任务失败: {str(e)}",
            error_code="E-TASK-001",
            extra={"async_task_id": async_task_id, "exception": str(e)}
        )
        return False


def retry_analysis_task(async_task_id: int) -> bool:
    """
    重试失败的分析任务
    
    参数:
        async_task_id: AsyncTask的ID
        
    返回:
        bool: 是否成功重试
    """
    try:
        task = db.get_async_task(async_task_id)
        if not task:
            logger.error(
                "ANALYSIS.RETRY.NOT_FOUND",
                msg=f"任务不存在: {async_task_id}",
                error_code="E-RETRY-001",
                extra={"async_task_id": async_task_id}
            )
            return False
        
        # 检查任务是否有event_summary
        event_summary = task.result.get("event_summary")
        if not event_summary:
            logger.error(
                "ANALYSIS.RETRY.NO_SUMMARY",
                msg="任务缺少event_summary",
                error_code="E-RETRY-002",
                extra={"async_task_id": async_task_id}
            )
            return False
        
        # 重置任务状态
        task.result["analysis_status"] = AnalysisStatus.PENDING.value
        task.result.pop("error", None)
        task.result.pop("conversation_id", None)
        task.result.pop("raw_response", None)
        task.error_msg = None
        db.update_async_task(task)
        
        # 重新提交任务
        return submit_analysis_task(
            async_task_id=async_task_id,
            event_summary=event_summary
        )
    
    except Exception as e:
        logger.error(
            "ANALYSIS.RETRY.FAILED",
            msg=f"重试任务失败: {str(e)}",
            error_code="E-RETRY-003",
            extra={"async_task_id": async_task_id, "exception": str(e)}
        )
        return False


def split_analysis_task(async_task_id: int) -> Dict[str, Any]:
    """
    拆分成功的analysis任务为多个decision任务

    处理流程:
    1. 验证任务状态（必须是analysis阶段且成功）
    2. 遍历analysis_result中的每个市场
    3. 获取市场详细信息
    4. 合并mark信息
    5. 创建decision任务
    6. 删除原始analysis任务

    参数:
        async_task_id: 异步任务ID

    返回:
        Dict[str, Any]: {
            "success": bool,
            "message": str,
            "created_tasks": List[int],  # 成功创建的任务ID列表
            "failed_markets": List[str],  # 失败的市场ID列表
            "total_markets": int,
            "success_count": int,
            "failed_count": int
        }
    """
    try:
        with TraceContext() as trace_id:
            logger.info(
                "ANALYSIS.SPLIT.START",
                msg=f"开始拆分分析任务: {async_task_id}",
                extra={"async_task_id": async_task_id},
                trace_id=trace_id
            )

            # 1. 获取并验证任务
            task = db.get_async_task(async_task_id)
            if not task:
                return {
                    "success": False,
                    "message": f"任务不存在: {async_task_id}",
                    "created_tasks": [],
                    "failed_markets": [],
                    "total_markets": 0,
                    "success_count": 0,
                    "failed_count": 0
                }

            # 验证任务阶段
            if task.stage != TaskStage.ANALYSIS:
                return {
                    "success": False,
                    "message": f"任务不是分析阶段: {task.stage.value}",
                    "created_tasks": [],
                    "failed_markets": [],
                    "total_markets": 0,
                    "success_count": 0,
                    "failed_count": 0
                }

            # 验证任务状态
            analysis_status = task.result.get("analysis_status")
            if analysis_status != AnalysisStatus.SUCCESS.value:
                return {
                    "success": False,
                    "message": f"任务未成功完成: {analysis_status}",
                    "created_tasks": [],
                    "failed_markets": [],
                    "total_markets": 0,
                    "success_count": 0,
                    "failed_count": 0
                }

            # 获取分析结果
            analysis_result = task.result.get("analysis_result", {})
            if not analysis_result:
                return {
                    "success": False,
                    "message": "分析结果为空",
                    "created_tasks": [],
                    "failed_markets": [],
                    "total_markets": 0,
                    "success_count": 0,
                    "failed_count": 0
                }

            # 获取原始metadata中的marks信息
            original_marks = task.metadata.get("marks", [])

            logger.info(
                "ANALYSIS.SPLIT.PROCESSING",
                msg=f"开始处理 {len(analysis_result)} 个市场",
                extra={
                    "async_task_id": async_task_id,
                    "market_count": len(analysis_result),
                    "original_marks": original_marks
                },
                trace_id=trace_id
            )

            # 2. 遍历每个市场，创建decision任务
            created_tasks = []
            failed_markets = []

            with GammaMarketsAPI() as api:
                for market_id, analysis_data in analysis_result.items():
                    try:
                        # 验证market_id格式（应该是纯数字字符串）
                        if not isinstance(market_id, str) or not market_id.strip().isdigit():
                            logger.warn(
                                "ANALYSIS.SPLIT.INVALID_MARKET_ID",
                                msg=f"无效的market_id格式: {market_id}",
                                extra={"market_id": market_id, "async_task_id": async_task_id},
                                trace_id=trace_id
                            )
                            failed_markets.append(market_id)
                            continue

                        market_id = market_id.strip()

                        # 3. 获取市场详细信息
                        market = api.get_market_by_id(market_id)

                        if not market:
                            logger.warn(
                                "ANALYSIS.SPLIT.MARKET_NOT_FOUND",
                                msg=f"市场不存在: {market_id}",
                                extra={"market_id": market_id, "async_task_id": async_task_id},
                                trace_id=trace_id
                            )
                            failed_markets.append(market_id)
                            continue

                        # 将Market对象转换为字典
                        market_data = market_to_dict(market)

                        # 4. 合并mark信息到市场数据
                        if original_marks:
                            # 将marks添加到市场的marks字段
                            existing_marks = set(market_data.get("marks", []))
                            existing_marks.update(original_marks)
                            market_data["marks"] = list(existing_marks)

                        # 5. 创建decision任务
                        decision_metadata = {
                            "market": market_data,
                            "analysis": {
                                "p": analysis_data.get("p"),
                                "n": analysis_data.get("n"),
                                "a": analysis_data.get("a"),
                                "reasons_y": analysis_data.get("reasons_y", []),
                                "reasons_n": analysis_data.get("reasons_n", [])
                            },
                            "source_analysis_task_id": async_task_id,
                            "marks": original_marks
                        }

                        decision_task = AsyncTask(
                            stage=TaskStage.DECISION,
                            status=TaskStatus.WAITING,
                            metadata=decision_metadata
                        )

                        # 保存任务到数据库
                        decision_task_id = db.create_async_task(decision_task)
                        created_tasks.append(decision_task_id)

                        logger.info(
                            "ANALYSIS.SPLIT.TASK_CREATED",
                            msg=f"创建decision任务成功: {decision_task_id}",
                            extra={
                                "decision_task_id": decision_task_id,
                                "market_id": market_id,
                                "async_task_id": async_task_id
                            },
                            trace_id=trace_id
                        )

                    except Exception as e:
                        logger.error(
                            "ANALYSIS.SPLIT.MARKET_ERROR",
                            msg=f"处理市场失败: {market_id}",
                            error_code="E-SPLIT-001",
                            extra={
                                "market_id": market_id,
                                "async_task_id": async_task_id,
                                "error": str(e)
                            },
                            trace_id=trace_id
                        )
                        failed_markets.append(market_id)

            # 统计结果
            total_markets = len(analysis_result)
            success_count = len(created_tasks)
            failed_count = len(failed_markets)

            # 6. 如果至少有一个任务创建成功，删除原始任务
            if success_count > 0:
                db.delete_async_task(async_task_id)
                logger.info(
                    "ANALYSIS.SPLIT.SUCCESS",
                    msg=f"拆分任务成功，已删除原始任务",
                    extra={
                        "async_task_id": async_task_id,
                        "total_markets": total_markets,
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "created_task_ids": created_tasks
                    },
                    trace_id=trace_id
                )

                return {
                    "success": True,
                    "message": f"成功拆分 {success_count}/{total_markets} 个市场",
                    "created_tasks": created_tasks,
                    "failed_markets": failed_markets,
                    "total_markets": total_markets,
                    "success_count": success_count,
                    "failed_count": failed_count
                }
            else:
                # 所有市场都失败了
                logger.error(
                    "ANALYSIS.SPLIT.ALL_FAILED",
                    msg="所有市场处理失败",
                    error_code="E-SPLIT-002",
                    extra={
                        "async_task_id": async_task_id,
                        "total_markets": total_markets,
                        "failed_markets": failed_markets
                    },
                    trace_id=trace_id
                )

                return {
                    "success": False,
                    "message": "所有市场处理失败，未删除原始任务",
                    "created_tasks": [],
                    "failed_markets": failed_markets,
                    "total_markets": total_markets,
                    "success_count": 0,
                    "failed_count": failed_count
                }

    except Exception as e:
        logger.error(
            "ANALYSIS.SPLIT.FAILED",
            msg=f"拆分任务失败: {str(e)}",
            error_code="E-SPLIT-003",
            extra={"async_task_id": async_task_id, "exception": str(e)}
        )
        return {
            "success": False,
            "message": f"拆分任务失败: {str(e)}",
            "created_tasks": [],
            "failed_markets": [],
            "total_markets": 0,
            "success_count": 0,
            "failed_count": 0
        }


# ==================== 额度恢复检查任务 ====================

@huey.task()
def check_quota_recovery():
    """
    检查等待额度的任务，如果额度已恢复则重新提交

    这个任务应该定期运行（例如每5分钟），检查所有处于WAITING_QUOTA状态的任务
    """
    with TraceContext() as trace_id:
        logger.info(
            "QUOTA.CHECK.START",
            msg="开始检查等待额度的任务",
            trace_id=trace_id
        )

        try:
            # 查询所有等待额度的分析任务
            waiting_tasks = db.query_async_tasks(
                stage=TaskStage.ANALYSIS,
                status=TaskStatus.PROCESSING,  # 分析任务在处理中状态
                limit=100
            )

            quota_waiting_tasks = []
            for task in waiting_tasks:
                analysis_status = task.result.get("analysis_status")
                if analysis_status == AnalysisStatus.WAITING_QUOTA.value:
                    quota_waiting_tasks.append(task)

            if not quota_waiting_tasks:
                logger.debug(
                    "QUOTA.CHECK.NO_WAITING",
                    msg="没有等待额度的任务",
                    trace_id=trace_id
                )
                return

            logger.info(
                "QUOTA.CHECK.FOUND",
                msg=f"找到 {len(quota_waiting_tasks)} 个等待额度的任务",
                extra={"waiting_count": len(quota_waiting_tasks)},
                trace_id=trace_id
            )

            # 检查当前额度状态
            quota_check = quota_manager.check_quota()

            if quota_check["allowed"]:
                # 额度已恢复，重新提交第一个等待的任务
                task = quota_waiting_tasks[0]  # 按创建时间排序，处理最早的任务

                event_summary = task.result.get("event_summary")
                if event_summary:
                    # 重置任务状态为PENDING
                    task.result["analysis_status"] = AnalysisStatus.PENDING.value
                    task.result.pop("quota_reason", None)
                    task.result.pop("quota_usage", None)
                    task.result.pop("next_available", None)
                    db.update_async_task(task)

                    # 重新提交GPT请求
                    submit_gpt_request(task.id, event_summary)

                    logger.info(
                        "QUOTA.CHECK.RESUBMIT",
                        msg=f"额度已恢复，重新提交任务: {task.id}",
                        extra={
                            "task_id": task.id,
                            "quota_usage": quota_check["current_usage"]
                        },
                        trace_id=trace_id
                    )
                else:
                    logger.warn(
                        "QUOTA.CHECK.NO_SUMMARY",
                        msg=f"任务缺少event_summary，无法重新提交: {task.id}",
                        extra={"task_id": task.id},
                        trace_id=trace_id
                    )
            else:
                logger.debug(
                    "QUOTA.CHECK.STILL_LIMITED",
                    msg="额度仍然受限，继续等待",
                    extra={
                        "quota_reason": quota_check["reason"],
                        "next_available": quota_check["next_available"].isoformat() if quota_check["next_available"] else None
                    },
                    trace_id=trace_id
                )

        except Exception as e:
            logger.error(
                "QUOTA.CHECK.EXCEPTION",
                msg=f"检查额度恢复异常: {str(e)}",
                error_code="E-QUOTA-001",
                extra={"exception": str(e)},
                trace_id=trace_id
            )


def get_quota_status() -> Dict[str, Any]:
    """
    获取GPT请求额度状态（供API调用）

    返回:
        Dict[str, Any]: 额度状态信息
    """
    return quota_manager.get_quota_status()


def cleanup_old_quota_records(days: int = 30):
    """
    清理旧的GPT请求记录（供定时任务调用）

    参数:
        days: 保留天数
    """
    quota_manager.db.cleanup_old_records(days)

