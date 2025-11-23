"""
事件类型管理

提供事件类型注册、查询和管理功能。
事件命名规范：域.子域.动作（全大写），如 EXEC.ORDER.SUBMIT
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from threading import Lock


@dataclass
class EventCode:
    """
    事件码定义
    
    属性:
        code: 事件码，如 EVT-5001
        name: 事件名称，如 EXEC.ORDER.SUBMIT
        description: 事件描述
        metadata: 额外的元数据
    """
    code: str
    name: str
    description: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata or {},
        }


class EventRegistry:
    """
    事件类型注册表
    
    提供事件类型的注册、查询和管理功能。
    线程安全的单例模式。
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化事件注册表"""
        if self._initialized:
            return
        
        self._events: Dict[str, EventCode] = {}
        self._name_to_code: Dict[str, str] = {}
        self._lock = Lock()
        self._initialized = True
        
        # 注册一些预定义的事件类型（示例）
        self._register_default_events()
    
    def _register_default_events(self):
        """注册默认的事件类型"""
        default_events = [
            # 系统事件
            EventCode("EVT-1001", "SYS.STARTUP", "系统启动"),
            EventCode("EVT-1002", "SYS.SHUTDOWN", "系统关闭"),
            EventCode("EVT-1003", "SYS.CONFIG.LOADED", "配置加载完成"),
            EventCode("EVT-1004", "SYS.HEARTBEAT", "系统心跳"),
            
            # 数据采集事件
            EventCode("EVT-2001", "INGEST.MARKET.DISCOVERED", "发现新市场"),
            EventCode("EVT-2002", "INGEST.MARKET.UPDATED", "市场数据更新"),
            EventCode("EVT-2003", "INGEST.MARKET.CANDIDATE", "市场进入候选池"),
            EventCode("EVT-2004", "INGEST.WS.CONNECTED", "WebSocket 连接建立"),
            EventCode("EVT-2005", "INGEST.WS.DISCONNECTED", "WebSocket 连接断开"),
            
            # 策略事件
            EventCode("EVT-3001", "STRATEGY.SIGNAL.GENERATED", "生成交易信号"),
            EventCode("EVT-3002", "STRATEGY.SIGNAL.FILTERED", "信号被过滤"),
            EventCode("EVT-3003", "STRATEGY.POSITION.OPENED", "开仓"),
            EventCode("EVT-3004", "STRATEGY.POSITION.CLOSED", "平仓"),
            
            # 路由事件
            EventCode("EVT-4001", "ROUTER.ROUTE.SELECTED", "选择交易路由"),
            EventCode("EVT-4002", "ROUTER.ROUTE.FAILED", "路由失败"),
            
            # 订单执行事件（TRADE 级别）
            EventCode("EVT-5001", "EXEC.ORDER.SUBMIT", "提交订单"),
            EventCode("EVT-5002", "EXEC.ORDER.ACCEPTED", "订单被接受"),
            EventCode("EVT-5003", "EXEC.ORDER.REJECTED", "订单被拒绝"),
            EventCode("EVT-5004", "EXEC.ORDER.FILLED", "订单成交"),
            EventCode("EVT-5005", "EXEC.ORDER.PARTIAL_FILLED", "订单部分成交"),
            EventCode("EVT-5006", "EXEC.ORDER.CANCELLED", "订单取消"),
            EventCode("EVT-5007", "EXEC.ORDER.EXPIRED", "订单过期"),
            
            # 对账事件
            EventCode("EVT-6001", "RECON.STARTED", "对账开始"),
            EventCode("EVT-6002", "RECON.COMPLETED", "对账完成"),
            EventCode("EVT-6003", "RECON.MISMATCH", "对账不平"),
            EventCode("EVT-6004", "RECON.POSITION.SYNCED", "仓位同步"),
            
            # 审计事件
            EventCode("EVT-7001", "AUDIT.AUTH.LOGIN", "用户登录"),
            EventCode("EVT-7002", "AUDIT.AUTH.LOGOUT", "用户登出"),
            EventCode("EVT-7003", "AUDIT.CONFIG.CHANGED", "配置变更"),
            EventCode("EVT-7004", "AUDIT.KEY.ROTATED", "密钥轮换"),
            EventCode("EVT-7005", "AUDIT.FUND.TRANSFER", "资金划拨"),

            # 过滤器事件
            EventCode("EVT-8001", "FILTER.INIT", "过滤器初始化"),
            EventCode("EVT-8002", "FILTER.START", "过滤流程开始"),
            EventCode("EVT-8003", "FILTER.COMPLETE", "过滤流程完成"),
            EventCode("EVT-8004", "FILTER.EMPTY_INPUT", "输入数据为空"),
            EventCode("EVT-8011", "FILTER.CATEGORY.COMPLETE", "Category 过滤完成"),
            EventCode("EVT-8012", "FILTER.CATEGORY.BLOCKED", "市场被 Category 黑名单过滤"),
            EventCode("EVT-8013", "FILTER.CATEGORY.SKIP", "Category 过滤跳过"),
            EventCode("EVT-8021", "FILTER.TAG.COMPLETE", "Tag 过滤完成"),
            EventCode("EVT-8022", "FILTER.TAG.BLOCKED", "市场被 Tag 黑名单过滤"),
            EventCode("EVT-8023", "FILTER.TAG.SKIP", "Tag 过滤跳过"),
            EventCode("EVT-8031", "FILTER.DESCRIPTION.COMPLETE", "描述关键词过滤完成"),
            EventCode("EVT-8032", "FILTER.DESCRIPTION.BLOCKED", "市场被描述关键词黑名单过滤"),
            EventCode("EVT-8033", "FILTER.DESCRIPTION.SKIP", "描述关键词过滤跳过"),
            EventCode("EVT-8041", "FILTER.DATABASE.COMPLETE", "数据库去重检查完成"),
            EventCode("EVT-8042", "FILTER.DATABASE.DUPLICATE", "市场已处理（重复）"),
            EventCode("EVT-8043", "FILTER.DATABASE.NO_ID", "市场缺少 ID 字段"),
            EventCode("EVT-8051", "FILTER.AI.SKIP", "AI 过滤跳过"),
            EventCode("EVT-8052", "FILTER.AI.PROCESS", "AI 处理市场"),
            EventCode("EVT-8061", "FILTER.BLACKLIST.ADD", "添加黑名单配置项"),
            EventCode("EVT-8062", "FILTER.BLACKLIST.REMOVE", "删除黑名单配置项"),
            EventCode("EVT-8063", "FILTER.BLACKLIST.UPDATE", "更新黑名单配置项"),
            EventCode("EVT-8064", "FILTER.BLACKLIST.DUPLICATE", "黑名单配置项已存在"),
            EventCode("EVT-8065", "FILTER.BLACKLIST.NOT_FOUND", "黑名单配置项不存在"),
            EventCode("EVT-8071", "FILTER.PROCESSED.MARK", "标记市场为已处理"),
            EventCode("EVT-8072", "FILTER.PROCESSED.CLEAR", "清理已处理市场记录"),
            EventCode("EVT-8081", "FILTER.DB.INIT", "数据库管理器初始化"),
            EventCode("EVT-8082", "FILTER.DB.TABLES_CREATED", "数据库表创建完成"),
            EventCode("EVT-8083", "FILTER.DB.DEFAULT_BLACKLIST", "默认黑名单配置插入完成"),
        ]
        
        for event in default_events:
            self._events[event.code] = event
            self._name_to_code[event.name] = event.code
    
    def register(
        self,
        code: str,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> EventCode:
        """
        注册新的事件类型
        
        参数:
            code: 事件码，如 EVT-5001
            name: 事件名称，如 EXEC.ORDER.SUBMIT
            description: 事件描述
            metadata: 额外的元数据
            overwrite: 是否覆盖已存在的事件
            
        返回:
            EventCode: 注册的事件码对象
            
        异常:
            ValueError: 如果事件码或名称已存在且 overwrite=False
        """
        with self._lock:
            if not overwrite:
                if code in self._events:
                    raise ValueError(f"事件码 {code} 已存在")
                if name in self._name_to_code:
                    raise ValueError(f"事件名称 {name} 已存在")
            
            event = EventCode(code, name, description, metadata)
            self._events[code] = event
            self._name_to_code[name] = code
            
            return event
    
    def get_by_code(self, code: str) -> Optional[EventCode]:
        """
        根据事件码获取事件
        
        参数:
            code: 事件码
            
        返回:
            EventCode: 事件码对象，如果不存在则返回 None
        """
        return self._events.get(code)
    
    def get_by_name(self, name: str) -> Optional[EventCode]:
        """
        根据事件名称获取事件
        
        参数:
            name: 事件名称
            
        返回:
            EventCode: 事件码对象，如果不存在则返回 None
        """
        code = self._name_to_code.get(name)
        if code:
            return self._events.get(code)
        return None
    
    def get_code_by_name(self, name: str) -> Optional[str]:
        """
        根据事件名称获取事件码
        
        参数:
            name: 事件名称
            
        返回:
            str: 事件码，如果不存在则返回 None
        """
        return self._name_to_code.get(name)
    
    def exists(self, code_or_name: str) -> bool:
        """
        检查事件是否存在
        
        参数:
            code_or_name: 事件码或事件名称
            
        返回:
            bool: 如果存在返回 True
        """
        return code_or_name in self._events or code_or_name in self._name_to_code
    
    def list_all(self) -> Dict[str, EventCode]:
        """
        列出所有已注册的事件
        
        返回:
            dict: 事件码到 EventCode 对象的映射
        """
        return self._events.copy()
    
    def list_by_prefix(self, prefix: str) -> Dict[str, EventCode]:
        """
        根据事件名称前缀列出事件
        
        参数:
            prefix: 事件名称前缀，如 "EXEC.ORDER"
            
        返回:
            dict: 匹配的事件码到 EventCode 对象的映射
        """
        return {
            code: event
            for code, event in self._events.items()
            if event.name.startswith(prefix)
        }
    
    def unregister(self, code: str) -> bool:
        """
        注销事件类型
        
        参数:
            code: 事件码
            
        返回:
            bool: 如果成功注销返回 True
        """
        with self._lock:
            event = self._events.pop(code, None)
            if event:
                self._name_to_code.pop(event.name, None)
                return True
            return False


# 全局事件注册表实例
_event_registry = EventRegistry()


def register_event(
    code: str,
    name: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    overwrite: bool = False
) -> EventCode:
    """
    注册事件类型的便捷函数
    
    参数:
        code: 事件码
        name: 事件名称
        description: 事件描述
        metadata: 额外的元数据
        overwrite: 是否覆盖已存在的事件
        
    返回:
        EventCode: 注册的事件码对象
    """
    return _event_registry.register(code, name, description, metadata, overwrite)


def get_event(code_or_name: str) -> Optional[EventCode]:
    """
    获取事件的便捷函数
    
    参数:
        code_or_name: 事件码或事件名称
        
    返回:
        EventCode: 事件码对象，如果不存在则返回 None
    """
    # 先尝试按事件码查找
    event = _event_registry.get_by_code(code_or_name)
    if event:
        return event
    # 再尝试按事件名称查找
    return _event_registry.get_by_name(code_or_name)

