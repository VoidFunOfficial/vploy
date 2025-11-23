#!/usr/bin/env python3
"""
调试 SignedOrder 对象结构的脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.polymarket_api.clob_api import get_client, create_limit_order, BUY

def debug_signed_order():
    """调试 SignedOrder 对象的结构"""
    try:
        # 创建一个测试订单
        token_id = "58969364816213855615291775146907533569112761571567201275002876280034021179495"
        price = 0.08
        size = 1
        side = BUY
        
        # 创建限价订单
        signed_order = create_limit_order(token_id, price, size, side)
        
        print("=== SignedOrder 对象信息 ===")
        print(f"类型: {type(signed_order)}")
        print(f"是否为字典: {isinstance(signed_order, dict)}")
        
        if hasattr(signed_order, '__dict__'):
            print(f"对象属性: {signed_order.__dict__}")
        
        print(f"dir() 结果: {dir(signed_order)}")
        
        # 尝试不同的访问方式
        print("\n=== 尝试访问订单ID ===")
        
        # 方式1: 字典访问
        try:
            order_id_dict = signed_order.get("id", "not_found")
            print(f"字典访问 .get('id'): {order_id_dict}")
        except Exception as e:
            print(f"字典访问失败: {e}")
        
        # 方式2: 属性访问
        try:
            order_id_attr = signed_order.id
            print(f"属性访问 .id: {order_id_attr}")
        except Exception as e:
            print(f"属性访问失败: {e}")
        
        # 方式3: 字典键访问
        try:
            order_id_key = signed_order["id"]
            print(f"字典键访问 ['id']: {order_id_key}")
        except Exception as e:
            print(f"字典键访问失败: {e}")
        
        # 方式4: 检查是否有其他可能的ID字段
        possible_id_fields = ['id', 'order_id', 'orderId', 'ID', 'hash', 'signature']
        for field in possible_id_fields:
            try:
                if hasattr(signed_order, field):
                    value = getattr(signed_order, field)
                    print(f"属性 {field}: {value}")
                elif isinstance(signed_order, dict) and field in signed_order:
                    value = signed_order[field]
                    print(f"字典键 {field}: {value}")
            except Exception as e:
                print(f"访问 {field} 失败: {e}")
        
        print(f"\n=== 完整对象内容 ===")
        print(signed_order)
        
    except Exception as e:
        print(f"调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_signed_order()
