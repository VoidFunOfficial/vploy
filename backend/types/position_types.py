# -*- coding: utf-8 -*-
"""
仓位管理相关数据类型定义

包含 SimpleMarket（用于仓位分配算法的简化市场数据）和 TradeAllocation（交易分配结果）等核心数据结构。
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SimpleMarket:
    """
    简化市场数据结构（用于仓位分配算法）
    
    属性:
        id: 市场ID（字符串或整数）
        m: YES价格（市场报价）
        p_yes: 主观YES概率（AI预测）
        d: 结算日期（天数索引，相对于now_day）
        p_no: 主观NO概率（可选，默认为1-p_yes）
    """
    id: Any                      # 市场ID（字符串或整数）
    m: float                     # YES价格（市场报价）
    p_yes: float                 # 主观YES概率（AI预测）
    d: int                       # 结算日期（天数索引，相对于now_day）
    p_no: Optional[float] = None # 主观NO概率（可选，默认为1-p_yes）


@dataclass
class TradeAllocation:
    """
    交易分配结果数据结构
    
    属性:
        id: 市场ID
        side: 交易方向（YES/NO）
        price: 交易价格
        p: 主观概率
        b: 赔率
        f: 仓位比例（占总资金的比例）
        invest: 投资金额（美元）
        shares: 购买份额
        settle_day: 结算日期（天数索引）
    """
    id: Any           # 市场ID
    side: str         # 交易方向（YES/NO）
    price: float      # 交易价格
    p: float          # 主观概率
    b: float          # 赔率
    f: float          # 仓位比例
    invest: float     # 投资金额
    shares: float     # 购买份额
    settle_day: int   # 结算日期
    
    def to_dict(self) -> dict:
        """转换为字典格式（向后兼容）"""
        return {
            "id": self.id,
            "side": self.side,
            "price": float(self.price),
            "p": float(self.p),
            "b": float(self.b),
            "f": float(self.f),
            "invest": float(self.invest),
            "shares": float(self.shares),
            "settle_day": self.settle_day,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TradeAllocation':
        """从字典创建 TradeAllocation 对象"""
        return cls(
            id=data["id"],
            side=data["side"],
            price=data["price"],
            p=data["p"],
            b=data["b"],
            f=data["f"],
            invest=data["invest"],
            shares=data["shares"],
            settle_day=data["settle_day"]
        )

