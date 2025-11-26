"""
数据库管理路由

提供数据库表查询、数据CRUD等数据库管理相关的API端点
"""

from flask import Blueprint, request, jsonify

from ...sys_configs.global_event_reg import vlogger
from ...sys_configs.config_manager import get_config_manager
from ..middleware.auth import require_auth

# 创建数据库路由蓝图
database_bp = Blueprint('database', __name__, url_prefix='/api/database')

# 获取配置管理器
config_manager = get_config_manager()


@database_bp.route('/tables', methods=['GET'])
@require_auth
def get_database_tables():
    """
    获取数据库中所有表的列表

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "tables": [
                    {
                        "name": "表名",
                        "type": "table",
                        "sql": "CREATE TABLE语句"
                    }
                ]
            }
        }
    """
    try:
        conn = config_manager.get_connection()
        cursor = conn.cursor()

        # 查询所有表
        cursor.execute("""
            SELECT name, type, sql
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)

        tables = []
        for row in cursor.fetchall():
            tables.append({
                'name': row[0],
                'type': row[1],
                'sql': row[2]
            })

        return jsonify({
            'success': True,
            'message': '获取表列表成功',
            'data': {
                'tables': tables
            }
        }), 200

    except Exception as e:
        vlogger.error("DB.TABLES.ERROR", msg="获取表列表失败",
                     error_code="E-API-007", extra={"error": str(e)})
        return jsonify({
            'success': False,
            'message': f'获取表列表失败: {str(e)}'
        }), 500


@database_bp.route('/schema/<table_name>', methods=['GET'])
@require_auth
def get_table_schema(table_name: str):
    """
    获取指定表的结构信息

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "columns": [
                    {
                        "cid": 列ID,
                        "name": "列名",
                        "type": "数据类型",
                        "notnull": 是否非空,
                        "dflt_value": 默认值,
                        "pk": 是否主键
                    }
                ]
            }
        }
    """
    try:
        conn = config_manager.get_connection()
        cursor = conn.cursor()

        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")

        columns = []
        for row in cursor.fetchall():
            columns.append({
                'cid': row[0],
                'name': row[1],
                'type': row[2],
                'notnull': bool(row[3]),
                'dflt_value': row[4],
                'pk': bool(row[5])
            })

        if not columns:
            return jsonify({
                'success': False,
                'message': f'表 {table_name} 不存在'
            }), 404

        return jsonify({
            'success': True,
            'message': '获取表结构成功',
            'data': {
                'columns': columns
            }
        }), 200

    except Exception as e:
        vlogger.error("DB.SCHEMA.ERROR", msg="获取表结构失败",
                     error_code="E-API-008", extra={"error": str(e), "table": table_name})
        return jsonify({
            'success': False,
            'message': f'获取表结构失败: {str(e)}'
        }), 500


@database_bp.route('/data/<table_name>', methods=['GET'])
@require_auth
def get_table_data(table_name: str):
    """
    获取指定表的数据

    查询参数:
        - page: 页码(默认1)
        - page_size: 每页数量(默认50)
        - order_by: 排序字段(可选)
        - order: 排序方向 asc/desc(默认desc)

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "rows": [...],
                "total": 总数,
                "page": 当前页,
                "page_size": 每页数量
            }
        }
    """
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        order_by = request.args.get('order_by', None)
        order = request.args.get('order', 'desc').upper()

        if order not in ['ASC', 'DESC']:
            order = 'DESC'

        conn = config_manager.get_connection()
        cursor = conn.cursor()

        # 验证表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """, (table_name,))

        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': f'表 {table_name} 不存在'
            }), 404

        # 获取表结构以确定默认排序字段
        if not order_by:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            # 优先使用 id 字段，如果没有则使用第一个主键字段，否则使用第一个字段
            order_by = None
            for col in columns:
                col_name = col[1]
                is_pk = col[5]
                if col_name.lower() == 'id':
                    order_by = 'id'
                    break
                if is_pk and not order_by:
                    order_by = col_name
            if not order_by and columns:
                order_by = columns[0][1]  # 使用第一个字段
            if not order_by:
                order_by = 'rowid'  # 最后的备选方案

        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]

        # 获取数据
        offset = (page - 1) * page_size
        query = f"SELECT * FROM {table_name} ORDER BY {order_by} {order} LIMIT ? OFFSET ?"
        cursor.execute(query, (page_size, offset))

        # 获取列名
        column_names = [description[0] for description in cursor.description]

        # 构建结果
        rows = []
        for row in cursor.fetchall():
            row_dict = {}
            for i, value in enumerate(row):
                row_dict[column_names[i]] = value
            rows.append(row_dict)

        return jsonify({
            'success': True,
            'message': '获取数据成功',
            'data': {
                'rows': rows,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        }), 200

    except Exception as e:
        vlogger.error("DB.DATA.ERROR", msg="获取表数据失败",
                     error_code="E-API-009", extra={"error": str(e), "table": table_name})
        return jsonify({
            'success': False,
            'message': f'获取表数据失败: {str(e)}'
        }), 500


@database_bp.route('/row/<table_name>', methods=['POST'])
@require_auth
def create_table_row(table_name: str):
    """
    在指定表中创建新行

    请求体:
        {
            "data": {
                "column1": "value1",
                "column2": "value2"
            }
        }

    响应:
        {
            "success": true/false,
            "message": "消息",
            "data": {
                "id": 新创建的行ID
            }
        }
    """
    try:
        data = request.get_json()
        if not data or 'data' not in data:
            return jsonify({
                'success': False,
                'message': '请求数据格式错误'
            }), 400

        row_data = data['data']

        conn = config_manager.get_connection()
        cursor = conn.cursor()

        # 构建INSERT语句
        columns = ', '.join(row_data.keys())
        placeholders = ', '.join(['?' for _ in row_data])
        values = list(row_data.values())

        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(query, values)
        conn.commit()

        new_id = cursor.lastrowid

        vlogger.info("DB.ROW.CREATE", msg="创建数据行成功", extra={
            "table": table_name,
            "id": new_id,
            "user": request.current_user['username']
        })

        return jsonify({
            'success': True,
            'message': '创建成功',
            'data': {
                'id': new_id
            }
        }), 201

    except Exception as e:
        vlogger.error("DB.ROW.CREATE.ERROR", msg="创建数据行失败",
                     error_code="E-API-010", extra={"error": str(e), "table": table_name})
        return jsonify({
            'success': False,
            'message': f'创建失败: {str(e)}'
        }), 500


@database_bp.route('/row/<table_name>/<int:row_id>', methods=['PUT'])
@require_auth
def update_table_row(table_name: str, row_id: int):
    """
    更新指定表中的行

    请求体:
        {
            "data": {
                "column1": "new_value1",
                "column2": "new_value2"
            }
        }

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        data = request.get_json()
        if not data or 'data' not in data:
            return jsonify({
                'success': False,
                'message': '请求数据格式错误'
            }), 400

        row_data = data['data']

        conn = config_manager.get_connection()
        cursor = conn.cursor()

        # 构建UPDATE语句
        set_clause = ', '.join([f"{k} = ?" for k in row_data.keys()])
        values = list(row_data.values())
        values.append(row_id)

        query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': f'未找到ID为 {row_id} 的记录'
            }), 404

        vlogger.info("DB.ROW.UPDATE", msg="更新数据行成功", extra={
            "table": table_name,
            "id": row_id,
            "user": request.current_user['username']
        })

        return jsonify({
            'success': True,
            'message': '更新成功'
        }), 200

    except Exception as e:
        vlogger.error("DB.ROW.UPDATE.ERROR", msg="更新数据行失败",
                     error_code="E-API-011", extra={"error": str(e), "table": table_name, "id": row_id})
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@database_bp.route('/row/<table_name>/<int:row_id>', methods=['DELETE'])
@require_auth
def delete_table_row(table_name: str, row_id: int):
    """
    删除指定表中的行

    响应:
        {
            "success": true/false,
            "message": "消息"
        }
    """
    try:
        conn = config_manager.get_connection()
        cursor = conn.cursor()

        query = f"DELETE FROM {table_name} WHERE id = ?"
        cursor.execute(query, (row_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': f'未找到ID为 {row_id} 的记录'
            }), 404

        vlogger.info("DB.ROW.DELETE", msg="删除数据行成功", extra={
            "table": table_name,
            "id": row_id,
            "user": request.current_user['username']
        })

        return jsonify({
            'success': True,
            'message': '删除成功'
        }), 200

    except Exception as e:
        vlogger.error("DB.ROW.DELETE.ERROR", msg="删除数据行失败",
                     error_code="E-API-012", extra={"error": str(e), "table": table_name, "id": row_id})
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500

