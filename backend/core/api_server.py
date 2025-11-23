"""
后端 API 服务器

提供前端管理面板所需的 RESTful API 接口
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from typing import Optional, Dict, Any
import json
import os
from pathlib import Path

from ..sys_configs.auth_config import get_auth_config
from ..sys_configs.global_event_reg import vlogger
from .system_monitor import get_system_monitor

app = Flask(__name__)
# 允许跨域请求（开发环境）
CORS(app)

# 获取认证配置管理器
auth_config = get_auth_config()

# 获取系统监控器
system_monitor = get_system_monitor()


def require_auth(f):
    """认证装饰器 - 要求请求携带有效的会话令牌"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({
                'success': False,
                'message': '未提供认证令牌'
            }), 401
        
        # 移除 "Bearer " 前缀（如果存在）
        if token.startswith('Bearer '):
            token = token[7:]
        
        user = auth_config.verify_session(token)
        if not user:
            return jsonify({
                'success': False,
                'message': '认证令牌无效或已过期'
            }), 401
        
        # 将用户信息添加到请求上下文
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录接口
    
    请求体:
        {
            "username": "用户名",
            "password": "密码"
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "token": "会话令牌",
                "user": {
                    "username": "用户名",
                    "role": "角色"
                }
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据格式错误'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        # 验证用户密码
        user = auth_config.verify_password(username, password)
        
        if not user:
            vlogger.warn("AUTH.LOGIN.FAILED", msg="登录失败", extra={
                "username": username,
                "ip": request.remote_addr
            })
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
        
        # 创建会话
        token = auth_config.create_session(user['id'], expires_hours=24)
        
        vlogger.info("AUTH.LOGIN.SUCCESS", msg="登录成功", extra={
            "username": username,
            "role": user['role'],
            "ip": request.remote_addr
        })
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token,
                'user': {
                    'username': user['username'],
                    'role': user['role']
                }
            }
        }), 200
        
    except Exception as e:
        vlogger.error("AUTH.LOGIN.ERROR", msg="登录接口异常", 
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """
    用户登出接口
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        token = request.headers.get('Authorization')
        if token.startswith('Bearer '):
            token = token[7:]
        
        auth_config.delete_session(token)
        
        vlogger.info("AUTH.LOGOUT.SUCCESS", msg="登出成功", extra={
            "username": request.current_user['username']
        })
        
        return jsonify({
            'success': True,
            'message': '登出成功'
        }), 200
        
    except Exception as e:
        vlogger.error("AUTH.LOGOUT.ERROR", msg="登出接口异常",
                     error_code="E-API-002", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500


@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify():
    """
    验证会话令牌接口
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "user": {
                    "username": "用户名",
                    "role": "角色"
                }
            }
        }
    """
    try:
        return jsonify({
            'success': True,
            'message': '令牌有效',
            'data': {
                'user': {
                    'username': request.current_user['username'],
                    'role': request.current_user['role']
                }
            }
        }), 200
        
    except Exception as e:
        vlogger.error("AUTH.VERIFY.ERROR", msg="验证接口异常",
                     error_code="E-API-003", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'API 服务运行正常',
        'data': {
            'status': 'healthy'
        }
    }), 200


@app.route('/api/monitor/system', methods=['GET'])
@require_auth
def get_system_monitor_data():
    """
    获取系统监控数据接口

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "cpu_percent": CPU 占用率,
                "cpu_count": CPU 核心数,
                "memory_percent": 内存占用率,
                "memory_total": 总内存,
                "memory_used": 已用内存,
                "disk_percent": 磁盘占用率,
                "disk_total": 总磁盘空间,
                "disk_used": 已用磁盘空间,
                "uptime": 运行时间（秒）,
                "boot_time": 启动时间,
                "current_tps": 当前 TPS,
                "avg_tps": 平均 TPS,
                "max_tps": 峰值 TPS,
                "total_transactions": 总事务数
            }
        }
    """
    try:
        monitor_data = system_monitor.get_all_info()

        return jsonify({
            'success': True,
            'message': '获取系统监控数据成功',
            'data': monitor_data
        }), 200

    except Exception as e:
        vlogger.error("MONITOR.SYSTEM.ERROR", msg="获取系统监控数据失败",
                     error_code="E-API-004", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': '获取系统监控数据失败'
        }), 500


@app.route('/api/logs/query', methods=['POST'])
@require_auth
def query_logs():
    """
    查询日志接口

    请求体:
        {
            "limit": 500,  # 返回最后N条日志
            "level": ["INFO", "ERROR"],  # 日志等级过滤（可选）
            "event": "API.REQUEST.START",  # 事件类型过滤（可选）
            "keyword": "搜索关键词",  # 关键词搜索（可选）
            "trace_id": "TRC-xxx",  # trace_id精确查询（可选）
            "start_time": "2025-11-13T00:00:00Z",  # 开始时间（可选）
            "end_time": "2025-11-13T23:59:59Z"  # 结束时间（可选）
        }

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "logs": [...],  # 日志列表
                "total": 100  # 总数
            }
        }
    """
    try:
        data = request.get_json() or {}

        # 获取查询参数
        limit = data.get('limit', 500)
        level_filter = data.get('level', [])
        event_filter = data.get('event', '')
        keyword = data.get('keyword', '')
        trace_id = data.get('trace_id', '')
        start_time = data.get('start_time', '')
        end_time = data.get('end_time', '')

        # 读取日志文件
        log_file = Path('./logs/vlogger.log')

        if not log_file.exists():
            return jsonify({
                'success': True,
                'message': '日志文件不存在',
                'data': {
                    'logs': [],
                    'total': 0
                }
            }), 200

        # 读取日志文件（只读取最后N行以提高性能）
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            # 读取所有行
            all_lines = f.readlines()

            # 只处理最后的行（提高性能）
            lines_to_process = all_lines[-limit*2:] if len(all_lines) > limit*2 else all_lines

            for line in lines_to_process:
                line = line.strip()
                if not line:
                    continue

                try:
                    log_entry = json.loads(line)

                    # 应用过滤条件
                    # 日志等级过滤
                    if level_filter and log_entry.get('level') not in level_filter:
                        continue

                    # 事件类型过滤
                    if event_filter and event_filter not in log_entry.get('event', ''):
                        continue

                    # trace_id精确查询
                    if trace_id and log_entry.get('trace_id') != trace_id:
                        continue

                    # 时间范围过滤
                    if start_time and log_entry.get('ts', '') < start_time:
                        continue
                    if end_time and log_entry.get('ts', '') > end_time:
                        continue

                    # 关键词搜索（在msg字段中搜索）
                    if keyword:
                        msg = log_entry.get('msg', '')
                        extra_str = json.dumps(log_entry.get('extra', {}), ensure_ascii=False)
                        if keyword not in msg and keyword not in extra_str:
                            continue

                    logs.append(log_entry)

                except json.JSONDecodeError:
                    # 跳过无法解析的行
                    continue

        # 按时间倒序排列（最新的在前）
        logs.sort(key=lambda x: x.get('ts', ''), reverse=True)

        # 限制返回数量
        logs = logs[:limit]

        return jsonify({
            'success': True,
            'message': '查询成功',
            'data': {
                'logs': logs,
                'total': len(logs)
            }
        }), 200

    except Exception as e:
        vlogger.error("LOGS.QUERY.ERROR", msg="查询日志失败",
                     error_code="E-API-005", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'查询日志失败: {str(e)}'
        }), 500


@app.route('/api/logs/export', methods=['POST'])
@require_auth
def export_logs():
    """
    导出日志接口

    请求体:
        {
            "format": "json",  # 导出格式: json/csv/txt
            "filters": {...}  # 与query接口相同的过滤条件
        }

    响应:
        返回文件内容（根据format不同返回不同格式）
    """
    try:
        data = request.get_json() or {}
        export_format = data.get('format', 'json')
        filters = data.get('filters', {})

        # 使用相同的查询逻辑获取日志
        limit = filters.get('limit', 500)
        level_filter = filters.get('level', [])
        event_filter = filters.get('event', '')
        keyword = filters.get('keyword', '')
        trace_id = filters.get('trace_id', '')
        start_time = filters.get('start_time', '')
        end_time = filters.get('end_time', '')

        # 读取日志文件
        log_file = Path('./logs/vlogger.log')

        if not log_file.exists():
            return jsonify({
                'success': False,
                'message': '日志文件不存在'
            }), 404

        # 读取并过滤日志
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            lines_to_process = all_lines[-limit*2:] if len(all_lines) > limit*2 else all_lines

            for line in lines_to_process:
                line = line.strip()
                if not line:
                    continue

                try:
                    log_entry = json.loads(line)

                    # 应用过滤条件（与query接口相同）
                    if level_filter and log_entry.get('level') not in level_filter:
                        continue
                    if event_filter and event_filter not in log_entry.get('event', ''):
                        continue
                    if trace_id and log_entry.get('trace_id') != trace_id:
                        continue
                    if start_time and log_entry.get('ts', '') < start_time:
                        continue
                    if end_time and log_entry.get('ts', '') > end_time:
                        continue
                    if keyword:
                        msg = log_entry.get('msg', '')
                        extra_str = json.dumps(log_entry.get('extra', {}), ensure_ascii=False)
                        if keyword not in msg and keyword not in extra_str:
                            continue

                    logs.append(log_entry)

                except json.JSONDecodeError:
                    continue

        # 按时间倒序排列
        logs.sort(key=lambda x: x.get('ts', ''), reverse=True)
        logs = logs[:limit]

        # 根据格式返回不同内容
        if export_format == 'json':
            return jsonify({
                'success': True,
                'data': logs
            }), 200

        elif export_format == 'csv':
            # 生成CSV格式
            csv_lines = ['时间,等级,事件,事件码,trace_id,服务,消息,额外信息']
            for log in logs:
                extra_str = json.dumps(log.get('extra', {}), ensure_ascii=False)
                csv_lines.append(f'"{log.get("ts", "")}","{log.get("level", "")}","{log.get("event", "")}","{log.get("event_code", "")}","{log.get("trace_id", "")}","{log.get("service", "")}","{log.get("msg", "")}","{extra_str}"')

            return '\n'.join(csv_lines), 200, {
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': 'attachment; filename=logs.csv'
            }

        elif export_format == 'txt':
            # 生成TXT格式
            txt_lines = []
            for log in logs:
                txt_lines.append(f"[{log.get('ts', '')}] [{log.get('level', '')}] {log.get('event', '')} - {log.get('msg', '')}")
                if log.get('extra'):
                    txt_lines.append(f"  额外信息: {json.dumps(log.get('extra', {}), ensure_ascii=False, indent=2)}")
                txt_lines.append('')

            return '\n'.join(txt_lines), 200, {
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Disposition': 'attachment; filename=logs.txt'
            }

        else:
            return jsonify({
                'success': False,
                'message': f'不支持的导出格式: {export_format}'
            }), 400

    except Exception as e:
        vlogger.error("LOGS.EXPORT.ERROR", msg="导出日志失败",
                     error_code="E-API-006", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'导出日志失败: {str(e)}'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'message': '接口不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({
        'success': False,
        'message': '服务器内部错误'
    }), 500


# 使用 run_api_server.py 启动服务器

