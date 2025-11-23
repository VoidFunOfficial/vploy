"""
自动交易配置管理模块

提供自动交易模块的参数配置管理，支持数据库存储和动态更新。
所有配置参数都存储在 SQLite 数据库中，便于运行时修改。
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .config_manager import ConfigManager
from .global_event_reg import vlogger


@dataclass
class AutoTradeConfig:
    """自动交易配置数据类"""
    
    # 滑点控制参数
    max_slippage_percent: float = 2.0           # 最大允许滑点百分比
    liquidity_threshold: float = 100.0          # 最小流动性阈值（USDC）
    
    # 订单大小限制
    min_order_size: float = 1.0                 # 最小订单金额（USDC）
    max_order_size: float = 10000.0             # 最大订单金额（USDC）
    
    # 价格策略参数
    price_improvement_factor: float = 0.1       # 价格改善因子（10%）
    safety_margin: float = 0.05                 # 安全边距（5%）
    
    # 重试机制参数
    max_retries: int = 3                        # 最大重试次数
    retry_delay: float = 1.0                    # 重试延迟（秒）
    
    # 风险评估阈值
    low_risk_slippage_threshold: float = 1.0    # 低风险滑点阈值（%）
    high_risk_slippage_threshold: float = 2.0   # 高风险滑点阈值（%）
    low_risk_liquidity_threshold: float = 60.0  # 低风险流动性阈值
    high_risk_liquidity_threshold: float = 30.0 # 高风险流动性阈值
    
    # 执行控制参数
    enable_slippage_protection: bool = True     # 启用滑点保护
    enable_liquidity_check: bool = True         # 启用流动性检查
    enable_size_validation: bool = True         # 启用订单大小验证
    
    # 调试和监控参数
    log_orderbook_analysis: bool = True         # 记录订单簿分析日志
    log_slippage_calculation: bool = True       # 记录滑点计算日志
    log_execution_details: bool = True          # 记录执行详情日志


class AutoTradeConfigManager:
    """自动交易配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_manager = ConfigManager()
        self.table_name = "auto_trade_config"
        self._ensure_table_exists()
        
        vlogger.info("AUTO_TRADE.CONFIG.INIT", msg="自动交易配置管理器初始化")
    
    def _ensure_table_exists(self):
        """确保配置表存在"""
        try:
            conn = self.config_manager.get_connection()
            cursor = conn.cursor()
            
            # 创建自动交易配置表
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value TEXT NOT NULL,
                    config_type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            vlogger.info("AUTO_TRADE.CONFIG.TABLE_CREATED", msg="自动交易配置表创建成功")
            
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.TABLE_ERROR", msg="创建配置表失败", 
                         error_code="E-AT-CONFIG-001", extra={"error": str(e)})
            raise
    
    def load_config(self) -> AutoTradeConfig:
        """
        从数据库加载配置
        
        返回:
            AutoTradeConfig: 配置对象
        """
        try:
            # 先尝试从数据库加载
            config_dict = self._load_from_database()
            
            if not config_dict:
                # 如果数据库为空，使用默认配置并保存
                vlogger.info("AUTO_TRADE.CONFIG.USE_DEFAULT", msg="使用默认配置")
                config = AutoTradeConfig()
                self.save_config(config)
                return config
            
            # 从数据库数据创建配置对象
            config = AutoTradeConfig(**config_dict)
            
            vlogger.info("AUTO_TRADE.CONFIG.LOADED", msg="配置加载成功", extra={
                "config_count": len(config_dict)
            })
            
            return config
            
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.LOAD_ERROR", msg="配置加载失败", 
                         error_code="E-AT-CONFIG-002", extra={"error": str(e)})
            
            # 返回默认配置
            return AutoTradeConfig()
    
    def save_config(self, config: AutoTradeConfig) -> bool:
        """
        保存配置到数据库
        
        参数:
            config: 配置对象
            
        返回:
            bool: 保存是否成功
        """
        try:
            config_dict = asdict(config)
            
            conn = self.config_manager.get_connection()
            cursor = conn.cursor()
            
            # 获取配置描述
            descriptions = self._get_config_descriptions()
            
            for key, value in config_dict.items():
                # 确定配置类型
                config_type = type(value).__name__
                description = descriptions.get(key, f"自动交易配置: {key}")
                
                # 转换值为字符串
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                # 插入或更新配置
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {self.table_name} 
                    (config_key, config_value, config_type, description, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, value_str, config_type, description, datetime.now()))
            
            conn.commit()
            
            vlogger.info("AUTO_TRADE.CONFIG.SAVED", msg="配置保存成功", extra={
                "config_count": len(config_dict)
            })
            
            return True
            
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.SAVE_ERROR", msg="配置保存失败", 
                         error_code="E-AT-CONFIG-003", extra={"error": str(e)})
            return False
    
    def update_config(self, **kwargs) -> bool:
        """
        更新部分配置
        
        参数:
            **kwargs: 要更新的配置项
            
        返回:
            bool: 更新是否成功
        """
        try:
            # 加载当前配置
            current_config = self.load_config()
            
            # 更新指定的配置项
            for key, value in kwargs.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)
                    vlogger.info("AUTO_TRADE.CONFIG.UPDATED", msg=f"配置项更新: {key}", extra={
                        "key": key,
                        "old_value": getattr(current_config, key),
                        "new_value": value
                    })
                else:
                    vlogger.warn("AUTO_TRADE.CONFIG.INVALID_KEY", msg=f"无效的配置项: {key}")
            
            # 保存更新后的配置
            return self.save_config(current_config)
            
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.UPDATE_ERROR", msg="配置更新失败", 
                         error_code="E-AT-CONFIG-004", extra={"error": str(e)})
            return False
    
    def get_config_value(self, key: str) -> Optional[Any]:
        """
        获取单个配置值
        
        参数:
            key: 配置键名
            
        返回:
            Any: 配置值，如果不存在返回None
        """
        try:
            config = self.load_config()
            return getattr(config, key, None)
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.GET_ERROR", msg=f"获取配置失败: {key}", 
                         error_code="E-AT-CONFIG-005", extra={"key": key, "error": str(e)})
            return None
    
    def _load_from_database(self) -> Dict[str, Any]:
        """从数据库加载配置字典"""
        try:
            conn = self.config_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT config_key, config_value, config_type FROM {self.table_name}")
            rows = cursor.fetchall()
            
            config_dict = {}
            for key, value_str, config_type in rows:
                # 根据类型转换值
                if config_type == 'bool':
                    config_dict[key] = value_str.lower() in ('true', '1', 'yes')
                elif config_type == 'int':
                    config_dict[key] = int(value_str)
                elif config_type == 'float':
                    config_dict[key] = float(value_str)
                elif config_type in ('dict', 'list'):
                    config_dict[key] = json.loads(value_str)
                else:
                    config_dict[key] = value_str
            
            return config_dict
            
        except Exception as e:
            vlogger.error("AUTO_TRADE.CONFIG.DB_LOAD_ERROR", msg="数据库配置加载失败", 
                         error_code="E-AT-CONFIG-006", extra={"error": str(e)})
            return {}
    
    def _get_config_descriptions(self) -> Dict[str, str]:
        """获取配置项描述"""
        return {
            "max_slippage_percent": "最大允许滑点百分比",
            "liquidity_threshold": "最小流动性阈值（USDC）",
            "min_order_size": "最小订单金额（USDC）",
            "max_order_size": "最大订单金额（USDC）",
            "price_improvement_factor": "价格改善因子",
            "safety_margin": "安全边距",
            "max_retries": "最大重试次数",
            "retry_delay": "重试延迟（秒）",
            "low_risk_slippage_threshold": "低风险滑点阈值（%）",
            "high_risk_slippage_threshold": "高风险滑点阈值（%）",
            "low_risk_liquidity_threshold": "低风险流动性阈值",
            "high_risk_liquidity_threshold": "高风险流动性阈值",
            "enable_slippage_protection": "启用滑点保护",
            "enable_liquidity_check": "启用流动性检查",
            "enable_size_validation": "启用订单大小验证",
            "log_orderbook_analysis": "记录订单簿分析日志",
            "log_slippage_calculation": "记录滑点计算日志",
            "log_execution_details": "记录执行详情日志"
        }


# 全局配置管理器实例
_config_manager = None

def get_auto_trade_config() -> AutoTradeConfig:
    """
    获取自动交易配置（全局单例）
    
    返回:
        AutoTradeConfig: 配置对象
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = AutoTradeConfigManager()
    
    return _config_manager.load_config()


def update_auto_trade_config(**kwargs) -> bool:
    """
    更新自动交易配置
    
    参数:
        **kwargs: 要更新的配置项
        
    返回:
        bool: 更新是否成功
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = AutoTradeConfigManager()
    
    return _config_manager.update_config(**kwargs)


def get_config_value(key: str) -> Optional[Any]:
    """
    获取单个配置值
    
    参数:
        key: 配置键名
        
    返回:
        Any: 配置值
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = AutoTradeConfigManager()
    
    return _config_manager.get_config_value(key)
