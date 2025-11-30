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

        # 转换为字典格式
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'stage': task.stage.value,
                'status': task.status.value,
                'metadata': task.metadata,
                'result': task.result,
                'error_msg': task.error_msg,
                'create_time': task.create_time.isoformat(),
                'update_time': task.update_time.isoformat()
            })

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
            'data': {
                'id': task.id,
                'stage': task.stage.value,
                'status': task.status.value,
                'metadata': task.metadata,
                'result': task.result,
                'error_msg': task.error_msg,
                'create_time': task.create_time.isoformat(),
                'update_time': task.update_time.isoformat()
            }
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
        
        # 保存更新
        db.update_async_task(task)
        
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

