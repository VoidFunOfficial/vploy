"""
系统设置管理路由

提供系统设置的CRUD操作API端点
"""

from flask import Blueprint, request, jsonify

from ...sys_configs.global_event_reg import vlogger
from ...sys_configs.sys_settings import (
    get_setting,
    get_all_settings,
    set_setting,
    delete_setting,
)
from ..middleware.auth import require_auth

# 创建系统设置路由蓝图
sys_settings_bp = Blueprint('sys_settings', __name__, url_prefix='/api/sys_settings')


@sys_settings_bp.route('', methods=['GET'])
@require_auth
def get_all_settings_api():
    """
    获取所有系统设置项
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "settings": [
                    {
                        "key": "设置键",
                        "value": 设置值,
                        "value_type": "值类型",
                        "description": "描述",
                        "created_at": "创建时间",
                        "updated_at": "更新时间"
                    },
                    ...
                ]
            }
        }
    """
    try:
        settings = get_all_settings()
        
        vlogger.info("SYS_SETTINGS.GET_ALL", msg="获取所有系统设置", extra={
            "count": len(settings),
            "user": request.current_user['username']
        })
        
        return jsonify({
            'success': True,
            'message': '获取成功',
            'data': {
                'settings': settings
            }
        }), 200
        
    except Exception as e:
        vlogger.error("SYS_SETTINGS.GET_ALL.ERROR", msg="获取所有系统设置失败",
                     error_code="E-API-014", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@sys_settings_bp.route('/<key>', methods=['GET'])
@require_auth
def get_setting_api(key):
    """
    获取指定key的系统设置项
    
    参数:
        key: 设置键
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "key": "设置键",
                "value": 设置值,
                "value_type": "值类型"
            }
        }
    """
    try:
        value = get_setting(key)
        
        if value is None:
            vlogger.warn("SYS_SETTINGS.GET.NOT_FOUND", msg="设置项不存在", extra={
                "key": key,
                "user": request.current_user['username']
            })
            return jsonify({
                'success': False,
                'message': f'设置项 {key} 不存在'
            }), 404
        
        vlogger.info("SYS_SETTINGS.GET", msg="获取系统设置", extra={
            "key": key,
            "user": request.current_user['username']
        })
        
        return jsonify({
            'success': True,
            'message': '获取成功',
            'data': {
                'key': key,
                'value': value
            }
        }), 200
        
    except Exception as e:
        vlogger.error("SYS_SETTINGS.GET.ERROR", msg="获取系统设置失败",
                     error_code="E-API-015", extra={"error": str(e), "key": key})
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@sys_settings_bp.route('', methods=['POST'])
@require_auth
def create_setting_api():
    """
    新增系统设置项
    
    请求体:
        {
            "key": "设置键",
            "value": 设置值,
            "value_type": "值类型（可选，自动推断）",
            "description": "描述（可选）"
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'key' not in data or 'value' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: key 和 value'
            }), 400
        
        key = data['key']
        value = data['value']
        value_type = data.get('value_type')
        description = data.get('description')
        
        success = set_setting(key, value, value_type, description)
        
        if success:
            vlogger.info("SYS_SETTINGS.CREATE", msg="新增系统设置", extra={
                "key": key,
                "value_type": value_type,
                "user": request.current_user['username']
            })
            
            return jsonify({
                'success': True,
                'message': '新增成功'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': '新增失败'
            }), 500
        
    except Exception as e:
        vlogger.error("SYS_SETTINGS.CREATE.ERROR", msg="新增系统设置失败",
                     error_code="E-API-016", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'新增失败: {str(e)}'
        }), 500


@sys_settings_bp.route('/<key>', methods=['PUT'])
@require_auth
def update_setting_api(key):
    """
    更新指定key的系统设置项
    
    参数:
        key: 设置键
    
    请求体:
        {
            "value": 设置值,
            "value_type": "值类型（可选，自动推断）",
            "description": "描述（可选）"
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'value' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: value'
            }), 400
        
        value = data['value']
        value_type = data.get('value_type')
        description = data.get('description')
        
        success = set_setting(key, value, value_type, description)
        
        if success:
            vlogger.info("SYS_SETTINGS.UPDATE", msg="更新系统设置", extra={
                "key": key,
                "value_type": value_type,
                "user": request.current_user['username']
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
        vlogger.error("SYS_SETTINGS.UPDATE.ERROR", msg="更新系统设置失败",
                     error_code="E-API-017", extra={"error": str(e), "key": key})
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@sys_settings_bp.route('/<key>', methods=['DELETE'])
@require_auth
def delete_setting_api(key):
    """
    删除指定key的系统设置项
    
    参数:
        key: 设置键
    
    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        success = delete_setting(key)
        
        if success:
            vlogger.info("SYS_SETTINGS.DELETE", msg="删除系统设置", extra={
                "key": key,
                "user": request.current_user['username']
            })
            
            return jsonify({
                'success': True,
                'message': '删除成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'设置项 {key} 不存在'
            }), 404
        
    except Exception as e:
        vlogger.error("SYS_SETTINGS.DELETE.ERROR", msg="删除系统设置失败",
                     error_code="E-API-018", extra={"error": str(e), "key": key})
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

