"""
Polymarket API 路由

提供 Polymarket 事件和市场数据查询的API端点
"""

from flask import Blueprint, request, jsonify

from ...sys_configs.global_event_reg import vlogger
from ..middleware.auth import require_auth
from ..utils.helpers import event_to_dict, market_to_dict

# 创建 Polymarket 路由蓝图
polymarket_bp = Blueprint('polymarket', __name__, url_prefix='/api/polymarket')


@polymarket_bp.route('/event/slug/<slug>', methods=['GET'])
@require_auth
def get_event_by_slug(slug):
    """
    通过 slug 获取事件

    参数:
        slug: 事件 slug

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": Event 对象数据
        }
    """
    try:
        from ...polymarket_api import GammaMarketsAPI

        with GammaMarketsAPI() as api:
            event = api.get_event_by_slug(slug)

            if not event:
                return jsonify({
                    'success': False,
                    'message': f'未找到 slug 为 {slug} 的事件'
                }), 404

            # 将 Event 对象转换为字典
            event_data = event_to_dict(event)

            vlogger.info("API.POLYMARKET.EVENT.GET", msg="获取事件成功", extra={
                "slug": slug,
                "event_id": event.id,
                "user": request.current_user['username']
            })

            return jsonify({
                'success': True,
                'message': '获取事件成功',
                'data': event_data
            }), 200

    except Exception as e:
        vlogger.error("API.POLYMARKET.EVENT.ERROR", msg="获取事件失败",
                     error_code="E-API-013", extra={"error": str(e), "slug": slug})
        return jsonify({
            'success': False,
            'message': f'获取事件失败: {str(e)}'
        }), 500


@polymarket_bp.route('/event/id/<event_id>', methods=['GET'])
@require_auth
def get_event_by_id(event_id):
    """
    通过 ID 获取事件

    参数:
        event_id: 事件 ID

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": Event 对象数据
        }
    """
    try:
        from ...polymarket_api import GammaMarketsAPI

        with GammaMarketsAPI() as api:
            event = api.get_event_by_id(event_id)

            if not event:
                return jsonify({
                    'success': False,
                    'message': f'未找到 ID 为 {event_id} 的事件'
                }), 404

            # 将 Event 对象转换为字典
            event_data = event_to_dict(event)

            vlogger.info("API.POLYMARKET.EVENT.GET", msg="获取事件成功", extra={
                "event_id": event_id,
                "user": request.current_user['username']
            })

            return jsonify({
                'success': True,
                'message': '获取事件成功',
                'data': event_data
            }), 200

    except Exception as e:
        vlogger.error("API.POLYMARKET.EVENT.ERROR", msg="获取事件失败",
                     error_code="E-API-013", extra={"error": str(e), "event_id": event_id})
        return jsonify({
            'success': False,
            'message': f'获取事件失败: {str(e)}'
        }), 500


@polymarket_bp.route('/market/slug/<slug>', methods=['GET'])
@require_auth
def get_market_by_slug(slug):
    """
    通过 slug 获取市场

    参数:
        slug: 市场 slug

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": Market 对象数据
        }
    """
    try:
        from ...polymarket_api import GammaMarketsAPI

        with GammaMarketsAPI() as api:
            market = api.get_market_by_slug(slug)

            if not market:
                return jsonify({
                    'success': False,
                    'message': f'未找到 slug 为 {slug} 的市场'
                }), 404

            # 将 Market 对象转换为字典
            market_data = market_to_dict(market)

            vlogger.info("API.POLYMARKET.MARKET.GET", msg="获取市场成功", extra={
                "slug": slug,
                "market_id": market.id,
                "user": request.current_user['username']
            })

            return jsonify({
                'success': True,
                'message': '获取市场成功',
                'data': market_data
            }), 200

    except Exception as e:
        vlogger.error("API.POLYMARKET.MARKET.ERROR", msg="获取市场失败",
                     error_code="E-API-014", extra={"error": str(e), "slug": slug})
        return jsonify({
            'success': False,
            'message': f'获取市场失败: {str(e)}'
        }), 500


@polymarket_bp.route('/market/id/<market_id>', methods=['GET'])
@require_auth
def get_market_by_id(market_id):
    """
    通过 ID 获取市场

    参数:
        market_id: 市场 ID

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": Market 对象数据
        }
    """
    try:
        from ...polymarket_api import GammaMarketsAPI

        with GammaMarketsAPI() as api:
            market = api.get_market_by_id(market_id)

            if not market:
                return jsonify({
                    'success': False,
                    'message': f'未找到 ID 为 {market_id} 的市场'
                }), 404

            # 将 Market 对象转换为字典
            market_data = market_to_dict(market)

            vlogger.info("API.POLYMARKET.MARKET.GET", msg="获取市场成功", extra={
                "market_id": market_id,
                "user": request.current_user['username']
            })

            return jsonify({
                'success': True,
                'message': '获取市场成功',
                'data': market_data
            }), 200

    except Exception as e:
        vlogger.error("API.POLYMARKET.MARKET.ERROR", msg="获取市场失败",
                     error_code="E-API-014", extra={"error": str(e), "market_id": market_id})
        return jsonify({
            'success': False,
            'message': f'获取市场失败: {str(e)}'
        }), 500

