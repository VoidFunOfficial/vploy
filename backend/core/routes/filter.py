"""
过滤器管理路由

提供过滤器黑名单配置、已处理事件管理等API端点
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from ...sys_configs.global_event_reg import vlogger
from ...sys_configs.filter_config import (
    get_blacklist,
    add_blacklist_item,
    remove_blacklist_item,
    update_blacklist_item,
    get_all_blacklist_items,
    clear_processed_markets,
)
from ...sys_configs.config_manager import get_config_manager
from ..middleware.auth import require_auth

# 创建过滤器路由蓝图
filter_bp = Blueprint('filter', __name__, url_prefix='/api/filter')

# 获取配置管理器
config_manager = get_config_manager()


@filter_bp.route('/blacklist', methods=['GET'])
@require_auth
def get_blacklist_config():
    """
    获取所有黑名单配置项（包括未激活的）
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "items": [
                    {
                        "id": 1,
                        "blacklist_type": "tag",
                        "value": "china",
                        "is_active": true,
                        "created_at": "2025-11-30T12:00:00",
                        "updated_at": "2025-11-30T12:00:00"
                    }
                ],
                "summary": {
                    "total": 10,
                    "active": 8,
                    "inactive": 2,
                    "by_type": {
                        "tag": 3,
                        "title_keyword": 4,
                        "description_keyword": 3
                    }
                }
            }
        }
    """
    try:
        # 获取所有黑名单配置项
        items = get_all_blacklist_items()
        
        # 统计信息
        total = len(items)
        active = sum(1 for item in items if item['is_active'])
        inactive = total - active
        
        # 按类型统计
        by_type = {}
        for item in items:
            bl_type = item['blacklist_type']
            by_type[bl_type] = by_type.get(bl_type, 0) + 1
        
        vlogger.info("FILTER.API.GET_BLACKLIST", msg="获取黑名单配置", extra={
            "total": total,
            "active": active
        })
        
        return jsonify({
            'success': True,
            'message': '获取黑名单配置成功',
            'data': {
                'items': items,
                'summary': {
                    'total': total,
                    'active': active,
                    'inactive': inactive,
                    'by_type': by_type
                }
            }
        }), 200
        
    except Exception as e:
        vlogger.error("FILTER.API.GET_BLACKLIST_ERROR", msg="获取黑名单配置失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'获取黑名单配置失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/blacklist', methods=['POST'])
@require_auth
def add_blacklist():
    """
    添加黑名单配置项
    
    请求体:
        {
            "blacklist_type": "tag",  # tag/title_keyword/description_keyword
            "value": "china"
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": null
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求体不能为空',
                'data': None
            }), 400
        
        blacklist_type = data.get('blacklist_type')
        value = data.get('value')
        
        # 验证参数
        if not blacklist_type or not value:
            return jsonify({
                'success': False,
                'message': 'blacklist_type 和 value 不能为空',
                'data': None
            }), 400
        
        # 验证黑名单类型
        valid_types = ['tag', 'title_keyword', 'description_keyword']
        if blacklist_type not in valid_types:
            return jsonify({
                'success': False,
                'message': f'无效的黑名单类型，必须是: {", ".join(valid_types)}',
                'data': None
            }), 400
        
        # 添加黑名单项
        success = add_blacklist_item(blacklist_type, value)
        
        if success:
            vlogger.info("FILTER.API.ADD_BLACKLIST", msg="添加黑名单配置项", extra={
                "blacklist_type": blacklist_type,
                "value": value
            })
            return jsonify({
                'success': True,
                'message': '添加黑名单配置项成功',
                'data': None
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '黑名单配置项已存在',
                'data': None
            }), 409
        
    except Exception as e:
        vlogger.error("FILTER.API.ADD_BLACKLIST_ERROR", msg="添加黑名单配置项失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'添加黑名单配置项失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/blacklist/<int:item_id>', methods=['DELETE'])
@require_auth
def delete_blacklist(item_id):
    """
    删除黑名单配置项
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": null
        }
    """
    try:
        # 先查询配置项信息
        query = "SELECT blacklist_type, value FROM filter_blacklist WHERE id = ?"
        rows = config_manager.execute_query(query, (item_id,))
        
        if not rows:
            return jsonify({
                'success': False,
                'message': '黑名单配置项不存在',
                'data': None
            }), 404
        
        blacklist_type = rows[0]['blacklist_type']
        value = rows[0]['value']
        
        # 删除黑名单项
        success = remove_blacklist_item(blacklist_type, value)
        
        if success:
            vlogger.info("FILTER.API.DELETE_BLACKLIST", msg="删除黑名单配置项", extra={
                "item_id": item_id,
                "blacklist_type": blacklist_type,
                "value": value
            })
            return jsonify({
                'success': True,
                'message': '删除黑名单配置项成功',
                'data': None
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '删除黑名单配置项失败',
                'data': None
            }), 500
        
    except Exception as e:
        vlogger.error("FILTER.API.DELETE_BLACKLIST_ERROR", msg="删除黑名单配置项失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'删除黑名单配置项失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/blacklist/<int:item_id>/toggle', methods=['PUT'])
@require_auth
def toggle_blacklist(item_id):
    """
    切换黑名单配置项的激活状态
    
    请求体:
        {
            "is_active": true/false
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": null
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'is_active' not in data:
            return jsonify({
                'success': False,
                'message': 'is_active 参数不能为空',
                'data': None
            }), 400
        
        is_active = data.get('is_active')
        
        # 更新黑名单项状态
        success = update_blacklist_item(item_id, is_active)
        
        if success:
            vlogger.info("FILTER.API.TOGGLE_BLACKLIST", msg="切换黑名单配置项状态", extra={
                "item_id": item_id,
                "is_active": is_active
            })
            return jsonify({
                'success': True,
                'message': '更新黑名单配置项状态成功',
                'data': None
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '黑名单配置项不存在',
                'data': None
            }), 404
        
    except Exception as e:
        vlogger.error("FILTER.API.TOGGLE_BLACKLIST_ERROR", msg="切换黑名单配置项状态失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'更新黑名单配置项状态失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/processed-markets', methods=['GET'])
@require_auth
def get_processed_markets():
    """
    获取已处理的事件列表

    查询参数:
        limit: 返回数量限制（默认100）
        offset: 偏移量（默认0）

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "items": [
                    {
                        "id": 1,
                        "market_id": "event_123",
                        "processed_at": "2025-11-30T12:00:00",
                        "created_at": "2025-11-30T12:00:00"
                    }
                ],
                "total": 100,
                "limit": 100,
                "offset": 0
            }
        }
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        # 查询总数
        count_query = "SELECT COUNT(*) as total FROM processed_markets"
        count_result = config_manager.execute_query(count_query)
        total = count_result[0]['total']

        # 查询数据
        query = """
            SELECT id, market_id, processed_at, created_at
            FROM processed_markets
            ORDER BY processed_at DESC
            LIMIT ? OFFSET ?
        """
        rows = config_manager.execute_query(query, (limit, offset))

        items = []
        for row in rows:
            items.append({
                'id': row['id'],
                'market_id': row['market_id'],
                'processed_at': row['processed_at'],
                'created_at': row['created_at']
            })

        vlogger.info("FILTER.API.GET_PROCESSED_MARKETS", msg="获取已处理事件列表", extra={
            "total": total,
            "limit": limit,
            "offset": offset
        })

        return jsonify({
            'success': True,
            'message': '获取已处理事件列表成功',
            'data': {
                'items': items,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        }), 200

    except Exception as e:
        vlogger.error("FILTER.API.GET_PROCESSED_MARKETS_ERROR", msg="获取已处理事件列表失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'获取已处理事件列表失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/processed-markets/<market_id>', methods=['DELETE'])
@require_auth
def delete_processed_market(market_id):
    """
    删除单个已处理事件记录

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": null
        }
    """
    try:
        query = "DELETE FROM processed_markets WHERE market_id = ?"
        rowcount = config_manager.execute_update(query, (market_id,))

        if rowcount > 0:
            vlogger.info("FILTER.API.DELETE_PROCESSED_MARKET", msg="删除已处理事件记录", extra={
                "market_id": market_id
            })
            return jsonify({
                'success': True,
                'message': '删除已处理事件记录成功',
                'data': None
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '已处理事件记录不存在',
                'data': None
            }), 404

    except Exception as e:
        vlogger.error("FILTER.API.DELETE_PROCESSED_MARKET_ERROR", msg="删除已处理事件记录失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'删除已处理事件记录失败: {str(e)}',
            'data': None
        }), 500


@filter_bp.route('/processed-markets/clear', methods=['POST'])
@require_auth
def clear_processed_markets_api():
    """
    清理已处理事件记录

    请求体:
        {
            "before_date": "2025-11-01T00:00:00"  # 可选，清理此日期之前的记录
        }

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "cleared_count": 100
            }
        }
    """
    try:
        data = request.get_json() or {}
        before_date_str = data.get('before_date')

        before_date = None
        if before_date_str:
            try:
                before_date = datetime.fromisoformat(before_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '日期格式无效，请使用 ISO 8601 格式',
                    'data': None
                }), 400

        # 清理记录
        cleared_count = clear_processed_markets(before_date)

        vlogger.info("FILTER.API.CLEAR_PROCESSED_MARKETS", msg="清理已处理事件记录", extra={
            "cleared_count": cleared_count,
            "before_date": before_date_str
        })

        return jsonify({
            'success': True,
            'message': f'清理了 {cleared_count} 条已处理事件记录',
            'data': {
                'cleared_count': cleared_count
            }
        }), 200

    except Exception as e:
        vlogger.error("FILTER.API.CLEAR_PROCESSED_MARKETS_ERROR", msg="清理已处理事件记录失败", extra={
            "error": str(e)
        })
        return jsonify({
            'success': False,
            'message': f'清理已处理事件记录失败: {str(e)}',
            'data': None
        }), 500

