"""
Token 管理路由

提供 Token 刷新管理相关的 API 端点
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from ...sys_configs.global_event_reg import vlogger
from ...sys_configs.token_refresher import get_token_refresher, TokenType
from ..middleware.auth import require_auth

# 创建 Token 路由蓝图
token_bp = Blueprint('token', __name__, url_prefix='/api/token')

# 获取 TokenRefresher 实例
token_refresher = get_token_refresher()


@token_bp.route('/status', methods=['GET'])
@require_auth
def get_all_status():
    """
    获取所有 Token 状态
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "tokens": {
                    "coze_token": {
                        "token_value": "...",
                        "expires_at": "2025-12-25T00:00:00",
                        "is_expired": false,
                        "last_checked_at": "2025-11-25T10:00:00",
                        "validity_days": 30,
                        "description": "Coze API Token"
                    },
                    ...
                },
                "check_interval_minutes": 10,
                "is_running": true
            }
        }
    """
    try:
        # 获取所有 token 状态
        all_status = token_refresher.get_all_token_status()
        
        # 获取检查间隔和运行状态
        check_interval = token_refresher.check_interval_minutes
        is_running = token_refresher.is_running()
        
        vlogger.info("TOKEN.API.STATUS.GET", msg="获取 Token 状态", extra={
            "user": request.current_user['username'],
            "token_count": len(all_status)
        })
        
        return jsonify({
            'success': True,
            'message': '获取成功',
            'data': {
                'tokens': all_status,
                'check_interval_minutes': check_interval,
                'is_running': is_running
            }
        }), 200
        
    except Exception as e:
        vlogger.error("TOKEN.API.STATUS.ERROR", msg="获取 Token 状态失败",
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@token_bp.route('/update', methods=['POST'])
@require_auth
def update_token():
    """
    更新 Token 信息
    
    请求体:
        {
            "token_type": "coze_token",
            "token_value": "new_token_value",
            "expires_at": "2025-12-25T00:00:00"  # 可选
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求体不能为空'
            }), 400
        
        token_type = data.get('token_type')
        token_value = data.get('token_value')
        expires_at_str = data.get('expires_at')
        
        if not token_type:
            return jsonify({
                'success': False,
                'message': 'token_type 不能为空'
            }), 400
        
        # 解析过期时间
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '过期时间格式错误，应为 ISO 8601 格式'
                }), 400
        
        # 更新 token
        success = token_refresher.update_token(
            token_type=token_type,
            token_value=token_value,
            expires_at=expires_at
        )
        
        if success:
            vlogger.info("TOKEN.API.UPDATE", msg="更新 Token 成功", extra={
                "user": request.current_user['username'],
                "token_type": token_type,
                "has_value": token_value is not None,
                "has_expires_at": expires_at is not None
            })
            
            return jsonify({
                'success': True,
                'message': '更新成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '更新失败'
            }), 500
        
    except Exception as e:
        vlogger.error("TOKEN.API.UPDATE.ERROR", msg="更新 Token 失败",
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@token_bp.route('/check', methods=['POST'])
@require_auth
def check_tokens():
    """
    手动检查所有 Token 过期状态
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "coze_token": false,
                "auth_token": true,
                ...
            }
        }
    """
    try:
        # 执行检查
        result = token_refresher.check_all_tokens()
        
        vlogger.info("TOKEN.API.CHECK", msg="手动检查 Token 状态", extra={
            "user": request.current_user['username'],
            "result": result
        })
        
        return jsonify({
            'success': True,
            'message': '检查完成',
            'data': result
        }), 200
        
    except Exception as e:
        vlogger.error("TOKEN.API.CHECK.ERROR", msg="检查 Token 失败",
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'检查失败: {str(e)}'
        }), 500


@token_bp.route('/expire', methods=['POST'])
@require_auth
def expire_token():
    """
    手动标记 Token 为过期
    
    请求体:
        {
            "token_type": "coze_token"
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求体不能为空'
            }), 400
        
        token_type = data.get('token_type')
        
        if not token_type:
            return jsonify({
                'success': False,
                'message': 'token_type 不能为空'
            }), 400
        
        # 标记为过期
        success = token_refresher.set_expired_immediate(token_type)
        
        if success:
            vlogger.warn("TOKEN.API.EXPIRE", msg="手动标记 Token 为过期", extra={
                "user": request.current_user['username'],
                "token_type": token_type
            })
            
            return jsonify({
                'success': True,
                'message': 'Token 已标记为过期，已发送告警邮件'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '标记失败'
            }), 500
        
    except Exception as e:
        vlogger.error("TOKEN.API.EXPIRE.ERROR", msg="标记 Token 过期失败",
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'标记失败: {str(e)}'
        }), 500


@token_bp.route('/config/interval', methods=['POST'])
@require_auth
def set_check_interval():
    """
    设置检查间隔
    
    请求体:
        {
            "minutes": 10
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求体不能为空'
            }), 400
        
        minutes = data.get('minutes')
        
        if not minutes or not isinstance(minutes, int) or minutes <= 0:
            return jsonify({
                'success': False,
                'message': '检查间隔必须为正整数'
            }), 400
        
        # 设置检查间隔
        success = token_refresher.set_check_interval(minutes)
        
        if success:
            vlogger.info("TOKEN.API.INTERVAL.SET", msg="设置检查间隔", extra={
                "user": request.current_user['username'],
                "minutes": minutes
            })
            
            return jsonify({
                'success': True,
                'message': f'检查间隔已设置为 {minutes} 分钟'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '设置失败'
            }), 500
        
    except Exception as e:
        vlogger.error("TOKEN.API.INTERVAL.ERROR", msg="设置检查间隔失败",
                     error_code="E-API-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'设置失败: {str(e)}'
        }), 500

