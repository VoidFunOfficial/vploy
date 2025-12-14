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
from ...vlogger import get_logger

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')
logger = get_logger("tasks_api")
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
            "data": {
                "analysis_status": "success",  # 或 "polling" (仍在思考)
                "has_result": true,
                "analysis_result": {...},  # 如果成功
                "market_ids": [...],
                "error": "..."  # 如果失败
            }
        }
    """
    try:
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

        # 获取Cookie
        from ...sys_configs.token_refresher import get_token_refresher, TokenType
        token_refresher = get_token_refresher()
        access_token_status = token_refresher.get_token_status(TokenType.ACCESS_TOKEN.value)
        auth_token_status = token_refresher.get_token_status(TokenType.AUTH_TOKEN.value)

        if not access_token_status or not auth_token_status:
            return jsonify({
                'success': False,
                'message': '未配置access_token或auth_token'
            }), 400

        if access_token_status.get('is_expired') or auth_token_status.get('is_expired'):
            return jsonify({
                'success': False,
                'message': 'access_token或auth_token已过期'
            }), 400

        # 构建cookie_string
        access_token = access_token_status.get('token_value')
        auth_token = auth_token_status.get('token_value')
        cookie_string = f"__Secure-access_token={access_token};__Secure-auth_token={auth_token}"

        from ...ai_analysis.gpt_api import parse_cookie_string, get_result
        from ...ai_analysis.analysis_tasks import validate_analysis_result, AnalysisStatus

        cookies_dict = parse_cookie_string(cookie_string)

        # 执行一次轮询
        logger.info(
            "TASKS.API.POLL_ONCE.START",
            msg=f"手动轮询分析结果: {task_id}",
            extra={"task_id": task_id, "conversation_id": conversation_id}
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
                task.status = TaskStatus.FINISHED
                db.update_async_task(task)

                logger.info(
                    "TASKS.API.POLL_ONCE.SUCCESS",
                    msg=f"手动轮询成功，分析完成: {task_id}",
                    extra={
                        "task_id": task_id,
                        "market_count": len(parsed_json),
                        "market_ids": list(parsed_json.keys())
                    }
                )

                return jsonify({
                    'success': True,
                    'data': {
                        'analysis_status': AnalysisStatus.SUCCESS.value,
                        'has_result': True,
                        'analysis_result': parsed_json,
                        'market_ids': list(parsed_json.keys()),
                        'market_count': len(parsed_json)
                    }
                }), 200
            else:
                # 验证失败
                error_msg = "结果验证失败: 返回的结果不符合预期的JSON结构"
                task.error_msg = error_msg
                task.result["analysis_status"] = AnalysisStatus.FAILED.value
                task.result["error"] = error_msg
                task.status = TaskStatus.FAILED
                db.update_async_task(task)

                logger.error(
                    "TASKS.API.POLL_ONCE.VALIDATION_FAILED",
                    msg=error_msg,
                    error_code="E-TASKS-API-011",
                    extra={
                        "task_id": task_id,
                        "response_preview": ai_response[:200]
                    }
                )

                return jsonify({
                    'success': False,
                    'message': error_msg,
                    'data': {
                        'analysis_status': AnalysisStatus.FAILED.value,
                        'has_result': False,
                        'error': error_msg,
                        'raw_response_preview': ai_response[:200]
                    }
                }), 200

        elif poll_result.get("error") == "AI is thinking":
            # AI仍在思考
            logger.info(
                "TASKS.API.POLL_ONCE.THINKING",
                msg=f"AI仍在思考: {task_id}",
                extra={"task_id": task_id}
            )

            return jsonify({
                'success': True,
                'data': {
                    'analysis_status': AnalysisStatus.POLLING.value,
                    'has_result': False,
                    'message': 'AI仍在思考中，请稍后再试'
                }
            }), 200

        else:
            # 查询失败
            error_msg = f"查询失败: {poll_result.get('error', '未知错误')}"
            logger.error(
                "TASKS.API.POLL_ONCE.QUERY_FAILED",
                msg=error_msg,
                error_code="E-TASKS-API-012",
                extra={"task_id": task_id, "poll_result": poll_result}
            )

            return jsonify({
                'success': False,
                'message': error_msg
            }), 500

    except Exception as e:
        logger.error(
            "TASKS.API.POLL_ONCE.ERROR",
            msg=f"手动轮询失败: {task_id}",
            error_code="E-TASKS-API-013",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'手动轮询失败: {str(e)}'
        }), 500


@tasks_bp.route('/<int:task_id>/split', methods=['POST'])
def split_analysis_task_route(task_id):
    """
    拆分成功的analysis任务为多个decision任务

    适用场景:
    - analysis任务成功完成后，将每个市场的分析结果拆分为独立的decision任务

    处理流程:
    1. 验证任务状态（必须是analysis阶段且成功）
    2. 遍历analysis_result中的每个市场
    3. 获取市场详细信息
    4. 合并mark信息
    5. 创建decision任务
    6. 删除原始analysis任务

    返回:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "created_tasks": [1, 2, 3],  # 创建的decision任务ID列表
                "failed_markets": ["market_id"],  # 失败的市场ID列表
                "total_markets": 5,
                "success_count": 4,
                "failed_count": 1
            }
        }
    """
    try:
        from ...ai_analysis.analysis_tasks import split_analysis_task

        logger.info(
            "TASKS.API.SPLIT.START",
            msg=f"开始拆分分析任务: {task_id}",
            extra={"task_id": task_id}
        )

        # 调用拆分函数
        result = split_analysis_task(task_id)

        if result["success"]:
            logger.info(
                "TASKS.API.SPLIT.SUCCESS",
                msg=f"拆分任务成功: {task_id}",
                extra={
                    "task_id": task_id,
                    "created_count": result["success_count"],
                    "failed_count": result["failed_count"]
                }
            )

            return jsonify({
                'success': True,
                'message': result["message"],
                'data': {
                    'created_tasks': result["created_tasks"],
                    'failed_markets': result["failed_markets"],
                    'total_markets': result["total_markets"],
                    'success_count': result["success_count"],
                    'failed_count': result["failed_count"]
                }
            }), 200
        else:
            logger.warn(
                "TASKS.API.SPLIT.FAILED",
                msg=f"拆分任务失败: {task_id}",
                extra={
                    "task_id": task_id,
                    "error": result["message"]
                }
            )

            return jsonify({
                'success': False,
                'message': result["message"],
                'data': {
                    'created_tasks': result["created_tasks"],
                    'failed_markets': result["failed_markets"],
                    'total_markets': result["total_markets"],
                    'success_count': result["success_count"],
                    'failed_count': result["failed_count"]
                }
            }), 400

    except Exception as e:
        logger.error(
            "TASKS.API.SPLIT.ERROR",
            msg=f"拆分任务异常: {task_id}",
            error_code="E-TASKS-API-014",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'拆分任务失败: {str(e)}'
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
        from ...auto_decision import allocate, Market
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

            # 创建Market对象
            market = Market(
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
        allocation_map = {alloc['id']: alloc for alloc in allocations}

        processed_count = 0
        filtered_count = 0  # 被过滤掉的任务数

        for market_id, task in task_map.items():
            alloc = allocation_map.get(market_id)

            if alloc:
                # 有分配结果，检查投入金额是否满足最小阈值
                side_price = alloc['price']  # 交易方向的价格
                min_invest = 5.0 * side_price  # 最小投入金额阈值

                if alloc['invest'] < min_invest:
                    # 投入金额不足，过滤掉
                    task.result = {
                        'decision': 'skip',
                        'reason': f'投入金额${alloc["invest"]:.2f}低于最小阈值${min_invest:.2f} (5*{side_price:.2f})',
                        'wealth': wealth,
                        'filtered': True,
                        'original_allocation': {
                            'side': alloc['side'],
                            'dollars': alloc['invest'],
                            'shares': alloc['shares'],
                            'cost': alloc['price']
                        }
                    }
                    filtered_count += 1

                    logger.info(
                        "TASKS.API.DECISION.FILTERED",
                        msg=f"过滤低投入任务: {task.id}",
                        extra={
                            "task_id": task.id,
                            "market_id": market_id,
                            "invest": alloc['invest'],
                            "min_invest": min_invest,
                            "side_price": side_price
                        }
                    )
                else:
                    # 投入金额满足要求
                    # 计算评分（基于投资金额占总资金的比例）
                    score = alloc['invest'] / wealth if wealth > 0 else 0.0

                    task.result = {
                        'decision': 'trade',
                        'allocation': {
                            'side': alloc['side'],
                            'score': score,
                            'fraction_of_gross': alloc['f'],
                            'dollars': alloc['invest'],
                            'shares': alloc['shares'],
                            'cost': alloc['price']
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
                'allocations': allocations,
                'summary': {
                    'total_tasks': len(pending_tasks),
                    'valid_markets': len(markets),
                    'tradable_markets': len(allocations),
                    'filtered_markets': filtered_count,
                    'actual_trade_markets': len([a for a in allocations if a['invest'] >= 5.0 * a['price']]),
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
