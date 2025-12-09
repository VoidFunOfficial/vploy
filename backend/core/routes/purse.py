"""
钱包管理路由

提供钱包状态查询、每日收益记录管理等API端点
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from ...purse import get_purse
from ...sys_configs.global_event_reg import vlogger
from ..middleware.auth import require_auth

# 创建钱包路由蓝图
purse_bp = Blueprint('purse', __name__, url_prefix='/api/purse')

# 获取钱包实例
purse = get_purse()


@purse_bp.route('/status', methods=['GET'])
@require_auth
def get_purse_status():
    """
    获取钱包当前状态

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "total_fund": 总资金,
                "locked_fund": 锁定资金,
                "available_cash": 可用现金,
                "loss": 总亏损,
                "expect_profit": 预期盈利,
                "real_profit": 实际盈利,
                "success_market": 成功市场数,
                "lost_market": 失败市场数,
                "updated_at": 更新时间
            }
        }
    """
    try:
        status = purse.get_status()

        return jsonify({
            'success': True,
            'message': '获取钱包状态成功',
            'data': status
        }), 200

    except Exception as e:
        vlogger.error("PURSE.STATUS.ERROR", msg="获取钱包状态失败",
                     error_code="E-API-PURSE-001", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取钱包状态失败: {str(e)}'
        }), 500


@purse_bp.route('/summary', methods=['GET'])
@require_auth
def get_profit_loss_summary():
    """
    获取盈亏汇总信息

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "loss": 总亏损,
                "expect_profit": 预期盈利,
                "real_profit": 实际盈利,
                "net_profit": 净盈利,
                "success_market": 成功市场数,
                "lost_market": 失败市场数,
                "total_market": 总市场数,
                "win_rate": 胜率
            }
        }
    """
    try:
        summary = purse.get_profit_loss_summary()

        return jsonify({
            'success': True,
            'message': '获取盈亏汇总成功',
            'data': summary
        }), 200

    except Exception as e:
        vlogger.error("PURSE.SUMMARY.ERROR", msg="获取盈亏汇总失败",
                     error_code="E-API-PURSE-002", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取盈亏汇总失败: {str(e)}'
        }), 500


@purse_bp.route('/status', methods=['PUT'])
@require_auth
def update_purse_status():
    """
    更新钱包状态

    请求体:
        {
            "total_fund": 总资金 (可选),
            "locked_fund": 锁定资金 (可选),
            "available_cash": 可用现金 (可选),
            "loss": 总亏损 (可选),
            "expect_profit": 预期盈利 (可选),
            "real_profit": 实际盈利 (可选),
            "success_market": 成功市场数 (可选),
            "lost_market": 失败市场数 (可选)
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

        # 调用purse的update_status方法
        success = purse.update_status(**data)

        if success:
            vlogger.info("PURSE.STATUS.UPDATE", msg="钱包状态更新成功",
                        extra={"updated_fields": list(data.keys()),
                               "user": request.current_user['username']})
            return jsonify({
                'success': True,
                'message': '钱包状态更新成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '钱包状态更新失败'
            }), 400

    except Exception as e:
        vlogger.error("PURSE.STATUS.UPDATE.ERROR", msg="更新钱包状态失败",
                     error_code="E-API-PURSE-008", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'更新钱包状态失败: {str(e)}'
        }), 500


