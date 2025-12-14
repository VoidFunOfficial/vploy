"""
定时任务管理路由

提供定时任务的增删改查、启动/关闭等管理接口
"""

from flask import Blueprint, request, jsonify
from ...task_manager import (
    add_scheduled_task,
    update_scheduled_task,
    get_scheduled_task_info,
    list_scheduled_tasks,
    TaskDatabase,
    get_scheduler
)
from ...vlogger import get_logger

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')
logger = get_logger("scheduler_api")
db = TaskDatabase()


@scheduler_bp.route('/tasks', methods=['GET'])
def get_scheduled_tasks():
    """
    获取定时任务列表

    查询参数:
        enabled: 是否启用 (true/false/all, 默认all)
        limit: 返回数量限制
        offset: 偏移量
    """
    try:
        enabled_param = request.args.get('enabled', 'all')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)

        # 解析enabled参数
        # list_scheduled_tasks 使用 enabled_only 参数
        if enabled_param == 'true':
            # 只返回启用的任务
            all_tasks = list_scheduled_tasks(enabled_only=True)
        elif enabled_param == 'false':
            # 返回所有任务,然后过滤出禁用的
            all_tasks = list_scheduled_tasks(enabled_only=False)
            all_tasks = [t for t in all_tasks if not t['enabled']]
        else:
            # 返回所有任务
            all_tasks = list_scheduled_tasks(enabled_only=False)

        # 应用分页
        total = len(all_tasks)
        if limit:
            tasks = all_tasks[offset:offset + limit]
        else:
            tasks = all_tasks[offset:]

        # tasks 已经是字典格式 (来自 to_dict())
        tasks_data = tasks

        return jsonify({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'total': total,
                'offset': offset,
                'limit': limit
            }
        }), 200

    except Exception as e:
        logger.error(
            "SCHEDULER.API.LIST.ERROR",
            msg="获取定时任务列表失败",
            error_code="E-SCHEDULER-API-001",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取定时任务列表失败: {str(e)}'
        }), 500


@scheduler_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_scheduled_task(task_id):
    """获取单个定时任务详情"""
    try:
        task = get_scheduled_task_info(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'id': task.id,
                'name': task.name,
                'task_type': task.task_type,
                'schedule': task.schedule,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'metadata': task.metadata,
                'create_time': task.create_time.isoformat(),
                'update_time': task.update_time.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(
            "SCHEDULER.API.GET.ERROR",
            msg=f"获取定时任务失败: {task_id}",
            error_code="E-SCHEDULER-API-002",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'获取定时任务失败: {str(e)}'
        }), 500


