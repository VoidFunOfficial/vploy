"""
系统监控路由

提供系统监控数据查询的API端点
"""

from flask import Blueprint, jsonify

from ...sys_configs.global_event_reg import vlogger
from ..system_monitor import get_system_monitor
from ..middleware.auth import require_auth

# 创建监控路由蓝图
monitor_bp = Blueprint('monitor', __name__, url_prefix='/api/monitor')

# 获取系统监控器
system_monitor = get_system_monitor()


@monitor_bp.route('/system', methods=['GET'])
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
                "uptime": 运行时间(秒),
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

