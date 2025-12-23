"""
异步任务处理模块

实现基于Huey的异步任务队列和任务路由机制。
"""

from typing import Optional, Dict, Any, Callable
from huey import SqliteHuey
from datetime import datetime

from .config import get_config
from .models import AsyncTask, TaskStage, TaskStatus, TaskDatabase
from ..vlogger import TraceContext
from ..sys_configs.global_event_reg import vlogger


# 初始化Huey任务队列
config = get_config()
huey = SqliteHuey(
    filename=config.huey_db_path,
    immediate=config.immediate,
    utc=True
)

# 使用全局日志记录器
logger = vlogger

# 初始化数据库
db = TaskDatabase()


# ==================== 任务路由注册表 ====================

# 任务处理函数注册表: {(stage, status): handler_function}
_task_handlers: Dict[tuple, Callable] = {}


def register_handler(stage: TaskStage, status: TaskStatus):
    """
    任务处理函数装饰器

    用于注册特定stage和status组合的处理函数。

    使用示例:
        @register_handler(TaskStage.MARK, TaskStatus.WAITING)
        def handle_mark_waiting(task: AsyncTask) -> Dict[str, Any]:
            # 处理逻辑
            return {"success": True}

    参数:
        stage: 任务阶段
        status: 任务状态
    """
    def decorator(func: Callable):
        key = (stage, status)
        _task_handlers[key] = func
        logger.info(
            "TASK.HANDLER.REGISTERED",
            msg=f"注册任务处理函数: {stage.value}/{status.value} -> {func.__name__}",
            extra={"stage": stage.value, "status": status.value, "handler": func.__name__}
        )
        return func
    return decorator


def get_handler(stage: TaskStage, status: TaskStatus) -> Optional[Callable]:
    """
    获取任务处理函数

    参数:
        stage: 任务阶段
        status: 任务状态

    返回:
        Callable: 处理函数，如果未注册则返回None
    """
    key = (stage, status)
    return _task_handlers.get(key)


# ==================== 核心任务处理函数 ====================