@scheduler_bp.route('/tasks', methods=['POST'])
def create_scheduled_task():
    """
    创建定时任务
    
    请求体:
        name: 任务名称 (必填)
        task_type: 任务类型 (interval/cron, 必填)
        schedule: 调度配置 (必填)
        enabled: 是否启用 (默认true)
        metadata: 任务元数据 (可选)
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': '任务名称不能为空'
            }), 400
        
        if not data.get('task_type'):
            return jsonify({
                'success': False,
                'message': '任务类型不能为空'
            }), 400
        
        if not data.get('schedule'):
            return jsonify({
                'success': False,
                'message': '调度配置不能为空'
            }), 400
        
        # 验证任务类型
        if data['task_type'] not in ['interval', 'cron']:
            return jsonify({
                'success': False,
                'message': '任务类型必须是 interval 或 cron'
            }), 400
        
        # 创建任务
        task_id = add_scheduled_task(
            name=data['name'],
            task_type=data['task_type'],
            schedule=data['schedule'],
            enabled=data.get('enabled', True),
            metadata=data.get('metadata', {})
        )
        
        logger.info(
            "SCHEDULER.API.CREATE.SUCCESS",
            msg=f"创建定时任务成功: {data['name']}",
            extra={"task_id": task_id, "name": data['name']}
        )
        
        return jsonify({
            'success': True,
            'message': '创建定时任务成功',
            'data': {'task_id': task_id}
        }), 201
        
    except Exception as e:
        logger.error(
            "SCHEDULER.API.CREATE.ERROR",
            msg="创建定时任务失败",
            error_code="E-SCHEDULER-API-003",
            extra={"error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'创建定时任务失败: {str(e)}'
        }), 500


@scheduler_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_scheduled_task_route(task_id):
    """
    更新定时任务

    请求体:
        task_type: 任务类型 (可选)
        schedule: 调度配置 (可选)
        enabled: 是否启用 (可选)
        metadata: 任务元数据 (可选)
    """
    try:
        data = request.get_json()

        # 获取现有任务
        task = db.get_scheduled_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        # 验证任务类型
        if 'task_type' in data:
            if data['task_type'] not in ['interval', 'cron']:
                return jsonify({
                    'success': False,
                    'message': '任务类型必须是 interval 或 cron'
                }), 400

        # 直接更新任务对象的字段
        if 'task_type' in data:
            task.task_type = data['task_type']

        if 'schedule' in data:
            task.schedule = data['schedule']

        if 'enabled' in data:
            task.enabled = data['enabled']

        if 'metadata' in data:
            task.metadata = data['metadata']

        # 使用数据库方法保存更新
        db.update_scheduled_task(task)

        logger.info(
            "SCHEDULER.API.UPDATE.SUCCESS",
            msg=f"更新定时任务成功: {task.name}",
            extra={"task_id": task_id, "name": task.name}
        )

        return jsonify({
            'success': True,
            'message': '更新定时任务成功'
        }), 200

    except Exception as e:
        logger.error(
            "SCHEDULER.API.UPDATE.ERROR",
            msg=f"更新定时任务失败: {task_id}",
            error_code="E-SCHEDULER-API-004",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'更新定时任务失败: {str(e)}'
        }), 500


@scheduler_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_scheduled_task(task_id):
    """删除定时任务"""
    try:
        # 获取任务信息
        task = get_scheduled_task_info(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        # 删除任务
        db.delete_scheduled_task(task_id)

        logger.info(
            "SCHEDULER.API.DELETE.SUCCESS",
            msg=f"删除定时任务成功: {task.name}",
            extra={"task_id": task_id, "name": task.name}
        )

        return jsonify({
            'success': True,
            'message': '删除定时任务成功'
        }), 200

    except Exception as e:
        logger.error(
            "SCHEDULER.API.DELETE.ERROR",
            msg=f"删除定时任务失败: {task_id}",
            error_code="E-SCHEDULER-API-005",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'删除定时任务失败: {str(e)}'
        }), 500


@scheduler_bp.route('/tasks/<int:task_id>/run', methods=['POST'])
def run_scheduled_task_now(task_id):
    """
    立即执行定时任务一次

    不影响任务的正常调度，只是手动触发一次执行
    提交到Huey队列异步执行，避免阻塞前端
    """
    try:
        from ...task_manager import execute_scheduled_task

        # 获取任务信息
        task = db.get_scheduled_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': f'任务不存在: {task_id}'
            }), 404

        logger.info(
            "SCHEDULER.API.RUN_NOW.START",
            msg=f"提交定时任务到Huey队列: {task.name}",
            extra={"task_id": task_id, "task_name": task.name}
        )

        # 提交到Huey队列异步执行
        execute_scheduled_task(task_id)

        # 更新最后运行时间（但不更新下次运行时间，保持原有调度）
        from datetime import datetime
        task.last_run = datetime.now()
        db.update_scheduled_task(task)

        logger.info(
            "SCHEDULER.API.RUN_NOW.SUBMITTED",
            msg=f"定时任务已提交到Huey队列: {task.name}",
            extra={"task_id": task_id, "task_name": task.name}
        )

        return jsonify({
            'success': True,
            'message': f'任务 {task.name} 已提交到队列，将在后台异步执行'
        }), 202

    except Exception as e:
        logger.error(
            "SCHEDULER.API.RUN_NOW.ERROR",
            msg=f"提交定时任务失败: {task_id}",
            error_code="E-SCHEDULER-API-006",
            extra={"task_id": task_id, "error": str(e)}
        )
        return jsonify({
            'success': False,
            'message': f'提交任务失败: {str(e)}'
        }), 500

