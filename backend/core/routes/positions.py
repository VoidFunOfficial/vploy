"""
持仓监控路由

提供持仓、订单、价格历史数据查询的API端点
"""

from flask import Blueprint, request, jsonify
from typing import Optional

from ...sys_configs.global_event_reg import vlogger
from ..middleware.auth import require_auth
from ...position_listener import (
    get_position,
    get_positions_by_market,
    get_open_positions,
    get_position_summary,
    get_order,
    get_pending_orders,
    monitor_position,
    monitor_order,
    Position,
    Order
)
from ...polymarket_api import PolymarketOrderbookClient, GammaMarketsAPI
from ...position_listener.database import PositionDatabase

# 创建持仓路由蓝图
positions_bp = Blueprint('positions', __name__, url_prefix='/api/positions')


def _get_token_id_for_market(market_id: str, side: str = "YES") -> Optional[str]:
    """
    获取市场的token_id

    优先从orders表获取,如果没有则从Gamma API获取

    参数:
        market_id: 市场ID
        side: 交易方向(YES/NO),默认YES

    返回:
        str: token_id,如果获取失败返回None
    """
    try:
        # 1. 尝试从orders表获取token_id
        db = PositionDatabase()
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT token_id FROM orders WHERE market_id = ? LIMIT 1",
            (market_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return row['token_id']

        # 2. 从Gamma API获取market信息
        with GammaMarketsAPI() as api:
            market = api.get_market(market_id)
            if market and market.clobTokenIds:
                # YES对应index 0, NO对应index 1
                index = 0 if side == "YES" else 1
                if len(market.clobTokenIds) > index:
                    return market.clobTokenIds[index]

        vlogger.warn("POSITIONS.TOKEN_ID.NOT_FOUND",
                    msg="无法获取市场的token_id",
                    extra={"market_id": market_id})
        return None

    except Exception as e:
        vlogger.error("POSITIONS.TOKEN_ID.ERROR",
                     msg="获取token_id失败",
                     error_code="E-POSITIONS-010",
                     extra={"market_id": market_id, "error": str(e)})
        return None


@positions_bp.route('/summary', methods=['GET'])
@require_auth
def get_summary():
    """
    获取持仓汇总信息
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "total_positions": 总持仓数,
                "total_invest": 总投资金额,
                "total_pnl": 总盈亏,
                "positions": [持仓列表]
            }
        }
    """
    try:
        from ...position_listener import get_position_summary
        summary = get_position_summary()
        
        vlogger.info("POSITIONS.SUMMARY.QUERY", msg="查询持仓汇总", extra={
            "total_positions": summary.get("total_positions", 0)
        })
        
        return jsonify({
            'success': True,
            'message': '获取持仓汇总成功',
            'data': summary
        }), 200
        
    except Exception as e:
        vlogger.error("POSITIONS.SUMMARY.ERROR", msg="获取持仓汇总失败",
                     error_code="E-POSITIONS-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取持仓汇总失败: {str(e)}'
        }), 500


@positions_bp.route('/list', methods=['GET'])
@require_auth
def get_positions_list():
    """
    获取持仓列表
    
    查询参数:
        market_id: 市场ID（可选，用于筛选特定市场的持仓）
        status: 持仓状态（可选，open/closed/monitoring）
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "positions": [持仓列表],
                "total": 总数
            }
        }
    """
    try:
        market_id = request.args.get('market_id')
        status = request.args.get('status')
        
        if market_id:
            positions = get_positions_by_market(market_id)
        elif status == 'open':
            positions = get_open_positions()
        else:
            # 获取所有持仓
            from ...position_listener import _db
            conn = _db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions ORDER BY create_time DESC")
            rows = cursor.fetchall()
            positions = [_db._row_to_position(row) for row in rows]
            conn.close()
        
        positions_data = [p.to_dict() for p in positions]
        
        vlogger.info("POSITIONS.LIST.QUERY", msg="查询持仓列表", extra={
            "market_id": market_id,
            "status": status,
            "total": len(positions_data)
        })
        
        return jsonify({
            'success': True,
            'message': '获取持仓列表成功',
            'data': {
                'positions': positions_data,
                'total': len(positions_data)
            }
        }), 200
        
    except Exception as e:
        vlogger.error("POSITIONS.LIST.ERROR", msg="获取持仓列表失败",
                     error_code="E-POSITIONS-002", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取持仓列表失败: {str(e)}'
        }), 500