@huey.task()
def process_async_task(task_id: int):
    """
    处理异步任务（Huey任务）

    根据任务的stage和status路由到对应的处理函数。

    参数:
        task_id: 任务ID
    """
    with TraceContext() as trace_id:
        logger.info(
            "TASK.PROCESS.START",
            msg=f"开始处理任务: {task_id}",
            extra={"task_id": task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(task_id)
            if task is None:
                logger.error(
                    "TASK.PROCESS.NOT_FOUND",
                    msg=f"任务不存在: {task_id}",
                    error_code="E-TASK-001",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )
                return

            # 获取处理函数
            handler = get_handler(task.stage, task.status)
            if handler is None:
                logger.warn(
                    "TASK.PROCESS.NO_HANDLER",
                    msg=f"未找到处理函数: {task.stage.value}/{task.status.value}",
                    extra={
                        "task_id": task_id,
                        "stage": task.stage.value,
                        "status": task.status.value
                    },
                    trace_id=trace_id
                )
                return

            # 执行处理函数
            logger.info(
                "TASK.PROCESS.EXECUTE",
                msg=f"执行处理函数: {handler.__name__}",
                extra={
                    "task_id": task_id,
                    "stage": task.stage.value,
                    "status": task.status.value,
                    "handler": handler.__name__
                },
                trace_id=trace_id
            )

            result = handler(task)

            # 更新任务结果
            task.result = result or {}

            # 检查是否需要转换到下一个阶段/状态
            if result and "next_stage" in result and "next_status" in result:
                next_stage = TaskStage(result["next_stage"])
                next_status = TaskStatus(result["next_status"])

                task.stage = next_stage
                task.status = next_status

                logger.info(
                    "TASK.PROCESS.STAGE_TRANSITION",
                    msg=f"任务转换到新阶段: {next_stage.value}/{next_status.value}",
                    extra={
                        "task_id": task_id,
                        "next_stage": next_stage.value,
                        "next_status": next_status.value
                    },
                    trace_id=trace_id
                )
            elif result and result.get("status") == "waiting":
                # 保持WAITING状态不变
                logger.info(
                    "TASK.PROCESS.KEEP_WAITING",
                    msg=f"任务保持WAITING状态",
                    extra={
                        "task_id": task_id,
                        "stage": task.stage.value,
                        "status": task.status.value
                    },
                    trace_id=trace_id
                )
            else:
                # 默认标记为完成
                task.status = TaskStatus.FINISHED

            db.update_async_task(task)

            logger.info(
                "TASK.PROCESS.SUCCESS",
                msg=f"任务处理成功: {task_id}",
                extra={
                    "task_id": task_id,
                    "stage": task.stage.value,
                    "status": task.status.value,
                    "result": result
                },
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "TASK.PROCESS.FAILED",
                msg=f"任务处理失败: {task_id}",
                error_code="E-TASK-002",
                extra={"task_id": task_id, "error": str(e)},
                trace_id=trace_id
            )

            # 更新任务状态为失败
            task = db.get_async_task(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error_msg = str(e)
                db.update_async_task(task)


def submit_task(task: AsyncTask) -> int:
    """
    提交异步任务

    将任务保存到数据库并提交到Huey队列。

    参数:
        task: 任务实例

    返回:
        int: 任务ID
    """
    with TraceContext() as trace_id:
        # 保存任务到数据库
        task_id = db.create_async_task(task)
        task.id = task_id

        logger.info(
            "TASK.SUBMIT",
            msg=f"提交任务: {task_id}",
            extra={
                "task_id": task_id,
                "stage": task.stage.value,
                "status": task.status.value,
                "metadata": task.metadata
            },
            trace_id=trace_id
        )

        # 提交到Huey队列
        process_async_task(task_id)

        return task_id


def approve_analysis(task_id: int) -> bool:
    """
    批准分析任务，将ANALYSIS+WAITING状态的任务转换为PROCESSING状态

    参数:
        task_id: 任务ID

    返回:
        bool: 是否成功批准
    """
    with TraceContext() as trace_id:
        logger.info(
            "TASK.APPROVE.START",
            msg=f"批准分析任务: {task_id}",
            extra={"task_id": task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(task_id)
            if task is None:
                logger.error(
                    "TASK.APPROVE.NOT_FOUND",
                    msg=f"任务不存在: {task_id}",
                    error_code="E-APPROVE-001",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )
                return False

            # 检查任务状态
            if task.stage != TaskStage.ANALYSIS or task.status != TaskStatus.WAITING:
                logger.error(
                    "TASK.APPROVE.INVALID_STATE",
                    msg=f"任务状态不正确，当前: {task.stage.value}/{task.status.value}",
                    error_code="E-APPROVE-002",
                    extra={
                        "task_id": task_id,
                        "stage": task.stage.value,
                        "status": task.status.value
                    },
                    trace_id=trace_id
                )
                return False

            # 转换为PROCESSING状态
            task.status = TaskStatus.PROCESSING
            db.update_async_task(task)

            logger.info(
                "TASK.APPROVE.SUCCESS",
                msg=f"任务已批准，转换为PROCESSING状态",
                extra={
                    "task_id": task_id,
                    "stage": task.stage.value,
                    "status": task.status.value
                },
                trace_id=trace_id
            )

            # 提交到Huey队列进行处理
            process_async_task(task_id)

            return True

        except Exception as e:
            logger.error(
                "TASK.APPROVE.FAILED",
                msg=f"批准任务失败: {task_id}",
                error_code="E-APPROVE-003",
                extra={"task_id": task_id, "error": str(e)},
                trace_id=trace_id
            )
            return False


def retry_analysis(task_id: int) -> bool:
    """
    重试失败的分析任务

    参数:
        task_id: 任务ID

    返回:
        bool: 是否成功重试
    """
    from ..ai_analysis.analysis_tasks import retry_analysis_task

    with TraceContext() as trace_id:
        logger.info(
            "TASK.RETRY.START",
            msg=f"重试分析任务: {task_id}",
            extra={"task_id": task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(task_id)
            if task is None:
                logger.error(
                    "TASK.RETRY.NOT_FOUND",
                    msg=f"任务不存在: {task_id}",
                    error_code="E-RETRY-001",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )
                return False

            # 检查任务阶段
            if task.stage != TaskStage.ANALYSIS:
                logger.error(
                    "TASK.RETRY.INVALID_STAGE",
                    msg=f"只能重试ANALYSIS阶段的任务，当前: {task.stage.value}",
                    error_code="E-RETRY-002",
                    extra={
                        "task_id": task_id,
                        "stage": task.stage.value
                    },
                    trace_id=trace_id
                )
                return False

            # 调用analysis_tasks模块的重试函数
            success = retry_analysis_task(task_id)

            if success:
                logger.info(
                    "TASK.RETRY.SUCCESS",
                    msg=f"任务已重新提交",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )
            else:
                logger.error(
                    "TASK.RETRY.FAILED",
                    msg=f"重试任务失败",
                    error_code="E-RETRY-003",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )

            return success

        except Exception as e:
            logger.error(
                "TASK.RETRY.EXCEPTION",
                msg=f"重试任务异常: {task_id}",
                error_code="E-RETRY-004",
                extra={"task_id": task_id, "error": str(e)},
                trace_id=trace_id
            )
            return False


# ==================== 任务处理函数占位符 ====================

@register_handler(TaskStage.MARK, TaskStatus.WAITING)
def handle_mark_waiting(task: AsyncTask) -> Dict[str, Any]:
    """
    处理MARK阶段的WAITING状态任务

    需要用户手动允许才进行实际业务处理。

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.MARK.WAITING",
        msg="MARK阶段任务等待用户确认",
        extra={"task_id": task.id, "metadata": task.metadata}
    )
    # TODO: 实现用户确认逻辑
    return {"status": "waiting_for_approval", "message": "等待用户确认"}


@register_handler(TaskStage.MARK, TaskStatus.PROCESSING)
def handle_mark_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理MARK阶段的PROCESSING状态任务

    使用auto_mark.py处理事件标记，将mark写到result里，
    然后转换到TRADE+WAITING状态

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    from ..polymarket_api import GammaMarketsAPI
    from ..mark.auto_mark import mark

    logger.info(
        "TASK.MARK.PROCESSING",
        msg="处理MARK阶段任务",
        extra={"task_id": task.id, "metadata": task.metadata}
    )

    try:
        # 从metadata中获取market信息(由decision阶段传递过来)
        market_data = task.metadata.get("market")
        if not market_data:
            error_msg = "metadata中缺少market信息"
            logger.error(
                "TASK.MARK.ERROR",
                msg=error_msg,
                error_code="E-MARK-001",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 获取event_id
        event_id = market_data.get("event_id")
        if not event_id:
            error_msg = "market中缺少event_id"
            logger.error(
                "TASK.MARK.ERROR",
                msg=error_msg,
                error_code="E-MARK-002",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 通过API获取Event对象
        with GammaMarketsAPI() as api:
            event = api.get_event_by_id(event_id)

        if not event:
            error_msg = f"未找到event_id: {event_id}"
            logger.error(
                "TASK.MARK.ERROR",
                msg=error_msg,
                error_code="E-MARK-003",
                extra={"task_id": task.id, "event_id": event_id}
            )
            return {"status": "failed", "message": error_msg}

        # 调用auto_mark进行标记
        mark_result = mark(event)

        logger.info(
            "TASK.MARK.SUCCESS",
            msg="标记处理完成",
            extra={
                "task_id": task.id,
                "event_id": event_id,
                "mark_result": mark_result
            }
        )

        # 将mark结果写入result
        result = {
            "mark": mark_result,
            "event_id": event_id,
            "event_title": event.title,
            "market_id": market_data.get("id")
        }

        # 将当前任务的metadata更新，添加mark结果
        task.metadata["mark"] = mark_result
        task.metadata["event_title"] = event.title

        logger.info(
            "TASK.MARK.TO_TRADE_WAITING",
            msg="标记完成，转换为TRADE+WAITING状态，等待用户批准",
            extra={
                "task_id": task.id,
                "event_id": event_id,
                "mark": mark_result
            }
        )

        # 返回结果，指示任务应该转换为TRADE+WAITING状态
        return {
            "status": "processed",
            "message": "标记处理完成，等待用户批准开始交易",
            "result": result,
            "next_stage": TaskStage.TRADE.value,
            "next_status": TaskStatus.WAITING.value
        }

    except Exception as e:
        error_msg = f"标记处理异常: {str(e)}"
        logger.error(
            "TASK.MARK.EXCEPTION",
            msg=error_msg,
            error_code="E-MARK-003",
            extra={"task_id": task.id, "exception": str(e)}
        )
        return {"status": "failed", "message": error_msg}


@register_handler(TaskStage.ANALYSIS, TaskStatus.WAITING)
def handle_analysis_waiting(task: AsyncTask) -> Dict[str, Any]:
    """
    处理ANALYSIS阶段的WAITING状态任务

    等待用户批准后才开始分析，不自动转换为PROCESSING

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.ANALYSIS.WAITING",
        msg="ANALYSIS阶段任务等待用户批准",
        extra={
            "task_id": task.id,
            "metadata": task.metadata,
            "event_id": task.metadata.get("event_id"),
            "mark": task.metadata.get("mark")
        }
    )

    # 返回waiting状态，保持WAITING状态不变，等待用户调用approve_analysis()
    return {
        "status": "waiting",
        "message": "等待用户批准开始分析",
        "result": {
            "event_id": task.metadata.get("event_id"),
            "mark": task.metadata.get("mark"),
            "event_title": task.metadata.get("event_title")
        }
    }


@register_handler(TaskStage.ANALYSIS, TaskStatus.PROCESSING)
def handle_analysis_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理ANALYSIS阶段的PROCESSING状态任务

    通过polymarket的api获取event_summary_readableforai，
    提交给Huey异步任务进行GPT分析处理

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    from ..polymarket_api import GammaMarketsAPI, event_summary_readableforai
    from ..ai_analysis.analysis_tasks import submit_analysis_task, AnalysisStatus

    logger.info(
        "TASK.ANALYSIS.PROCESSING",
        msg="处理ANALYSIS阶段任务",
        extra={"task_id": task.id, "metadata": task.metadata}
    )

    try:
        # 从metadata中获取event_id
        event_id = task.metadata.get("event_id")
        if not event_id:
            error_msg = "metadata中缺少event_id"
            logger.error(
                "TASK.ANALYSIS.ERROR",
                msg=error_msg,
                error_code="E-ANALYSIS-001",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 通过API获取Event对象
        with GammaMarketsAPI() as api:
            event = api.get_event_by_id(event_id)

        if not event:
            error_msg = f"未找到event_id: {event_id}"
            logger.error(
                "TASK.ANALYSIS.ERROR",
                msg=error_msg,
                error_code="E-ANALYSIS-002",
                extra={"task_id": task.id, "event_id": event_id}
            )
            return {"status": "failed", "message": error_msg}

        # 生成event_summary_readableforai
        event_summary = event_summary_readableforai(event)

        logger.info(
            "TASK.ANALYSIS.SUMMARY_GENERATED",
            msg="生成事件摘要",
            extra={
                "task_id": task.id,
                "event_id": event_id,
                "summary_length": len(event_summary)
            }
        )

        # 将event_summary保存到result中，供重试使用
        task.result["event_summary"] = event_summary
        task.result["analysis_status"] = AnalysisStatus.PENDING.value
        db.update_async_task(task)

        # 提交到Huey异步任务队列
        success = submit_analysis_task(
            async_task_id=task.id,
            event_summary=event_summary,
            initial_delay=300,      # 5分钟
            polling_interval=60,    # 1分钟
            max_timeout=3600        # 1小时
        )

        if not success:
            error_msg = "提交分析任务到Huey队列失败"
            logger.error(
                "TASK.ANALYSIS.ERROR",
                msg=error_msg,
                error_code="E-ANALYSIS-003",
                extra={"task_id": task.id, "event_id": event_id}
            )
            return {"status": "failed", "message": error_msg}

        logger.info(
            "TASK.ANALYSIS.SUBMITTED",
            msg="已提交分析任务到Huey队列",
            extra={
                "task_id": task.id,
                "event_id": event_id
            }
        )

        # 返回processing状态，任务将继续在后台执行
        # 注意：这里不等待结果，任务会在Huey中异步执行
        # 结果会直接写入task.result和task.metadata
        return {
            "status": "processing",
            "message": "分析任务已提交到后台队列",
            "result": {
                "event_id": event_id,
                "analysis_status": AnalysisStatus.PENDING.value
            }
        }

    except Exception as e:
        error_msg = f"分析处理异常: {str(e)}"
        logger.error(
            "TASK.ANALYSIS.EXCEPTION",
            msg=error_msg,
            error_code="E-ANALYSIS-007",
            extra={"task_id": task.id, "exception": str(e)}
        )
        return {"status": "failed", "message": error_msg}




@register_handler(TaskStage.DECISION, TaskStatus.WAITING)
def handle_decision_waiting(task: AsyncTask) -> Dict[str, Any]:
    """
    处理DECISION阶段的WAITING状态任务

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.DECISION.WAITING",
        msg="DECISION阶段任务等待处理",
        extra={"task_id": task.id}
    )
    # TODO: 实现决策等待逻辑
    return {"status": "ready", "message": "准备开始决策"}


@register_handler(TaskStage.DECISION, TaskStatus.PROCESSING)
def handle_decision_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理DECISION阶段的PROCESSING状态任务

    决策完成后转换到MARK+WAITING阶段

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.DECISION.PROCESSING",
        msg="处理DECISION阶段任务",
        extra={"task_id": task.id, "metadata": task.metadata}
    )

    # TODO: 实现决策处理逻辑
    # 这里应该实现具体的决策算法

    # 将决策结果保存到result中
    decision_result = {
        "decision": "TEMP_DECISION",  # 临时决策结果,待实现真正的决策逻辑
        "timestamp": datetime.now().isoformat()
    }

    task.result["decision"] = decision_result

    logger.info(
        "TASK.DECISION.TO_MARK_WAITING",
        msg="决策完成,转换为MARK+WAITING状态,等待用户批准",
        extra={
            "task_id": task.id,
            "decision": decision_result
        }
    )

    # 返回结果,指示任务应该转换为MARK+WAITING状态
    return {
        "status": "processed",
        "message": "决策处理完成,等待用户批准开始标记",
        "result": decision_result,
        "next_stage": TaskStage.MARK.value,
        "next_status": TaskStatus.WAITING.value
    }


@register_handler(TaskStage.TRADE, TaskStatus.WAITING)
def handle_trade_waiting(task: AsyncTask) -> Dict[str, Any]:
    """
    处理TRADE阶段的WAITING状态任务

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.TRADE.WAITING",
        msg="TRADE阶段任务等待处理",
        extra={"task_id": task.id}
    )
    # TODO: 实现交易等待逻辑
    return {"status": "waiting", "message": task.result}


@register_handler(TaskStage.TRADE, TaskStatus.PROCESSING)
def handle_trade_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理TRADE阶段的PROCESSING状态任务

    根据任务的metadata和result进行自动挂单，并添加到仓位监听

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    from ..auto_trade.auto_trade_exec import trade
    from ..position_listener import record_trade
    from ..types import TradeAllocation
    import json

    logger.info(
        "TASK.TRADE.PROCESSING",
        msg="处理TRADE阶段任务",
        extra={"task_id": task.id, "metadata": task.metadata, "result": task.result}
    )

    try:
        # 从metadata中获取市场信息
        market = task.metadata.get("market")
        if not market:
            error_msg = "metadata中缺少market信息"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-001",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 从result中获取决策信息
        decision = task.result.get("decision")
        allocation = task.result.get("allocation")

        if not decision or not allocation:
            error_msg = "result中缺少decision或allocation信息"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-002",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 检查是否需要交易
        if decision != "trade":
            logger.info(
                "TASK.TRADE.SKIP",
                msg=f"决策为{decision}，跳过交易",
                extra={"task_id": task.id, "decision": decision}
            )
            return {
                "status": "skipped",
                "message": f"决策为{decision}，跳过交易",
                "decision": decision
            }

        # 提取交易参数
        side = allocation.get("side")  # "YES" 或 "NO"
        dollars = allocation.get("dollars")  # 投入金额
        shares = allocation.get("shares")  # 购买份额
        cost = allocation.get("cost")  # 成本（价格）

        if not side or dollars is None or cost is None:
            error_msg = "allocation中缺少必要的交易参数"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-003",
                extra={"task_id": task.id, "allocation": allocation}
            )
            return {"status": "failed", "message": error_msg}

        # 获取clobTokenIds
        clob_token_ids_str = market.get("clobTokenIds")
        if not clob_token_ids_str:
            error_msg = "market中缺少clobTokenIds"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-004",
                extra={"task_id": task.id, "market_id": market.get("id")}
            )
            return {"status": "failed", "message": error_msg}

        # 解析clobTokenIds (JSON数组字符串)
        try:
            clob_token_ids = json.loads(clob_token_ids_str)
        except json.JSONDecodeError:
            error_msg = f"clobTokenIds解析失败: {clob_token_ids_str}"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-005",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 根据side选择token_id
        # clobTokenIds[0] 是 YES token, clobTokenIds[1] 是 NO token
        if side == "YES":
            clobtoken = clob_token_ids[0]
        elif side == "NO":
            clobtoken = clob_token_ids[1]
        else:
            error_msg = f"无效的side值: {side}"
            logger.error(
                "TASK.TRADE.ERROR",
                msg=error_msg,
                error_code="E-TRADE-006",
                extra={"task_id": task.id, "side": side}
            )
            return {"status": "failed", "message": error_msg}

        # 获取negRisk标志
        neg_risk = market.get("negRisk", False)

        logger.info(
            "TASK.TRADE.EXECUTE",
            msg="开始执行交易",
            extra={
                "task_id": task.id,
                "market_id": market.get("id"),
                "market_question": market.get("question"),
                "side": side,
                "dollars": dollars,
                "cost": cost,
                "shares": shares,
                "clobtoken": clobtoken,
                "neg_risk": neg_risk
            }
        )

        # 调用auto_trade_exec.trade()进行自动挂单（挂best-bid-2限价单）
        # 目标: 达到预期shares且花费不超过dollars
        trade_result = trade(
            side="BUY",  # 我们总是买入(BUY)，买入YES或NO token
            target_shares=shares,  # 目标购买数量
            max_cost=dollars,  # 最大允许成本
            clobtoken=clobtoken,  # token ID
            neg_risk=neg_risk  # 是否为负风险市场
        )

        logger.info(
            "TASK.TRADE.SUCCESS",
            msg="交易执行成功（已挂best-bid-2限价单）",
            extra={
                "task_id": task.id,
                "market_id": market.get("id"),
                "trade_result": trade_result
            }
        )

        # 添加到仓位监听（使用新的position_listener系统）
        try:
            # 提取订单信息
            order_id = trade_result.get("order_id") or trade_result.get("orderID")

            # 创建TradeAllocation对象
            # 从allocation中提取信息，如果没有则使用默认值
            allocation_data = allocation or {}

            trade_allocation = TradeAllocation(
                id=market.get("id"),  # 市场ID
                side=side,  # 交易方向（YES/NO）
                price=cost,  # 交易价格
                p=allocation_data.get("p", 0.5),  # 主观概率（如果没有则默认0.5）
                b=allocation_data.get("b", 2.0),  # 赔率（如果没有则默认2.0）
                f=allocation_data.get("f", 0.0),  # 仓位比例
                invest=dollars,  # 投资金额
                shares=shares,  # 购买份额
                settle_day=allocation_data.get("settle_day", 30)  # 结算日期（默认30天）
            )

            # 准备任务元信息，传递给position_listener
            task_metadata_for_position = {
                "analysis": task.metadata.get("analysis"),
                "market": task.metadata.get("market"),
                "marks": task.metadata.get("marks"),
                "source_analysis_task_id": task.metadata.get("source_analysis_task_id")
            }

            # 记录交易到position_listener（record_trade内部会自动创建订单记录）
            position_id = record_trade(
                allocation=trade_allocation,
                order_id=order_id,
                token_id=clobtoken,
                task_metadata=task_metadata_for_position
            )

            logger.info(
                "TASK.TRADE.POSITION_ADDED",
                msg="已添加到仓位监听（新系统）",
                extra={
                    "task_id": task.id,
                    "position_id": position_id,
                    "market_id": market.get("id"),
                    "buy_price": cost,
                    "buy_side": side,
                    "shares": shares,
                    "order_id": order_id
                }
            )

            # 返回成功结果，包含order_id和订单创建时间
            import time
            return {
                "status": "traded",
                "message": "交易完成并已添加到仓位监听（挂best-bid-2限价单）",
                "trade_result": trade_result,
                "order_id": order_id,  # 保存order_id供LISTEN阶段使用
                "order_created_at": time.time(),  # 记录订单创建时间
                "position_id": position_id,
                "market_id": market.get("id"),
                "market_question": market.get("question"),
                "side": side,
                "dollars": dollars,
                "cost": cost,
                "shares": shares,
                "clobtoken": clobtoken,
                "neg_risk": neg_risk,
                "next_stage": TaskStage.LISTEN.value,
                "next_status": TaskStatus.WAITING.value
            }

        except Exception as e:
            error_msg = f"添加仓位监听失败: {str(e)}"
            logger.error(
                "TASK.TRADE.POSITION_ERROR",
                msg=error_msg,
                error_code="E-TRADE-008",
                extra={"task_id": task.id, "exception": str(e)}
            )
            # 即使添加仓位监听失败，交易已经完成，所以返回部分成功
            return {
                "status": "traded_with_warning",
                "message": f"交易完成但添加仓位监听失败: {str(e)}",
                "trade_result": trade_result,
                "warning": error_msg
            }

    except Exception as e:
        error_msg = f"交易处理异常: {str(e)}"
        logger.error(
            "TASK.TRADE.EXCEPTION",
            msg=error_msg,
            error_code="E-TRADE-007",
            extra={"task_id": task.id, "exception": str(e)}
        )
        return {"status": "failed", "message": error_msg}


@register_handler(TaskStage.LISTEN, TaskStatus.WAITING)
def handle_listen_waiting(task: AsyncTask) -> Dict[str, Any]:
    """
    处理LISTEN阶段的WAITING状态任务

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.LISTEN.WAITING",
        msg="LISTEN阶段任务等待处理",
        extra={"task_id": task.id}
    )
    return {"status": "ready", "message": "准备开始监听订单状态"}


@register_handler(TaskStage.LISTEN, TaskStatus.PROCESSING)
def handle_listen_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理LISTEN阶段的PROCESSING状态任务

    监听订单状态，如果10分钟后仍未成交，则调用sweep_order进行扫单

    注意：订单状态监控由position_listener系统自动处理（每2分钟），
    此处主要处理超时扫单逻辑。

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    from ..auto_trade.auto_trade_exec import sweep_order
    from ..polymarket_api.clob_api import get_order, cancel_order
    from ..position_listener import monitor_order
    import time

    logger.info(
        "TASK.LISTEN.PROCESSING",
        msg="处理LISTEN阶段任务",
        extra={"task_id": task.id}
    )

    try:
        # 从result中获取订单信息
        order_id = task.result.get("order_id")
        order_created_at = task.result.get("order_created_at")

        if not order_id:
            error_msg = "result中缺少order_id信息"
            logger.error(
                "TASK.LISTEN.ERROR",
                msg=error_msg,
                error_code="E-LISTEN-001",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        if not order_created_at:
            error_msg = "result中缺少order_created_at信息"
            logger.error(
                "TASK.LISTEN.ERROR",
                msg=error_msg,
                error_code="E-LISTEN-002",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 检查订单状态（使用新的position_listener系统）
        try:
            # 先使用position_listener监控订单
            monitor_result = monitor_order(order_id)

            # 同时从CLOB API获取订单详情
            order_info = get_order(order_id)
            order_status = order_info.get("status", "").upper()

            logger.info(
                "TASK.LISTEN.ORDER_STATUS",
                msg=f"订单状态: {order_status}",
                extra={
                    "task_id": task.id,
                    "order_id": order_id,
                    "order_status": order_status,
                    "monitor_result": monitor_result,
                    "order_info": order_info
                }
            )

            # 如果订单已完全成交，任务完成
            if order_status in ["FILLED", "MATCHED"]:
                logger.info(
                    "TASK.LISTEN.ORDER_FILLED",
                    msg="订单已完全成交",
                    extra={
                        "task_id": task.id,
                        "order_id": order_id,
                        "order_info": order_info
                    }
                )
                return {
                    "status": "completed",
                    "message": "订单已完全成交",
                    "order_id": order_id,
                    "order_info": order_info,
                    "next_stage": TaskStage.LISTEN.value,
                    "next_status": TaskStatus.FINISHED.value
                }

            # 如果订单已取消或失败
            if order_status in ["CANCELLED", "CANCELED", "FAILED", "EXPIRED"]:
                logger.warn(
                    "TASK.LISTEN.ORDER_CANCELLED",
                    msg=f"订单已取消或失败: {order_status}",
                    extra={
                        "task_id": task.id,
                        "order_id": order_id,
                        "order_status": order_status
                    }
                )
                # 需要扫单
                return _execute_sweep_order(task)

            # 检查是否超过10分钟
            current_time = time.time()
            elapsed_time = current_time - order_created_at
            WAIT_TIMEOUT = 600  # 10分钟 = 600秒

            if elapsed_time >= WAIT_TIMEOUT:
                logger.info(
                    "TASK.LISTEN.TIMEOUT",
                    msg="订单10分钟未成交，准备取消并扫单",
                    extra={
                        "task_id": task.id,
                        "order_id": order_id,
                        "elapsed_time": elapsed_time,
                        "timeout": WAIT_TIMEOUT
                    }
                )

                # 取消原订单
                try:
                    cancel_result = cancel_order(order_id)
                    logger.info(
                        "TASK.LISTEN.ORDER_CANCELLED",
                        msg="已取消原订单",
                        extra={
                            "task_id": task.id,
                            "order_id": order_id,
                            "cancel_result": cancel_result
                        }
                    )
                except Exception as e:
                    logger.warn(
                        "TASK.LISTEN.CANCEL_ERROR",
                        msg=f"取消订单失败（可能已成交或已取消）: {str(e)}",
                        extra={
                            "task_id": task.id,
                            "order_id": order_id,
                            "error": str(e)
                        }
                    )

                # 执行扫单
                return _execute_sweep_order(task)

            else:
                # 继续等待
                remaining_time = WAIT_TIMEOUT - elapsed_time
                logger.info(
                    "TASK.LISTEN.WAITING",
                    msg=f"订单尚未成交，继续等待（剩余{remaining_time:.0f}秒）",
                    extra={
                        "task_id": task.id,
                        "order_id": order_id,
                        "elapsed_time": elapsed_time,
                        "remaining_time": remaining_time
                    }
                )
                return {
                    "status": "listening",
                    "message": f"订单尚未成交，继续等待（剩余{remaining_time:.0f}秒）",
                    "order_id": order_id,
                    "elapsed_time": elapsed_time,
                    "remaining_time": remaining_time
                }

        except Exception as e:
            error_msg = f"查询订单状态失败: {str(e)}"
            logger.error(
                "TASK.LISTEN.QUERY_ERROR",
                msg=error_msg,
                error_code="E-LISTEN-003",
                extra={"task_id": task.id, "order_id": order_id, "error": str(e)}
            )
            return {"status": "failed", "message": error_msg}

    except Exception as e:
        error_msg = f"监听处理异常: {str(e)}"
        logger.error(
            "TASK.LISTEN.EXCEPTION",
            msg=error_msg,
            error_code="E-LISTEN-004",
            extra={"task_id": task.id, "exception": str(e)}
        )
        return {"status": "failed", "message": error_msg}


def _execute_sweep_order(task: AsyncTask) -> Dict[str, Any]:
    """
    执行扫单操作（内部辅助函数）

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    from ..auto_trade.auto_trade_exec import sweep_order

    logger.info(
        "TASK.LISTEN.SWEEP_START",
        msg="开始执行扫单",
        extra={"task_id": task.id}
    )

    try:
        # 从result中获取交易参数
        side = task.result.get("side")
        dollars = task.result.get("dollars")
        shares = task.result.get("shares")
        clobtoken = task.result.get("clobtoken")
        neg_risk = task.result.get("neg_risk")

        if not all([side, dollars, shares, clobtoken]):
            error_msg = "result中缺少必要的交易参数"
            logger.error(
                "TASK.LISTEN.SWEEP_ERROR",
                msg=error_msg,
                error_code="E-LISTEN-005",
                extra={"task_id": task.id}
            )
            return {"status": "failed", "message": error_msg}

        # 执行扫单
        sweep_result = sweep_order(
            side="BUY",  # 我们总是买入(BUY)
            target_shares=shares,
            max_cost=dollars,
            clobtoken=clobtoken,
            neg_risk=neg_risk
        )

        logger.info(
            "TASK.LISTEN.SWEEP_SUCCESS",
            msg="扫单执行成功",
            extra={
                "task_id": task.id,
                "sweep_result": sweep_result
            }
        )

        return {
            "status": "completed",
            "message": "扫单执行成功，订单已成交",
            "sweep_result": sweep_result,
            "next_stage": TaskStage.LISTEN.value,
            "next_status": TaskStatus.FINISHED.value
        }

    except Exception as e:
        error_msg = f"扫单执行失败: {str(e)}"
        logger.error(
            "TASK.LISTEN.SWEEP_EXCEPTION",
            msg=error_msg,
            error_code="E-LISTEN-006",
            extra={"task_id": task.id, "exception": str(e)}
        )
        return {"status": "failed", "message": error_msg}


# ==================== 前端触发任务的Huey包装器 ====================

@huey.task()
def execute_scheduled_task(task_id: int):
    """
    Huey任务: 执行定时任务

    参数:
        task_id: 定时任务ID
    """
    from .dynamic_scheduler import get_scheduler

    with TraceContext() as trace_id:
        logger.info(
            "HUEY.SCHEDULED_TASK.START",
            msg=f"开始执行定时任务: {task_id}",
            extra={"task_id": task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务信息
            task = db.get_scheduled_task(task_id)
            if not task:
                logger.error(
                    "HUEY.SCHEDULED_TASK.NOT_FOUND",
                    msg=f"定时任务不存在: {task_id}",
                    error_code="E-HUEY-SCHEDULED-001",
                    extra={"task_id": task_id},
                    trace_id=trace_id
                )
                return {"success": False, "message": f"任务不存在: {task_id}"}

            # 获取调度器并执行任务
            scheduler = get_scheduler()
            scheduler._execute_task(task)

            logger.info(
                "HUEY.SCHEDULED_TASK.SUCCESS",
                msg=f"定时任务执行完成: {task.name}",
                extra={"task_id": task_id, "task_name": task.name},
                trace_id=trace_id
            )

            return {"success": True, "message": f"任务 {task.name} 执行成功"}

        except Exception as e:
            logger.error(
                "HUEY.SCHEDULED_TASK.ERROR",
                msg=f"定时任务执行失败: {task_id}",
                error_code="E-HUEY-SCHEDULED-002",
                extra={"task_id": task_id, "error": str(e)},
                trace_id=trace_id
            )
            raise


@huey.task()
def execute_poll_analysis_once(async_task_id: int):
    """
    Huey任务: 手动轮询一次分析任务结果

    参数:
        async_task_id: 分析任务ID
    """
    from ..ai_analysis.gpt_api import parse_cookie_string, get_result
    from ..ai_analysis.analysis_tasks import validate_analysis_result, AnalysisStatus
    from ..sys_configs.token_refresher import get_token_refresher, TokenType

    with TraceContext() as trace_id:
        logger.info(
            "HUEY.POLL_ONCE.START",
            msg=f"开始手动轮询分析结果: {async_task_id}",
            extra={"async_task_id": async_task_id},
            trace_id=trace_id
        )

        try:
            # 获取任务
            task = db.get_async_task(async_task_id)
            if not task:
                logger.error(
                    "HUEY.POLL_ONCE.NOT_FOUND",
                    msg=f"任务不存在: {async_task_id}",
                    error_code="E-HUEY-POLL-001",
                    extra={"async_task_id": async_task_id},
                    trace_id=trace_id
                )
                return {"success": False, "message": f"任务不存在: {async_task_id}"}

            # 检查conversation_id
            conversation_id = task.result.get("conversation_id")
            if not conversation_id:
                return {"success": False, "message": "缺少conversation_id"}

            # 获取Cookie
            token_refresher = get_token_refresher()
            access_token_status = token_refresher.get_token_status(TokenType.ACCESS_TOKEN.value)
            auth_token_status = token_refresher.get_token_status(TokenType.AUTH_TOKEN.value)

            if not access_token_status or not auth_token_status:
                return {"success": False, "message": "未配置token"}

            if access_token_status.get('is_expired') or auth_token_status.get('is_expired'):
                return {"success": False, "message": "token已过期"}

            # 构建cookie_string
            access_token = access_token_status.get('token_value')
            auth_token = auth_token_status.get('token_value')
            cookie_string = f"__Secure-access_token={access_token};__Secure-auth_token={auth_token}"
            cookies_dict = parse_cookie_string(cookie_string)

            # 执行轮询
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
                    task.status = TaskStatus.FINISHED
                    db.update_async_task(task)

                    logger.info(
                        "HUEY.POLL_ONCE.SUCCESS",
                        msg=f"轮询成功，分析完成: {async_task_id}",
                        extra={
                            "async_task_id": async_task_id,
                            "market_count": len(parsed_json)
                        },
                        trace_id=trace_id
                    )

                    # 自动拆分为decision任务
                    from ..ai_analysis.analysis_tasks import split_analysis_task
                    try:
                        split_result = split_analysis_task(async_task_id)
                        if split_result.get("success"):
                            logger.info(
                                "HUEY.POLL_ONCE.AUTO_SPLIT_SUCCESS",
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
                                "HUEY.POLL_ONCE.AUTO_SPLIT_FAILED",
                                msg=f"自动拆分失败: {split_result.get('message')}",
                                error_code="E-POLL-ONCE-003",
                                extra={
                                    "async_task_id": async_task_id,
                                    "error": split_result.get("message")
                                },
                                trace_id=trace_id
                            )
                    except Exception as split_error:
                        logger.error(
                            "HUEY.POLL_ONCE.AUTO_SPLIT_EXCEPTION",
                            msg=f"自动拆分异常: {str(split_error)}",
                            error_code="E-POLL-ONCE-004",
                            extra={
                                "async_task_id": async_task_id,
                                "exception": str(split_error)
                            },
                            trace_id=trace_id
                        )

                    return {
                        "success": True,
                        "analysis_status": AnalysisStatus.SUCCESS.value,
                        "has_result": True,
                        "analysis_result": parsed_json,
                        "market_ids": list(parsed_json.keys())
                    }
                else:
                    # 验证失败
                    task.result["analysis_status"] = AnalysisStatus.FAILED.value
                    task.result["error"] = "AI返回格式验证失败"
                    task.status = TaskStatus.FAILED
                    db.update_async_task(task)

                    return {
                        "success": False,
                        "analysis_status": AnalysisStatus.FAILED.value,
                        "error": "AI返回格式验证失败"
                    }
            else:
                # 仍在思考中
                return {
                    "success": True,
                    "analysis_status": AnalysisStatus.POLLING.value,
                    "has_result": False
                }

        except Exception as e:
            logger.error(
                "HUEY.POLL_ONCE.ERROR",
                msg=f"轮询失败: {async_task_id}",
                error_code="E-HUEY-POLL-002",
                extra={"async_task_id": async_task_id, "error": str(e)},
                trace_id=trace_id
            )
            raise


# ==================== GPT额度相关定时任务 ====================

@huey.task()
def scheduled_gpt_quota_check():
    """
    定时检查GPT额度恢复任务

    由定时任务调度器调用，检查等待额度的任务并在额度恢复后重新提交
    """
    from ..ai_analysis.analysis_tasks import check_quota_recovery

    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULED.GPT_QUOTA_CHECK.START",
            msg="开始执行定时GPT额度检查",
            trace_id=trace_id
        )

        try:
            # 调用额度恢复检查任务
            check_quota_recovery()

            logger.info(
                "SCHEDULED.GPT_QUOTA_CHECK.SUCCESS",
                msg="定时GPT额度检查完成",
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "SCHEDULED.GPT_QUOTA_CHECK.ERROR",
                msg=f"定时GPT额度检查失败: {str(e)}",
                error_code="E-SCHEDULED-GPT-001",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.task()
def scheduled_gpt_quota_cleanup():
    """
    定时清理GPT请求记录任务

    由定时任务调度器调用，清理30天前的GPT请求记录
    """
    from ..ai_analysis.analysis_tasks import cleanup_old_quota_records

    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULED.GPT_QUOTA_CLEANUP.START",
            msg="开始执行定时GPT请求记录清理",
            trace_id=trace_id
        )

        try:
            # 清理30天前的记录
            cleanup_old_quota_records(days=30)

            logger.info(
                "SCHEDULED.GPT_QUOTA_CLEANUP.SUCCESS",
                msg="定时GPT请求记录清理完成",
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "SCHEDULED.GPT_QUOTA_CLEANUP.ERROR",
                msg=f"定时GPT请求记录清理失败: {str(e)}",
                error_code="E-SCHEDULED-GPT-002",
                extra={"error": str(e)},
                trace_id=trace_id
            )


@huey.task()
def scheduled_auto_decision():
    """
    定时自动决策任务

    每2小时执行一次，如果待决策市场列表少于10个则跳过
    使用与 /api/tasks/decision/execute 相同的决策逻辑
    """
    from ..auto_decision import allocate, SimpleMarket
    from ..purse import get_purse
    import json

    with TraceContext() as trace_id:
        logger.info(
            "SCHEDULED.AUTO_DECISION.START",
            msg="开始执行定时自动决策",
            trace_id=trace_id
        )

        try:
            # 1. 获取所有待决策任务
            pending_tasks = db.query_async_tasks(
                stage=TaskStage.DECISION,
                status=TaskStatus.WAITING,
                limit=100
            )

            # 检查待决策任务数量
            # if len(pending_tasks) < 10:
            #     logger.info(
            #         "SCHEDULED.AUTO_DECISION.SKIP",
            #         msg=f"待决策任务数量不足10个({len(pending_tasks)}个)，跳过本次执行",
            #         extra={"pending_count": len(pending_tasks)},
            #         trace_id=trace_id
            #     )
            #     return

            logger.info(
                "SCHEDULED.AUTO_DECISION.PENDING_TASKS",
                msg=f"待决策任务: {len(pending_tasks)}个",
                extra={"pending_count": len(pending_tasks)},
                trace_id=trace_id
            )

            # 2. 构建Market列表和任务映射
            markets = []
            task_map = {}  # market_id -> task
            now_day = 0  # 当前天索引

            for task in pending_tasks:
                metadata = task.metadata
                market_data = metadata.get('market')
                analysis_data = metadata.get('analysis')

                # 严格验证：不使用默认值
                if not market_data:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少market数据，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-001",
                        extra={"task_id": task.id},
                        trace_id=trace_id
                    )
                    continue

                if not analysis_data:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少analysis数据，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-002",
                        extra={"task_id": task.id},
                        trace_id=trace_id
                    )
                    continue

                market_id = market_data.get('id')
                if not market_id:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少market_id，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-003",
                        extra={"task_id": task.id},
                        trace_id=trace_id
                    )
                    continue

                # 严格解析outcome_prices - 不使用默认值
                outcome_prices_str = market_data.get('outcome_prices')
                if not outcome_prices_str:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少outcome_prices，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-004",
                        extra={"task_id": task.id, "market_id": market_id},
                        trace_id=trace_id
                    )
                    continue

                try:
                    if isinstance(outcome_prices_str, str):
                        outcome_prices = json.loads(outcome_prices_str)
                    else:
                        outcome_prices = outcome_prices_str

                    if not outcome_prices or len(outcome_prices) < 1:
                        raise ValueError("outcome_prices为空或长度不足")

                    yes_price = float(outcome_prices[0])
                except Exception as e:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"解析outcome_prices失败，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-005",
                        extra={"task_id": task.id, "market_id": market_id, "error": str(e)},
                        trace_id=trace_id
                    )
                    continue

                # 严格解析end_date计算结算天数 - 不使用默认值
                end_date_str = market_data.get('end_date')
                if not end_date_str:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少end_date，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-006",
                        extra={"task_id": task.id, "market_id": market_id},
                        trace_id=trace_id
                    )
                    continue

                try:
                    from datetime import datetime as dt
                    end_date = dt.strptime(end_date_str, "%Y-%m-%dT%H:%M:%SZ")
                    tau = max(1, (end_date - dt.now()).days)
                except Exception as e:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"解析end_date失败，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-007",
                        extra={"task_id": task.id, "market_id": market_id, "error": str(e)},
                        trace_id=trace_id
                    )
                    continue

                # 严格获取分析结果 - 不使用默认值
                p_predict = analysis_data.get('p')  # AI预测的YES概率
                p_no_predict = analysis_data.get('n')  # AI预测的NO概率
                a = analysis_data.get('a')  # 风险因子

                if p_predict is None:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少分析结果p，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-008",
                        extra={"task_id": task.id, "market_id": market_id},
                        trace_id=trace_id
                    )
                    continue

                if p_no_predict is None:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少分析结果n，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-009",
                        extra={"task_id": task.id, "market_id": market_id},
                        trace_id=trace_id
                    )
                    continue

                if a is None:
                    logger.error(
                        "SCHEDULED.AUTO_DECISION.SKIP_TASK",
                        msg=f"任务缺少风险因子a，跳过: {task.id}",
                        error_code="E-SCHEDULED-DECISION-010",
                        extra={"task_id": task.id, "market_id": market_id},
                        trace_id=trace_id
                    )
                    continue

                # 使用风险因子a进行概率放缩
                # 公式: p = pmarket + a*(p_predict - pmarket)
                p_yes = yes_price + a * (p_predict - yes_price)
                p_no = (1.0 - yes_price) + a * (p_no_predict - (1.0 - yes_price))

                logger.info(
                    "SCHEDULED.AUTO_DECISION.PROB_SCALING",
                    msg=f"概率放缩: {task.id}",
                    extra={
                        "task_id": task.id,
                        "market_id": market_id,
                        "pmarket": yes_price,
                        "p_predict": p_predict,
                        "a": a,
                        "p_scaled": p_yes,
                        "p_no_predict": p_no_predict,
                        "p_no_scaled": p_no
                    },
                    trace_id=trace_id
                )

                # 创建SimpleMarket对象
                market = SimpleMarket(
                    id=market_id,
                    m=yes_price,
                    p_yes=p_yes,
                    d=now_day + tau,  # 结算日期 = 当前天 + 剩余天数
                    p_no=p_no
                )
                markets.append(market)
                task_map[market_id] = task

            if not markets:
                logger.warn(
                    "SCHEDULED.AUTO_DECISION.NO_VALID_MARKETS",
                    msg="没有有效的市场数据",
                    trace_id=trace_id
                )
                return

            logger.info(
                "SCHEDULED.AUTO_DECISION.MARKETS",
                msg=f"待决策市场: {len(markets)}个",
                extra={"market_count": len(markets), "market_ids": [m.id for m in markets]},
                trace_id=trace_id
            )

            # 3. 从purse获取资金状态并调用仓位分配
            purse = get_purse()
            wealth = purse.get_total_fund()
            locked_value = purse.get_locked_fund()

            logger.info(
                "SCHEDULED.AUTO_DECISION.PURSE_STATUS",
                msg="从purse获取资金状态",
                extra={"wealth": wealth, "locked_value": locked_value},
                trace_id=trace_id
            )

            # 策略参数
            theta_params = {
                "lambda_time": 0.0,   # 久期贴现系数（0表示不贴现）
                "c_fraction": 0.5,    # 分数Kelly系数（0.5表示半Kelly）
                "f_cap": 0.95         # 单市场仓位上限
            }
            k = 0.6  # 最大锁仓占比

            allocations = allocate(
                markets_today=markets,
                wealth=wealth,
                locked_value_now=locked_value,
                now_day=now_day,
                k=k,
                theta=theta_params
            )

            # 4. 将分配结果写回任务（过滤投入金额少于5*side_price的decision）
            allocation_map = {alloc.id: alloc for alloc in allocations}

            processed_count = 0
            filtered_count = 0  # 被过滤掉的任务数

            for market_id, task in task_map.items():
                alloc = allocation_map.get(market_id)
                from ..mark import mark
                from ..types import Market
                market_info = task.metadata.get("market")
                mark_result = mark(market_info,alloc)
                #将 mark_result添加到task.metadata
                task.metadata["mark"] = mark_result

                if alloc:
                    # 有分配结果，检查投入金额是否满足最小阈值
                    side_price = alloc.price  # 交易方向的价格
                    min_invest = 5.0 * side_price  # 最小投入金额阈值

                    if alloc.invest < min_invest:
                        # 投入金额不足，过滤掉
                        task.result = {
                            'decision': 'skip',
                            'reason': f'投入金额${alloc.invest:.2f}低于最小阈值${min_invest:.2f} (5*{side_price:.2f})',
                            'wealth': wealth,
                            'filtered': True,
                            'original_allocation': {
                                'side': alloc.side,
                                'dollars': alloc.invest,
                                'shares': alloc.shares,
                                'cost': alloc.price
                            }
                        }
                        filtered_count += 1

                        logger.info(
                            "SCHEDULED.AUTO_DECISION.FILTERED",
                            msg=f"过滤低投入任务: {task.id}",
                            extra={
                                "task_id": task.id,
                                "market_id": market_id,
                                "invest": alloc.invest,
                                "min_invest": min_invest,
                                "side_price": side_price
                            },
                            trace_id=trace_id
                        )
                    else:
                        # 投入金额满足要求
                        # 计算评分（基于投资金额占总资金的比例）
                        score = alloc.invest / wealth if wealth > 0 else 0.0
                        task.result = {
                            'decision': 'trade',
                            'allocation': {
                                'side': alloc.side,
                                'score': score,
                                'fraction_of_gross': alloc.f,
                                'dollars': alloc.invest,
                                'shares': alloc.shares,
                                'cost': alloc.price
                            },
                            'wealth': wealth,
                            'locked_value': locked_value,
                            'mark': mark_result
                        }
                else:
                    # 无分配（不值得交易）
                    task.result = {
                        'decision': 'skip',
                        'reason': '根据Kelly准则，当前市场不值得交易',
                        'wealth': wealth
                    }
                task.stage = TaskStage.TRADE
                task.status = TaskStatus.WAITING
                db.update_async_task(task)
                processed_count += 1

            logger.info(
                "SCHEDULED.AUTO_DECISION.SUCCESS",
                msg=f"定时自动决策完成: {processed_count}个任务, 过滤{filtered_count}个低投入任务",
                extra={
                    "processed_count": processed_count,
                    "allocation_count": len(allocations),
                    "filtered_count": filtered_count,
                    "actual_trade_count": processed_count - filtered_count - (len(task_map) - len(allocations))
                },
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "SCHEDULED.AUTO_DECISION.ERROR",
                msg=f"定时自动决策失败: {str(e)}",
                error_code="E-SCHEDULED-DECISION-011",
                extra={"error": str(e)},
                trace_id=trace_id
            )

