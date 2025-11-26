"""
错误处理器

提供全局错误处理器,统一处理HTTP错误响应
"""

from flask import jsonify


def register_error_handlers(app):
    """
    注册错误处理器到Flask应用
    
    参数:
        app: Flask应用实例
    """
    
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