@purse_bp.route('/daily-records', methods=['GET'])
@require_auth
def get_daily_records():
    """
    获取每日收益记录列表

    查询参数:
        - start_date: 开始日期 (YYYY-MM-DD, 可选)
        - end_date: 结束日期 (YYYY-MM-DD, 可选)
        - limit: 返回记录数量限制 (可选)

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": [
                {
                    "record_date": "2025-12-07",
                    "expect_profit": 预期收益,
                    "real_profit": 实际收益,
                    "total_fund": 总资金,
                    "success_market": 成功市场数,
                    "lost_market": 失败市场数,
                    "notes": 备注,
                    "created_at": 创建时间,
                    "updated_at": 更新时间
                }
            ]
        }
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int)

        records = purse.get_daily_records(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return jsonify({
            'success': True,
            'message': '获取每日收益记录成功',
            'data': records
        }), 200

    except Exception as e:
        vlogger.error("PURSE.DAILY.GET.ERROR", msg="获取每日收益记录失败",
                     error_code="E-API-PURSE-003", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取每日收益记录失败: {str(e)}'
        }), 500


@purse_bp.route('/daily-record/<record_date>', methods=['GET'])
@require_auth
def get_daily_record(record_date: str):
    """
    获取指定日期的收益记录

    参数:
        record_date: 记录日期 (YYYY-MM-DD)

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "record_date": "2025-12-07",
                "expect_profit": 预期收益,
                "real_profit": 实际收益,
                "total_fund": 总资金,
                "success_market": 成功市场数,
                "lost_market": 失败市场数,
                "notes": 备注,
                "created_at": 创建时间,
                "updated_at": 更新时间
            }
        }
    """
    try:
        record = purse.get_daily_record(record_date)

        if record is None:
            return jsonify({
                'success': False,
                'message': '未找到该日期的记录'
            }), 404

        return jsonify({
            'success': True,
            'message': '获取每日收益记录成功',
            'data': record
        }), 200

    except Exception as e:
        vlogger.error("PURSE.DAILY.GET.ERROR", msg="获取每日收益记录失败",
                     error_code="E-API-PURSE-004", extra={"error": str(e), "date": record_date})
        return jsonify({
            'success': False,
            'message': f'获取每日收益记录失败: {str(e)}'
        }), 500


@purse_bp.route('/daily-record', methods=['POST'])
@require_auth
def add_daily_record():
    """
    添加每日收益记录

    请求体:
        {
            "record_date": "2025-12-07",
            "expect_profit": 预期收益,
            "real_profit": 实际收益,
            "total_fund": 总资金 (可选),
            "success_market": 成功市场数 (可选),
            "lost_market": 失败市场数 (可选),
            "notes": 备注 (可选)
        }

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()

        if not data or 'record_date' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: record_date'
            }), 400

        if 'expect_profit' not in data or 'real_profit' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: expect_profit 或 real_profit'
            }), 400

        success = purse.add_daily_record(
            record_date=data['record_date'],
            expect_profit=data['expect_profit'],
            real_profit=data['real_profit'],
            total_fund=data.get('total_fund'),
            success_market=data.get('success_market'),
            lost_market=data.get('lost_market'),
            notes=data.get('notes')
        )

        if success:
            return jsonify({
                'success': True,
                'message': '添加每日收益记录成功'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': '添加每日收益记录失败,该日期的记录可能已存在'
            }), 400

    except Exception as e:
        vlogger.error("PURSE.DAILY.ADD.ERROR", msg="添加每日收益记录失败",
                     error_code="E-API-PURSE-005", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'添加每日收益记录失败: {str(e)}'
        }), 500





@purse_bp.route('/daily-record/<record_date>', methods=['PUT'])
@require_auth
def update_daily_record(record_date: str):
    """
    更新每日收益记录

    参数:
        record_date: 记录日期 (YYYY-MM-DD)

    请求体:
        {
            "expect_profit": 预期收益 (可选),
            "real_profit": 实际收益 (可选),
            "total_fund": 总资金 (可选),
            "success_market": 成功市场数 (可选),
            "lost_market": 失败市场数 (可选),
            "notes": 备注 (可选)
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

        success = purse.update_daily_record(
            record_date=record_date,
            expect_profit=data.get('expect_profit'),
            real_profit=data.get('real_profit'),
            total_fund=data.get('total_fund'),
            success_market=data.get('success_market'),
            lost_market=data.get('lost_market'),
            notes=data.get('notes')
        )

        if success:
            return jsonify({
                'success': True,
                'message': '更新每日收益记录成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '更新每日收益记录失败,未找到该日期的记录'
            }), 404

    except Exception as e:
        vlogger.error("PURSE.DAILY.UPDATE.ERROR", msg="更新每日收益记录失败",
                     error_code="E-API-PURSE-006", extra={"error": str(e), "date": record_date})
        return jsonify({
            'success': False,
            'message': f'更新每日收益记录失败: {str(e)}'
        }), 500


@purse_bp.route('/daily-record/<record_date>', methods=['DELETE'])
@require_auth
def delete_daily_record(record_date: str):
    """
    删除每日收益记录

    参数:
        record_date: 记录日期 (YYYY-MM-DD)

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        success = purse.delete_daily_record(record_date)

        if success:
            return jsonify({
                'success': True,
                'message': '删除每日收益记录成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '删除每日收益记录失败,未找到该日期的记录'
            }), 404

    except Exception as e:
        vlogger.error("PURSE.DAILY.DELETE.ERROR", msg="删除每日收益记录失败",
                     error_code="E-API-PURSE-007", extra={"error": str(e), "date": record_date})
        return jsonify({
            'success': False,
            'message': f'删除每日收益记录失败: {str(e)}'
        }), 500
