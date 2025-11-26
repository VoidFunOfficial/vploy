"""
认证中间件

提供认证装饰器用于保护需要登录的API端点
"""

from flask import request, jsonify
from functools import wraps

from ...sys_configs.auth_config import get_auth_config

# 获取认证配置管理器
auth_config = get_auth_config()


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
        
        # 移除 "Bearer " 前缀(如果存在)
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