@positions_bp.route('/<int:position_id>', methods=['GET'])
@require_auth
def get_position_detail(position_id: int):
    """
    获取单个持仓详情
    
    参数:
        position_id: 持仓ID
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": 持仓详情
        }
    """
    try:
        position = get_position(position_id)
        
        if not position:
            return jsonify({
                'success': False,
                'message': f'持仓不存在: {position_id}'
            }), 404
        
        vlogger.info("POSITIONS.DETAIL.QUERY", msg="查询持仓详情", extra={
            "position_id": position_id
        })
        
        return jsonify({
            'success': True,
            'message': '获取持仓详情成功',
            'data': position.to_dict()
        }), 200
        
    except Exception as e:
        vlogger.error("POSITIONS.DETAIL.ERROR", msg="获取持仓详情失败",
                     error_code="E-POSITIONS-003", extra={
                         "position_id": position_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'获取持仓详情失败: {str(e)}'
        }), 500


@positions_bp.route('/<int:position_id>/monitor', methods=['POST'])
@require_auth
def monitor_position_endpoint(position_id: int):
    """
    手动监控单个持仓

    参数:
        position_id: 持仓ID

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": 监控结果
        }
    """
    try:
        result = monitor_position(position_id)

        vlogger.info("POSITIONS.MONITOR", msg="手动监控持仓", extra={
            "position_id": position_id,
            "result": result
        })

        return jsonify({
            'success': True,
            'message': '监控持仓成功',
            'data': result
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.MONITOR.ERROR", msg="监控持仓失败",
                     error_code="E-POSITIONS-004", extra={
                         "position_id": position_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'监控持仓失败: {str(e)}'
        }), 500


@positions_bp.route('/<int:position_id>', methods=['PUT'])
@require_auth
def update_position_endpoint(position_id: int):
    """
    更新持仓信息

    参数:
        position_id: 持仓ID

    请求体:
        {
            "current_price": 当前价格（可选）,
            "status": 状态（可选，open/closed/monitoring）,
            "settlement_result": 结算结果（可选，YES/NO）,
            "settlement_payout": 结算收益（可选）
        }

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()

        position = get_position(position_id)
        if not position:
            return jsonify({
                'success': False,
                'message': f'持仓不存在: {position_id}'
            }), 404

        # 更新价格
        if 'current_price' in data:
            from ...position_listener import update_position_price
            update_position_price(position_id, float(data['current_price']))

        # 更新状态
        if 'status' in data:
            from ...position_listener.models import PositionStatus
            position.status = PositionStatus(data['status'])

        # 结算持仓
        if 'settlement_result' in data and 'settlement_payout' in data:
            from ...position_listener import settle_position
            settle_position(
                position_id,
                data['settlement_result'],
                float(data['settlement_payout'])
            )

        vlogger.info("POSITIONS.UPDATE", msg="更新持仓", extra={
            "position_id": position_id,
            "updates": data
        })

        return jsonify({
            'success': True,
            'message': '更新持仓成功'
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.UPDATE.ERROR", msg="更新持仓失败",
                     error_code="E-POSITIONS-011", extra={
                         "position_id": position_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'更新持仓失败: {str(e)}'
        }), 500


@positions_bp.route('/<int:position_id>', methods=['DELETE'])
@require_auth
def delete_position_endpoint(position_id: int):
    """
    删除持仓记录

    参数:
        position_id: 持仓ID

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        position = get_position(position_id)
        if not position:
            return jsonify({
                'success': False,
                'message': f'持仓不存在: {position_id}'
            }), 404

        # 删除持仓记录
        db = PositionDatabase()
        conn = db._get_connection()
        cursor = conn.cursor()

        try:
            # 先删除关联的交易记录
            cursor.execute("DELETE FROM trades WHERE position_id = ?", (position_id,))
            # 再删除持仓记录
            cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
            conn.commit()

            vlogger.info("POSITIONS.DELETE", msg="删除持仓", extra={
                "position_id": position_id
            })

            return jsonify({
                'success': True,
                'message': '删除持仓成功'
            }), 200

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    except Exception as e:
        vlogger.error("POSITIONS.DELETE.ERROR", msg="删除持仓失败",
                     error_code="E-POSITIONS-012", extra={
                         "position_id": position_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'删除持仓失败: {str(e)}'
        }), 500


@positions_bp.route('/orders', methods=['GET'])
@require_auth
def get_orders_list():
    """
    获取订单列表
    
    查询参数:
        status: 订单状态（可选，pending/filled/cancelled/failed）
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "orders": [订单列表],
                "total": 总数
            }
        }
    """
    try:
        status = request.args.get('status')
        
        if status == 'pending':
            orders = get_pending_orders()
        else:
            # 获取所有订单
            from ...position_listener import _db
            conn = _db._get_connection()
            cursor = conn.cursor()
            
            if status:
                cursor.execute("SELECT * FROM orders WHERE status = ? ORDER BY create_time DESC", (status,))
            else:
                cursor.execute("SELECT * FROM orders ORDER BY create_time DESC")
            
            rows = cursor.fetchall()
            orders = [_db._row_to_order(row) for row in rows]
            conn.close()
        
        orders_data = [o.to_dict() for o in orders]
        
        vlogger.info("POSITIONS.ORDERS.QUERY", msg="查询订单列表", extra={
            "status": status,
            "total": len(orders_data)
        })
        
        return jsonify({
            'success': True,
            'message': '获取订单列表成功',
            'data': {
                'orders': orders_data,
                'total': len(orders_data)
            }
        }), 200
        
    except Exception as e:
        vlogger.error("POSITIONS.ORDERS.ERROR", msg="获取订单列表失败",
                     error_code="E-POSITIONS-005", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取订单列表失败: {str(e)}'
        }), 500


