"""
异步任务管理路由

提供异步任务的查询、状态更新、删除等管理接口
"""

from flask import Blueprint, request, jsonify
from ...task_manager import (
    submit_task,
    AsyncTask,
    TaskStage,
    TaskStatus,
    TaskDatabase
)
from ...sys_configs.global_event_reg import vlogger

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')
logger = vlogger
db = TaskDatabase()


@tasks_bp.route('/', methods=['GET'])
def get_tasks():
    """
    获取异步任务列表

    查询参数:
        stage: 任务阶段 (mark/analysis/decision/trade/listen)
        status: 任务状态 (waiting/processing/success/failed/cancelled)
        limit: 返回数量限制 (默认100)
        offset: 偏移量 (默认0) - 注意: 当前仅用于前端分页显示,后端暂不支持
    """
    try:
        stage_param = request.args.get('stage')
        status_param = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        # 解析stage参数
        stage = None
        if stage_param:
            try:
                stage = TaskStage(stage_param)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的任务阶段: {stage_param}'
                }), 400

        # 解析status参数
        status = None
        if status_param:
            try:
                status = TaskStatus(status_param)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的任务状态: {status_param}'
                }), 400

        # 查询任务列表 (注意: query_async_tasks 不支持 offset 参数)
        # 我们查询更多数据然后在内存中分页
        all_tasks = db.query_async_tasks(
            stage=stage,
            status=status,
            limit=limit + offset  # 查询足够的数据
        )

        # 应用偏移量进行分页
        tasks = all_tasks[offset:offset + limit] if offset < len(all_tasks) else []

        # 转换为字典格式（使用to_dict方法以包含扩展信息）
        tasks_data = []
        for task in tasks:
            tasks_data.append(task.to_dict())

        return jsonify({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'total': len(tasks_data),
                'offset': offset,
                'limit': limit
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.LIST.ERROR",
            msg="获取任务列表失败",
            error_code="E-TASKS-API-001",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务详情"""
    try:
        task = db.get_async_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': task.to_dict()
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.GET.ERROR",
            msg=f"获取任务失败: {task_id}",
            error_code="E-TASKS-API-002",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/', methods=['POST'])
def create_task():
    """
    创建异步任务
    
    请求体:
        stage: 任务阶段 (必填)
        status: 任务状态 (默认waiting)
        metadata: 任务元数据 (可选)
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('stage'):
            return jsonify({
                'success': False,
                'message': '任务阶段不能为空'
            }), 400
        
        # 解析stage
        try:
            stage = TaskStage(data['stage'])
        except ValueError:
            return jsonify({
                'success': False,
                'message': f'无效的任务阶段: {data["stage"]}'
            }), 400
        
        # 解析status
        status = TaskStatus.WAITING
        if data.get('status'):
            try:
                status = TaskStatus(data['status'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的任务状态: {data["status"]}'
                }), 400
        
        # 创建任务
        task = AsyncTask(
            stage=stage,
            status=status,
            metadata=data.get('metadata', {})
        )
        
        task_id = submit_task(task)
        
        logger.info(
            "TASKS.API.CREATE.SUCCESS",
            msg=f"创建任务成功: {stage.value}",
            extra={"task_id": task_id, "stage": stage.value}
        )
        
        return jsonify({
            'success': True,
            'message': '创建任务成功',
            'data': {'task_id': task_id}
        }), 201
        
    except Exception as e:
        logger.error(
            "TASKS.API.CREATE.ERROR",
            msg="创建任务失败",
            error_code="E-TASKS-API-003",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'创建任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """
    更新任务状态

    请求体:
        status: 任务状态 (可选)
        result: 任务结果 (可选)
        error_msg: 错误信息 (可选)
        metadata: 任务元数据 (可选)

    特殊逻辑:
        当状态从waiting变为processing时,自动提交任务到Huey队列进行处理

    注意:
        仅更新metadata或result时不会触发任务状态变更和队列提交
    """
    try:
        data = request.get_json()

        # 获取现有任务
        task = db.get_async_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        # 记录原始状态
        old_status = task.status

        # 更新字段
        if 'status' in data:
            try:
                task.status = TaskStatus(data['status'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的任务状态: {data["status"]}'
                }), 400

        if 'result' in data:
            task.result = data['result']

        if 'error_msg' in data:
            task.error_msg = data['error_msg']

        if 'metadata' in data:
            task.metadata = data['metadata']

        # 保存更新
        db.update_async_task(task)

        # 特殊处理: 仅当明确更新了status字段且状态从waiting变为processing时,才提交到Huey队列
        if 'status' in data and old_status == TaskStatus.WAITING and task.status == TaskStatus.PROCESSING:
            from ...task_manager import process_async_task

            logger.info(
                "TASKS.API.UPDATE.SUBMIT_TO_HUEY",
                msg=f"任务状态从waiting变为processing,提交到Huey队列: {task_id}",
                extra={
                    "task_id": task_id,
                    "stage": task.stage.value,
                    "old_status": old_status.value,
                    "new_status": task.status.value
                }
            )

            # 提交到Huey队列进行处理
            process_async_task(task_id)

        logger.info(
            "TASKS.API.UPDATE.SUCCESS",
            msg=f"更新任务成功: {task_id}",
            extra={"task_id": task_id, "status": task.status.value}
        )

        return jsonify({
            'success': True,
            'message': '更新任务成功'
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.UPDATE.ERROR",
            msg=f"更新任务失败: {task_id}",
            error_code="E-TASKS-API-004",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'更新任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        # 获取任务信息
        task = db.get_async_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        # 删除任务
        db.delete_async_task(task_id)

        logger.info(
            "TASKS.API.DELETE.SUCCESS",
            msg=f"删除任务成功: {task_id}",
            extra={"task_id": task_id}
        )

        return jsonify({
            'success': True,
            'message': '删除任务成功'
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.DELETE.ERROR",
            msg=f"删除任务失败: {task_id}",
            error_code="E-TASKS-API-005",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'删除任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/batch-delete', methods=['POST'])
def batch_delete_tasks():
    """批量删除任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({
                'success': False,
                'message': '未提供任务ID列表'
            }), 400

        if not isinstance(task_ids, list):
            return jsonify({
                'success': False,
                'message': '任务ID列表格式错误'
            }), 400

        # 批量删除任务
        deleted_count = 0
        failed_ids = []

        for task_id in task_ids:
            try:
                task = db.get_async_task(task_id)
                if task:
                    db.delete_async_task(task_id)
                    deleted_count += 1
                else:
                    failed_ids.append(task_id)
            except Exception as e:
                logger.error(
                    "TASKS.API.BATCH_DELETE.ITEM_ERROR",
                    msg=f"删除任务失败: {task_id}",
                    error_code="E-TASKS-API-006",
                    extra={"task_id": task_id, "error": str(e)}
                )
                failed_ids.append(task_id)

        logger.info(
            "TASKS.API.BATCH_DELETE.SUCCESS",
            msg=f"批量删除任务完成: 成功{deleted_count}个, 失败{len(failed_ids)}个",
            extra={
                "deleted_count": deleted_count,
                "failed_count": len(failed_ids),
                "failed_ids": failed_ids
            }
        )

        return jsonify({
            'success': True,
            'message': f'批量删除完成: 成功{deleted_count}个, 失败{len(failed_ids)}个',
            'data': {
                'deleted_count': deleted_count,
                'failed_count': len(failed_ids),
                'failed_ids': failed_ids
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.BATCH_DELETE.ERROR",
            msg="批量删除任务失败",
            error_code="E-TASKS-API-007",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'批量删除任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """
    重试任务

    将失败或已取消的任务重新打回到waiting状态并重新提交到队列
    """
    try:
        # 获取任务
        task = db.get_async_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        # 检查任务状态是否允许重试
        if task.status not in [TaskStatus.FAILED, TaskStatus.FINISHED]:
            return jsonify({
                'success': False,
                'message': f'只有失败或已完成的任务才能重试，当前状态: {task.status.value}'
            }), 400

        # 记录原始状态
        old_status = task.status

        # 重置任务状态
        task.status = TaskStatus.WAITING
        task.error_msg = None
        task.result = None

        # 保存更新
        db.update_async_task(task)

        # 提交到Huey队列重新处理
        from ...task_manager import process_async_task

        logger.info(
            "TASKS.API.RETRY.SUBMIT",
            msg=f"重试任务，提交到Huey队列: {task_id}",
            extra={
                "task_id": task_id,
                "stage": task.stage.value,
                "old_status": old_status.value,
                "new_status": task.status.value
            }
        )

        # 提交到Huey队列进行处理
        process_async_task(task_id)

        logger.info(
            "TASKS.API.RETRY.SUCCESS",
            msg=f"重试任务成功: {task_id}",
            extra={"task_id": task_id}
        )

        return jsonify({
            'success': True,
            'message': '任务已重新提交'
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.RETRY.ERROR",
            msg=f"重试任务失败: {task_id}",
            error_code="E-TASKS-API-008",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'重试任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>/analysis-status', methods=['GET'])
def get_analysis_status(task_id):
    """
    获取分析任务的详细状态

    返回:
        {
            "success": true,
            "data": {
                "analysis_status": "polling",
                "conversation_id": "conv_abc123",
                "market_count": 5,
                "has_result": false
            }
        }
    """
    try:
        task = db.get_async_task(task_id)

        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        if task.stage != TaskStage.ANALYSIS:
            return jsonify({
                'success': False,
                'message': f'任务不是分析阶段任务: {task.stage.value}'
            }), 400

        # 获取分析状态信息
        analysis_status = task.result.get("analysis_status")
        conversation_id = task.result.get("conversation_id")
        market_ids = task.result.get("market_ids", [])
        has_result = bool(task.result.get("analysis_result"))

        return jsonify({
            'success': True,
            'data': {
                'analysis_status': analysis_status,
                'conversation_id': conversation_id,
                'market_count': len(market_ids) if market_ids else 0,
                'market_ids': market_ids,
                'has_result': has_result,
                'error': task.result.get("error")
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.ANALYSIS_STATUS.ERROR",
            msg=f"获取分析状态失败: {task_id}",
            error_code="E-TASKS-API-009",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取分析状态失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>/analysis-result', methods=['GET'])
def get_analysis_result(task_id):
    """
    获取分析任务的结果

    返回:
        {
            "success": true,
            "data": {
                "analysis_result": {
                    "68095": {
                        "p": 0.6,
                        "a": 0.3,
                        "reasons_p": ["原因1"],
                        "reasons_n": ["原因1"]
                    }
                },
                "market_ids": ["68095"],
                "raw_response": "..."
            }
        }
    """
    try:
        task = db.get_async_task(task_id)

        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        if task.stage != TaskStage.ANALYSIS:
            return jsonify({
                'success': False,
                'message': f'任务不是分析阶段任务: {task.stage.value}'
            }), 400

        # 获取分析结果
        analysis_result = task.result.get("analysis_result")

        if not analysis_result:
            return jsonify({
                'success': False,
                'message': '分析结果尚未生成'
            }), 404

        return jsonify({
            'success': True,
            'data': {
                'analysis_result': analysis_result,
                'market_ids': task.result.get("market_ids", []),
                'raw_response': task.result.get("raw_response"),
                'conversation_id': task.result.get("conversation_id")
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.ANALYSIS_RESULT.ERROR",
            msg=f"获取分析结果失败: {task_id}",
            error_code="E-TASKS-API-010",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取分析结果失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>/poll-once', methods=['POST'])
def poll_analysis_once(task_id):
    """
    手动轮询一次分析任务的结果

    适用场景:
    - 分析任务处于polling状态时，手动触发一次结果查询
    - 用于调试或加速获取结果

    返回:
        {
            "success": true,
            "message": "轮询任务已提交到队列"
        }
    """
    try:
        from ...task_manager import execute_poll_analysis_once

        # 获取任务
        task = db.get_async_task(task_id)

        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        if task.stage != TaskStage.ANALYSIS:
            return jsonify({
                'success': False,
                'message': f'任务不是分析阶段任务: {task.stage.value}'
            }), 400

        # 检查任务是否处于可轮询状态
        analysis_status = task.result.get("analysis_status")
        if analysis_status not in ["polling", "requesting"]:
            return jsonify({
                'success': False,
                'message': f'任务当前状态不支持手动轮询: {analysis_status}'
            }), 400

        # 检查conversation_id
        conversation_id = task.result.get("conversation_id")
        if not conversation_id:
            return jsonify({
                'success': False,
                'message': '缺少conversation_id，无法轮询结果'
            }), 400

        logger.info(
            "TASKS.API.POLL_ONCE.START",
            msg=f"提交轮询任务到Huey队列: {task_id}",
            extra={"task_id": task_id, "conversation_id": conversation_id}
        )

        # 提交到Huey队列异步执行
        execute_poll_analysis_once(task_id)

        logger.info(
            "TASKS.API.POLL_ONCE.SUBMITTED",
            msg=f"轮询任务已提交到Huey队列: {task_id}",
            extra={"task_id": task_id}
        )

        return jsonify({
            'success': True,
            'message': '轮询任务已提交到队列，将在后台异步执行'
        }), 202

    except Exception as e:
        logger.error(
            "TASKS.API.POLL_ONCE.ERROR",
            msg=f"提交轮询任务失败: {task_id}",
            error_code="E-TASKS-API-013",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'提交轮询任务失败: {str(e)}'
        }), 500





@tasks_bp.route('/decision/pending', methods=['GET'])
def get_pending_decision_tasks():
    """
    获取所有待决策的任务

    返回:
        {
            "success": true,
            "data": {
                "tasks": [...],  # 待决策任务列表
                "total": 5       # 总数
            }
        }
    """
    try:
        # 查询decision阶段且waiting状态的任务
        tasks = db.query_async_tasks(
            stage=TaskStage.DECISION,
            status=TaskStatus.WAITING,
            limit=100
        )

        # 转换为字典格式
        tasks_data = [task.to_dict() for task in tasks]

        logger.info(
            "TASKS.API.DECISION.PENDING",
            msg=f"获取待决策任务: {len(tasks_data)}个",
            extra={"count": len(tasks_data)}
        )

        return jsonify({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'total': len(tasks_data)
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.DECISION.PENDING.ERROR",
            msg="获取待决策任务失败",
            error_code="E-TASKS-API-015",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取待决策任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/trade/pending', methods=['GET'])
def get_pending_trade_tasks():
    """
    获取所有待交易的任务

    返回:
        {
            "success": true,
            "data": {
                "tasks": [...],  # 待交易任务列表
                "total": 5       # 总数
            }
        }
    """
    try:
        # 查询trade阶段且waiting状态的任务
        tasks = db.query_async_tasks(
            stage=TaskStage.TRADE,
            status=TaskStatus.WAITING,
            limit=100
        )

        # 转换为字典格式
        tasks_data = [task.to_dict() for task in tasks]

        logger.info(
            "TASKS.API.TRADE.PENDING",
            msg=f"获取待交易任务: {len(tasks_data)}个",
            extra={"count": len(tasks_data)}
        )

        return jsonify({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'total': len(tasks_data)
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.TRADE.PENDING.ERROR",
            msg="获取待交易任务失败",
            error_code="E-TASKS-API-027",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取待交易任务失败: {str(e)}'
        }), 500


@tasks_bp.route('/decision/execute', methods=['POST'])
def execute_decision():
    """
    执行决策处理 - 批量处理所有待决策任务

    处理流程:
    1. 获取所有待决策任务
    2. 提取每个任务的market和analysis数据
    3. 调用position_manager进行仓位分配
    4. 将分配结果写回各任务的result字段
    5. 更新任务状态为finished

    返回:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "processed_count": 5,
                "allocations": [...],  # 仓位分配结果
                "summary": {...}       # 汇总信息
            }
        }
    """
    try:
        from ...auto_decision import allocate, SimpleMarket
        from ...purse import get_purse
        import json

        logger.info(
            "TASKS.API.DECISION.EXECUTE.START",
            msg="开始执行决策处理"
        )

        # 1. 获取所有待决策任务
        pending_tasks = db.query_async_tasks(
            stage=TaskStage.DECISION,
            status=TaskStatus.WAITING,
            limit=100
        )

        if not pending_tasks:
            return jsonify({
                'success': False,
                'message': '没有待决策的任务'
            }), 400

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
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少market数据，跳过: {task.id}",
                    error_code="E-TASKS-API-017",
                    extra={"task_id": task.id}
                )
                continue

            if not analysis_data:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少analysis数据，跳过: {task.id}",
                    error_code="E-TASKS-API-018",
                    extra={"task_id": task.id}
                )
                continue

            market_id = market_data.get('id')
            if not market_id:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少market_id，跳过: {task.id}",
                    error_code="E-TASKS-API-019",
                    extra={"task_id": task.id}
                )
                continue

            # 严格解析outcome_prices - 不使用默认值
            outcome_prices_str = market_data.get('outcome_prices')
            if not outcome_prices_str:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少outcome_prices，跳过: {task.id}",
                    error_code="E-TASKS-API-020",
                    extra={"task_id": task.id, "market_id": market_id}
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
                    "TASKS.API.DECISION.SKIP",
                    msg=f"解析outcome_prices失败，跳过: {task.id}",
                    error_code="E-TASKS-API-021",
                    extra={"task_id": task.id, "market_id": market_id, "error": str(e)}
                )
                continue

            # 严格解析end_date计算结算天数 - 不使用默认值
            end_date_str = market_data.get('end_date')
            if not end_date_str:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少end_date，跳过: {task.id}",
                    error_code="E-TASKS-API-022",
                    extra={"task_id": task.id, "market_id": market_id}
                )
                continue

            try:
                from datetime import datetime
                end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%SZ")
                tau = max(1, (end_date - datetime.now()).days)
            except Exception as e:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"解析end_date失败，跳过: {task.id}",
                    error_code="E-TASKS-API-023",
                    extra={"task_id": task.id, "market_id": market_id, "error": str(e)}
                )
                continue

            # 严格获取分析结果 - 不使用默认值
            p_predict = analysis_data.get('p')  # AI预测的YES概率
            p_no_predict = analysis_data.get('n')  # AI预测的NO概率
            a = analysis_data.get('a')  # 风险因子

            if p_predict is None:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少分析结果p，跳过: {task.id}",
                    error_code="E-TASKS-API-024",
                    extra={"task_id": task.id, "market_id": market_id}
                )
                continue

            if p_no_predict is None:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少分析结果n，跳过: {task.id}",
                    error_code="E-TASKS-API-025",
                    extra={"task_id": task.id, "market_id": market_id}
                )
                continue

            if a is None:
                logger.error(
                    "TASKS.API.DECISION.SKIP",
                    msg=f"任务缺少风险因子a，跳过: {task.id}",
                    error_code="E-TASKS-API-026",
                    extra={"task_id": task.id, "market_id": market_id}
                )
                continue

            # 使用风险因子a进行概率放缩
            # 公式: p = pmarket + a*(p_predict - pmarket)
            p_yes = yes_price + a * (p_predict - yes_price)
            p_no = (1.0 - yes_price) + a * (p_no_predict - (1.0 - yes_price))

            logger.info(
                "TASKS.API.DECISION.PROB_SCALING",
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
                }
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
            return jsonify({
                'success': False,
                'message': '没有有效的市场数据'
            }), 400

        logger.info(
            "TASKS.API.DECISION.MARKETS",
            msg=f"待决策市场: {len(markets)}个",
            extra={"market_count": len(markets), "market_ids": [m.id for m in markets]}
        )

        # 3. 从purse获取资金状态并调用仓位分配
        purse = get_purse()
        wealth = purse.get_total_fund()
        locked_value = purse.get_locked_fund()

        logger.info(
            "TASKS.API.DECISION.PURSE_STATUS",
            msg="从purse获取资金状态",
            extra={"wealth": wealth, "locked_value": locked_value}
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
                        "TASKS.API.DECISION.FILTERED",
                        msg=f"过滤低投入任务: {task.id}",
                        extra={
                            "task_id": task.id,
                            "market_id": market_id,
                            "invest": alloc.invest,
                            "min_invest": min_invest,
                            "side_price": side_price
                        }
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
                        'locked_value': locked_value
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
            "TASKS.API.DECISION.EXECUTE.SUCCESS",
            msg=f"决策处理完成: {processed_count}个任务, 过滤{filtered_count}个低投入任务",
            extra={
                "processed_count": processed_count,
                "allocation_count": len(allocations),
                "filtered_count": filtered_count,
                "actual_trade_count": processed_count - filtered_count - (len(task_map) - len(allocations))
            }
        )

        return jsonify({
            'success': True,
            'message': f'决策处理完成，处理了{processed_count}个任务，过滤了{filtered_count}个低投入任务',
            'data': {
                'processed_count': processed_count,
                'filtered_count': filtered_count,
                'allocations': [a.to_dict() for a in allocations],
                'summary': {
                    'total_tasks': len(pending_tasks),
                    'valid_markets': len(markets),
                    'tradable_markets': len(allocations),
                    'filtered_markets': filtered_count,
                    'actual_trade_markets': len([a for a in allocations if a.invest >= 5.0 * a.price]),
                    'wealth': wealth,
                    'locked_value': locked_value
                }
            }
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.DECISION.EXECUTE.ERROR",
            msg="决策处理失败",
            error_code="E-TASKS-API-016",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'决策处理失败: {str(e)}'
        }), 500


@tasks_bp.route('/gpt-quota', methods=['GET'])
def get_gpt_quota_status():
    """
    获取GPT请求额度状态

    返回:
        {
            "success": true,
            "data": {
                "allowed": true,
                "reason": "",
                "usage": {
                    "6h": {"current": 5, "limit": 30, "remaining": 25},
                    "72h": {"current": 15, "limit": 180, "remaining": 165}
                },
                "next_available": null,
                "limits": [
                    {"hours": 6, "max_requests": 30},
                    {"hours": 72, "max_requests": 180}
                ]
            }
        }
    """
    try:
        from ...ai_analysis.analysis_tasks import get_quota_status

        quota_status = get_quota_status()

        return jsonify({
            'success': True,
            'data': quota_status
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.GPT_QUOTA.ERROR",
            msg="获取GPT额度状态失败",
            error_code="E-TASKS-API-028",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取GPT额度状态失败: {str(e)}'
        }), 500


@tasks_bp.route('/gpt-quota/cleanup', methods=['POST'])
def cleanup_gpt_quota_records():
    """
    清理旧的GPT请求记录

    请求体:
        days: 保留天数 (默认30天)
    """
    try:
        from ...ai_analysis.analysis_tasks import cleanup_old_quota_records

        data = request.get_json() or {}
        days = data.get('days', 30)

        if not isinstance(days, int) or days <= 0:
            return jsonify({
                'success': False,
                'message': '保留天数必须是正整数'
            }), 400

        cleanup_old_quota_records(days)

        logger.info(
            "TASKS.API.GPT_QUOTA.CLEANUP.SUCCESS",
            msg=f"清理GPT请求记录成功，保留{days}天",
            extra={"days": days}
        )

        return jsonify({
            'success': True,
            'message': f'清理完成，保留了最近{days}天的记录'
        }), 200

    except Exception as e:
        logger.error(
            "TASKS.API.GPT_QUOTA.CLEANUP.ERROR",
            msg="清理GPT请求记录失败",
            error_code="E-TASKS-API-029",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'清理GPT请求记录失败: {str(e)}'
        }), 500
