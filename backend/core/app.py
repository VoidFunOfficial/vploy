"""
Flask 应用工厂

创建和配置 Flask 应用实例,注册路由和中间件
"""

from flask import Flask, jsonify
from flask_cors import CORS

from .routes.auth import auth_bp
from .routes.monitor import monitor_bp
from .routes.logs import logs_bp
from .routes.database import database_bp
from .routes.polymarket import polymarket_bp
from .routes.token import token_bp
from .routes.scheduler import scheduler_bp
from .routes.tasks import tasks_bp
from .routes.filter import filter_bp
from .routes.sys_settings import sys_settings_bp
from .routes.purse import purse_bp
from .handlers.errors import register_error_handlers


def create_app():
    """
    创建并配置 Flask 应用

    返回:
        Flask: 配置好的 Flask 应用实例
    """
    app = Flask(__name__)

    # 允许跨域请求(开发环境)
    CORS(app)

    # 初始化配置数据库（确保所有表都存在）
    from ..sys_configs import init_config_database
    init_config_database()

    # 初始化任务管理器
    from ..task_manager import init_task_manager
    init_task_manager()

    # 注册蓝图(路由)
    app.register_blueprint(auth_bp)
    app.register_blueprint(monitor_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(database_bp)
    app.register_blueprint(polymarket_bp)
    app.register_blueprint(token_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(filter_bp)
    app.register_blueprint(sys_settings_bp)
    app.register_blueprint(purse_bp)

    # 注册错误处理器
    register_error_handlers(app)

    # 健康检查接口
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

    return app


# 创建应用实例(用于向后兼容)
app = create_app()

