"""
持仓监听配置管理模块

提供持仓监听列表的数据库操作功能。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .config_manager import get_config_manager


def add_position_listen(
    market_id: str,
    buy_price: float,
    buy_side: str,
    marks: Optional[str] = None,
    shares: Optional[float] = None,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    添加持仓监听记录

    参数:
        market_id: 市场ID
        buy_price: 买入价格
        buy_side: 买入方向 (YES/NO)
        marks: 标记/备注信息
        shares: 持仓份额
        db_path: 数据库文件路径

    返回:
        bool: 是否添加成功
    """
    try:
        config_manager = get_config_manager(db_path)

        # 验证buy_side参数
        if buy_side not in ['YES', 'NO']:
            raise ValueError(f"buy_side必须是'YES'或'NO', 当前值: {buy_side}")

        # 验证buy_price参数
        if not (0.0 < buy_price < 1.0):
            raise ValueError(f"buy_price必须在0到1之间, 当前值: {buy_price}")

        # 验证shares参数
        if shares is not None and shares < 0:
            raise ValueError(f"shares必须大于等于0, 当前值: {shares}")

        query = """
            INSERT INTO position_listen_list (market_id, marks, buy_price, buy_side, shares, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """
        params = (market_id, marks, buy_price, buy_side, shares)

        config_manager.execute_update(query, params)
        return True

    except Exception as e:
        print(f"[PositionListenConfig] 添加监听记录失败: {str(e)}")
        return False


def get_position_listen_list(
    market_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db_path: str = "backend/sys_configs/system_config.db"
) -> List[Dict[str, Any]]:
    """
    获取持仓监听列表
    
    参数:
        market_id: 市场ID (可选，用于筛选特定市场)
        is_active: 是否激活 (可选，True=仅激活, False=仅未激活, None=全部)
        db_path: 数据库文件路径
        
    返回:
        List[Dict]: 监听记录列表
    """
    try:
        config_manager = get_config_manager(db_path)
        
        # 构建查询语句
        query = "SELECT * FROM position_listen_list WHERE 1=1"
        params = []
        
        if market_id is not None:
            query += " AND market_id = ?"
            params.append(market_id)
        
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)
        
        query += " ORDER BY created_at DESC"
        
        rows = config_manager.execute_query(query, tuple(params))
        
        # 转换为字典列表
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'market_id': row['market_id'],
                'marks': row['marks'],
                'buy_price': row['buy_price'],
                'buy_side': row['buy_side'],
                'shares': row['shares'],
                'is_active': bool(row['is_active']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })

        return result
        
    except Exception as e:
        print(f"[PositionListenConfig] 获取监听列表失败: {str(e)}")
        return []


def update_position_listen(
    listen_id: int,
    marks: Optional[str] = None,
    buy_price: Optional[float] = None,
    buy_side: Optional[str] = None,
    shares: Optional[float] = None,
    is_active: Optional[bool] = None,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    更新持仓监听记录

    参数:
        listen_id: 监听记录ID
        marks: 标记/备注信息 (可选)
        buy_price: 买入价格 (可选)
        buy_side: 买入方向 (可选)
        shares: 持仓份额 (可选)
        is_active: 是否激活 (可选)
        db_path: 数据库文件路径

    返回:
        bool: 是否更新成功
    """
    try:
        config_manager = get_config_manager(db_path)

        # 构建更新语句
        updates = []
        params = []

        if marks is not None:
            updates.append("marks = ?")
            params.append(marks)

        if buy_price is not None:
            if not (0.0 < buy_price < 1.0):
                raise ValueError(f"buy_price必须在0到1之间, 当前值: {buy_price}")
            updates.append("buy_price = ?")
            params.append(buy_price)

        if buy_side is not None:
            if buy_side not in ['YES', 'NO']:
                raise ValueError(f"buy_side必须是'YES'或'NO', 当前值: {buy_side}")
            updates.append("buy_side = ?")
            params.append(buy_side)

        if shares is not None:
            if shares < 0:
                raise ValueError(f"shares必须大于等于0, 当前值: {shares}")
            updates.append("shares = ?")
            params.append(shares)

        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)

        if not updates:
            return True  # 没有需要更新的字段

        # 添加updated_at字段
        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE position_listen_list SET {', '.join(updates)} WHERE id = ?"
        params.append(listen_id)

        config_manager.execute_update(query, tuple(params))
        return True

    except Exception as e:
        print(f"[PositionListenConfig] 更新监听记录失败: {str(e)}")
        return False


def remove_position_listen(
    listen_id: int,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    删除持仓监听记录
    
    参数:
        listen_id: 监听记录ID
        db_path: 数据库文件路径
        
    返回:
        bool: 是否删除成功
    """
    try:
        config_manager = get_config_manager(db_path)
        
        query = "DELETE FROM position_listen_list WHERE id = ?"
        params = (listen_id,)
        
        config_manager.execute_update(query, params)
        return True
        
    except Exception as e:
        print(f"[PositionListenConfig] 删除监听记录失败: {str(e)}")
        return False


def deactivate_position_listen(
    listen_id: int,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    停用持仓监听记录（软删除）
    
    参数:
        listen_id: 监听记录ID
        db_path: 数据库文件路径
        
    返回:
        bool: 是否停用成功
    """
    return update_position_listen(listen_id, is_active=False, db_path=db_path)


def clear_position_listen_list(
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    清空持仓监听列表
    
    参数:
        db_path: 数据库文件路径
        
    返回:
        bool: 是否清空成功
    """
    try:
        config_manager = get_config_manager(db_path)
        
        query = "DELETE FROM position_listen_list"
        config_manager.execute_update(query, ())
        return True
        
    except Exception as e:
        print(f"[PositionListenConfig] 清空监听列表失败: {str(e)}")
        return False