@positions_bp.route('/orders/<order_id>', methods=['GET'])
@require_auth
def get_order_detail(order_id: str):
    """
    获取单个订单详情
    
    参数:
        order_id: 订单ID
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": 订单详情
        }
    """
    try:
        order = get_order(order_id)
        
        if not order:
            return jsonify({
                'success': False,
                'message': f'订单不存在: {order_id}'
            }), 404
        
        vlogger.info("POSITIONS.ORDER.DETAIL", msg="查询订单详情", extra={
            "order_id": order_id
        })
        
        return jsonify({
            'success': True,
            'message': '获取订单详情成功',
            'data': order.to_dict()
        }), 200
        
    except Exception as e:
        vlogger.error("POSITIONS.ORDER.DETAIL.ERROR", msg="获取订单详情失败",
                     error_code="E-POSITIONS-006", extra={
                         "order_id": order_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'获取订单详情失败: {str(e)}'
        }), 500


@positions_bp.route('/orders/<order_id>/monitor', methods=['POST'])
@require_auth
def monitor_order_endpoint(order_id: str):
    """
    手动监控单个订单

    参数:
        order_id: 订单ID

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": 监控结果
        }
    """
    try:
        result = monitor_order(order_id)

        vlogger.info("POSITIONS.ORDER.MONITOR", msg="手动监控订单", extra={
            "order_id": order_id,
            "result": result
        })

        return jsonify({
            'success': True,
            'message': '监控订单成功',
            'data': result
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.ORDER.MONITOR.ERROR", msg="监控订单失败",
                     error_code="E-POSITIONS-007", extra={
                         "order_id": order_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'监控订单失败: {str(e)}'
        }), 500


@positions_bp.route('/orders/<order_id>', methods=['PUT'])
@require_auth
def update_order_endpoint(order_id: str):
    """
    更新订单信息

    参数:
        order_id: 订单ID

    请求体:
        {
            "status": 状态（可选，pending/filled/cancelled/failed）,
            "filled_size": 已成交数量（可选）
        }

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()

        order = get_order(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': f'订单不存在: {order_id}'
            }), 404

        # 更新订单状态
        if 'status' in data or 'filled_size' in data:
            from ...position_listener.models import OrderStatus
            from ...position_listener import _db

            status = OrderStatus(data['status']) if 'status' in data else order.status
            filled_size = float(data['filled_size']) if 'filled_size' in data else order.filled_size

            _db.update_order_status(order_id, status, filled_size)

        vlogger.info("POSITIONS.ORDER.UPDATE", msg="更新订单", extra={
            "order_id": order_id,
            "updates": data
        })

        return jsonify({
            'success': True,
            'message': '更新订单成功'
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.ORDER.UPDATE.ERROR", msg="更新订单失败",
                     error_code="E-POSITIONS-013", extra={
                         "order_id": order_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'更新订单失败: {str(e)}'
        }), 500


@positions_bp.route('/orders/<order_id>', methods=['DELETE'])
@require_auth
def delete_order_endpoint(order_id: str):
    """
    删除订单记录

    参数:
        order_id: 订单ID

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        order = get_order(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': f'订单不存在: {order_id}'
            }), 404

        # 删除订单记录
        from ...position_listener import _db
        success = _db.delete_order(order_id)

        if success:
            vlogger.info("POSITIONS.ORDER.DELETE", msg="删除订单", extra={
                "order_id": order_id
            })

            return jsonify({
                'success': True,
                'message': '删除订单成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '删除订单失败'
            }), 500

    except Exception as e:
        vlogger.error("POSITIONS.ORDER.DELETE.ERROR", msg="删除订单失败",
                     error_code="E-POSITIONS-014", extra={
                         "order_id": order_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'删除订单失败: {str(e)}'
        }), 500


