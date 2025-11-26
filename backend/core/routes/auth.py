"""
认证路由

提供用户登录、登出、会话验证等认证相关的API端点
"""

from flask import Blueprint, request, jsonify

from ...sys_configs.auth_config import get_auth_config
from ...sys_configs.global_event_reg import vlogger
from ..middleware.auth import require_auth

# 创建认证路由蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 获取认证配置管理器
auth_config = get_auth_config()


@auth_bp.route('/login', methods=['POST'])
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


@auth_bp.route('/logout', methods=['POST'])
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


@auth_bp.route('/verify', methods=['GET'])
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

