"""
日志管理路由

提供日志查询、导出等日志管理相关的API端点
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import json

from ...sys_configs.global_event_reg import vlogger
from ..middleware.auth import require_auth

# 创建日志路由蓝图
logs_bp = Blueprint('logs', __name__, url_prefix='/api/logs')


@logs_bp.route('/query', methods=['POST'])
@require_auth
def query_logs():
    """
    查询日志接口

    请求体:
        {
            "limit": 500,  # 返回最后N条日志
            "level": ["INFO", "ERROR"],  # 日志等级过滤(可选)
            "event": "API.REQUEST.START",  # 事件类型过滤(可选)
            "keyword": "搜索关键词",  # 关键词搜索(可选)
            "trace_id": "TRC-xxx",  # trace_id精确查询(可选)
            "start_time": "2025-11-13T00:00:00Z",  # 开始时间(可选)
            "end_time": "2025-11-13T23:59:59Z"  # 结束时间(可选)
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

        # 读取日志文件(只读取最后N行以提高性能)
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            # 读取所有行
            all_lines = f.readlines()

            # 只处理最后的行(提高性能)
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

                    # 关键词搜索(在msg字段中搜索)
                    if keyword:
                        msg = log_entry.get('msg', '')
                        extra_str = json.dumps(log_entry.get('extra', {}), ensure_ascii=False)
                        if keyword not in msg and keyword not in extra_str:
                            continue

                    logs.append(log_entry)

                except json.JSONDecodeError:
                    # 跳过无法解析的行
                    continue

        # 按时间倒序排列(最新的在前)
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


@logs_bp.route('/export', methods=['POST'])
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
        返回文件内容(根据format不同返回不同格式)
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

                    # 应用过滤条件(与query接口相同)
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


@logs_bp.route('/notification', methods=['POST'])
@require_auth
def log_notification():
    """
    记录前端通知日志

    请求体:
        {
            "type": "success/error/warning/info/confirm",
            "title": "标题",
            "message": "消息内容",
            "action": "show/confirm/cancel/close",
            "timestamp": "2025-12-07T12:00:00Z"
        }

    响应:
        {
            "success": true/false
        }
    """
    try:
        data = request.get_json() or {}

        notification_type = data.get('type', 'info')
        title = data.get('title', '')
        message = data.get('message', '')
        action = data.get('action', 'show')
        timestamp = data.get('timestamp', '')

        # 构建日志事件
        event = f"UI.NOTIFICATION.{notification_type.upper()}"

        # 根据通知类型选择日志级别
        if notification_type == 'error':
            vlogger.warn(
                event,
                msg=f"前端通知: {message}",
                extra={
                    "notification_type": notification_type,
                    "title": title,
                    "message": message,
                    "action": action,
                    "client_timestamp": timestamp
                }
            )
        elif notification_type == 'confirm':
            vlogger.audit(
                event,
                msg=f"用户确认操作: {message} -> {action}",
                extra={
                    "notification_type": notification_type,
                    "title": title,
                    "message": message,
                    "action": action,
                    "client_timestamp": timestamp
                }
            )
        else:
            vlogger.info(
                event,
                msg=f"前端通知: {message}",
                extra={
                    "notification_type": notification_type,
                    "title": title,
                    "message": message,
                    "action": action,
                    "client_timestamp": timestamp
                }
            )

        return jsonify({'success': True}), 200

    except Exception as e:
        # 通知日志记录失败不应影响前端体验，静默处理
        return jsonify({'success': False}), 200

