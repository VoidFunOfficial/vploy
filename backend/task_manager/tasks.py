"""
异步任务处理模块

实现基于Huey的异步任务队列和任务路由机制。
"""

from typing import Optional, Dict, Any, Callable
from huey import SqliteHuey
from datetime import datetime

from .config import get_config
from .models import AsyncTask, TaskStage, TaskStatus, TaskDatabase
from ..vlogger import get_logger, TraceContext


# 初始化Huey任务队列
config = get_config()
huey = SqliteHuey(
    filename=config.huey_db_path,
    immediate=config.immediate,
    utc=True
)

# 初始化日志记录器
logger = get_logger("task_manager")

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
    from ..polymarket_api.gamma_markets import GammaMarketsAPI
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
    from ..polymarket_api.gamma_markets import GammaMarketsAPI, event_summary_readableforai
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
    return {"status": "ready", "message": "准备开始交易"}


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
    from ..position_listener.database import get_db
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

        # 调用auto_trade_exec.trade()进行自动挂单
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
            msg="交易执行成功",
            extra={
                "task_id": task.id,
                "market_id": market.get("id"),
                "trade_result": trade_result
            }
        )

        # 添加到仓位监听
        try:
            db = get_db()

            # 准备marks信息
            marks = task.metadata.get("marks", [])
            marks_str = json.dumps(marks) if marks else None

            # 添加仓位监听记录
            position_id = db.add_position(
                market_id=market.get("id"),
                buy_price=cost,  # 买入价格
                buy_side=side,  # 买入方向 (YES/NO)
                marks=marks_str,  # 标记信息
                shares=shares,  # 持仓份额
                threshold_config=None  # 暂不设置阈值配置
            )

            logger.info(
                "TASK.TRADE.POSITION_ADDED",
                msg="已添加到仓位监听",
                extra={
                    "task_id": task.id,
                    "position_id": position_id,
                    "market_id": market.get("id"),
                    "buy_price": cost,
                    "buy_side": side,
                    "shares": shares
                }
            )

            # 返回成功结果
            return {
                "status": "traded",
                "message": "交易完成并已添加到仓位监听",
                "trade_result": trade_result,
                "position_id": position_id,
                "market_id": market.get("id"),
                "market_question": market.get("question"),
                "side": side,
                "dollars": dollars,
                "cost": cost,
                "shares": shares
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
    # TODO: 实现监听等待逻辑
    return {"status": "ready", "message": "准备开始监听"}


@register_handler(TaskStage.LISTEN, TaskStatus.PROCESSING)
def handle_listen_processing(task: AsyncTask) -> Dict[str, Any]:
    """
    处理LISTEN阶段的PROCESSING状态任务

    参数:
        task: 任务实例

    返回:
        Dict[str, Any]: 处理结果
    """
    logger.info(
        "TASK.LISTEN.PROCESSING",
        msg="处理LISTEN阶段任务",
        extra={"task_id": task.id}
    )
    # TODO: 实现监听处理逻辑
    return {"status": "listening", "message": "监听中"}