@positions_bp.route('/market/<market_id>/price-history', methods=['GET'])
@require_auth
def get_market_price_history(market_id: str):
    """
    获取市场价格历史数据

    参数:
        market_id: 市场ID(会自动转换为token_id)

    查询参数:
        interval: 时间间隔（1h/6h/1d/1w/1m/max），默认1d
        fidelity: 数据分辨率（分钟），默认60
        side: 交易方向(YES/NO),默认YES

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "market_id": 市场ID,
                "history": [
                    {"t": 时间戳, "p": 价格},
                    ...
                ]
            }
        }
    """
    try:
        interval = request.args.get('interval', '1d')
        fidelity = int(request.args.get('fidelity', 60))
        side = request.args.get('side', 'YES')

        # 获取token_id
        token_id = _get_token_id_for_market(market_id, side)
        if not token_id:
            return jsonify({
                'success': False,
                'message': '无法获取市场的token_id'
            }), 404

        # 使用Orderbook API获取价格历史
        with PolymarketOrderbookClient() as client:
            history_data = client.get_prices_history(
                market=token_id,  # 使用token_id
                interval=interval,
                fidelity=fidelity
            )

        vlogger.info("POSITIONS.PRICE_HISTORY.QUERY", msg="查询价格历史", extra={
            "market_id": market_id,
            "interval": interval,
            "fidelity": fidelity,
            "data_points": len(history_data.get('history', []))
        })

        return jsonify({
            'success': True,
            'message': '获取价格历史成功',
            'data': {
                'market_id': market_id,
                'history': history_data.get('history', [])
            }
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.PRICE_HISTORY.ERROR", msg="获取价格历史失败",
                     error_code="E-POSITIONS-008", extra={
                         "market_id": market_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'获取价格历史失败: {str(e)}'
        }), 500


@positions_bp.route('/market/<market_id>/positions', methods=['GET'])
@require_auth
def get_market_positions(market_id: str):
    """
    获取指定市场的所有持仓及价格历史（用于绘制买点）

    参数:
        market_id: 市场ID

    查询参数:
        interval: 时间间隔（1h/6h/1d/1w/1m/max），默认1d
        fidelity: 数据分辨率（分钟），默认60

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "market_id": 市场ID,
                "positions": [持仓列表],
                "price_history": [价格历史],
                "current_price": 当前价格
            }
        }
    """
    try:
        interval = request.args.get('interval', '1d')
        fidelity = int(request.args.get('fidelity', 60))

        # 获取该市场的所有持仓
        positions = get_positions_by_market(market_id)
        positions_data = [p.to_dict() for p in positions]

        # 获取价格历史
        price_history = []
        current_price = None

        if positions:
            # 获取token_id(使用第一个持仓的side)
            first_position_side = positions[0].side if positions else "YES"
            token_id = _get_token_id_for_market(market_id, first_position_side)

            if token_id:
                try:
                    with PolymarketOrderbookClient() as client:
                        import time

                        # 根据interval计算时间范围
                        end_ts = int(time.time())
                        interval_seconds = {
                            '1h': 3600,
                            '6h': 21600,
                            '1d': 86400,
                            '1w': 604800,
                            '1m': 2592000,
                            'max': 31536000  # 1年作为max
                        }
                        start_ts = end_ts - interval_seconds.get(interval, 86400)

                        history_data = client.get_prices_history(
                            market=token_id,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            fidelity=fidelity
                        )
                        price_history = history_data.get('history', [])

                        # 获取当前价格
                        try:
                            current_price = client.get_midpoint(token_id)  # 使用token_id
                        except:
                            if price_history:
                                current_price = price_history[-1].get('p')
                except Exception as e:
                    vlogger.warn("POSITIONS.MARKET.PRICE_HISTORY.ERROR",
                               msg="获取价格历史失败，继续返回持仓数据",
                               extra={"market_id": market_id, "token_id": token_id, "error": str(e)})
            else:
                vlogger.warn("POSITIONS.MARKET.NO_TOKEN_ID",
                           msg="无法获取token_id，跳过价格历史查询",
                           extra={"market_id": market_id})

        vlogger.info("POSITIONS.MARKET.QUERY", msg="查询市场持仓和价格", extra={
            "market_id": market_id,
            "positions_count": positions_data,
            "price_points": price_history
        })

        return jsonify({
            'success': True,
            'message': '获取市场数据成功',
            'data': {
                'market_id': market_id,
                'positions': positions_data,
                'price_history': price_history,
                'current_price': current_price
            }
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.MARKET.ERROR", msg="获取市场数据失败",
                     error_code="E-POSITIONS-009", extra={
                         "market_id": market_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'获取市场数据失败: {str(e)}'
        }), 500


@positions_bp.route('/<int:position_id>/price-curve', methods=['GET'])
@require_auth
def get_position_price_curve(position_id: int):
    """
    获取单个持仓的价格曲线数据（以购买时刻为基准）

    参数:
        position_id: 持仓ID

    查询参数:
        before_hours: 购买前的小时数，默认24
        after_hours: 购买后的小时数，默认24
        fidelity: 数据分辨率（分钟），默认60

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "position": 持仓信息,
                "purchase_time": 购买时刻时间戳,
                "price_history": [
                    {"t": 时间戳, "p": 价格},
                    ...
                ],
                "current_price": 当前价格
            }
        }
    """
    try:
        from datetime import datetime
        import time

        # 获取查询参数
        before_hours = int(request.args.get('before_hours', 24))
        after_hours = int(request.args.get('after_hours', 24))
        fidelity = int(request.args.get('fidelity', 60))

        # 获取持仓信息
        position = get_position(position_id)
        if not position:
            return jsonify({
                'success': False,
                'message': f'持仓不存在: {position_id}'
            }), 404

        # 获取购买时刻时间戳
        if position.create_time:
            purchase_time = int(position.create_time.timestamp())
        else:
            return jsonify({
                'success': False,
                'message': '持仓缺少创建时间信息'
            }), 400

        # 计算时间范围（以购买时刻为基准）
        start_ts = purchase_time - (before_hours * 3600)
        end_ts = purchase_time + (after_hours * 3600)
        current_ts = int(time.time())

        # 如果end_ts超过当前时间，调整为当前时间
        if end_ts > current_ts:
            end_ts = current_ts

        # 获取token_id
        token_id = _get_token_id_for_market(position.market_id, position.side)
        if not token_id:
            return jsonify({
                'success': False,
                'message': '无法获取市场的token_id'
            }), 404

        # 获取价格历史数据
        price_history = []
        current_price = None

        try:
            with PolymarketOrderbookClient() as client:
                history_data = client.get_prices_history(
                    market=token_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    fidelity=fidelity
                )
                price_history = history_data.get('history', [])

                # 获取当前价格
                try:
                    current_price = client.get_midpoint(token_id)
                except:
                    if price_history:
                        current_price = price_history[-1].get('p')
        except Exception as e:
            vlogger.error("POSITIONS.PRICE_CURVE.API_ERROR",
                         msg="获取价格历史失败",
                         error_code="E-POSITIONS-011",
                         extra={
                             "position_id": position_id,
                             "token_id": token_id,
                             "error": str(e)
                         })
            return jsonify({
                'success': False,
                'message': f'获取价格历史失败: {str(e)}'
            }), 500

        vlogger.info("POSITIONS.PRICE_CURVE.QUERY", msg="查询持仓价格曲线", extra={
            "position_id": position_id,
            "purchase_time": purchase_time,
            "before_hours": before_hours,
            "after_hours": after_hours,
            "data_points": len(price_history)
        })

        return jsonify({
            'success': True,
            'message': '获取价格曲线成功',
            'data': {
                'position': position.to_dict(),
                'purchase_time': purchase_time,
                'price_history': price_history,
                'current_price': current_price
            }
        }), 200

    except Exception as e:
        vlogger.error("POSITIONS.PRICE_CURVE.ERROR", msg="获取价格曲线失败",
                     error_code="E-POSITIONS-010", extra={
                         "position_id": position_id,
                         "error": str(e)
                     })
        return jsonify({
            'success': False,
            'message': f'获取价格曲线失败: {str(e)}'
        }), 500

