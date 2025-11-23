"""
全局事件注册和 VLogger 实例管理

统一管理所有模块的事件注册码和错误码，提供全局 VLogger 实例。
"""

from backend.vlogger import get_logger, register_event, register_error

# 创建全局 VLogger 实例
vlogger = get_logger("voidpoly")

def register_all_events():
    """注册所有模块的事件码和错误码"""

    # ==================== 仓位管理模块事件 ====================
    # EVT-POS-xxx 系列
    register_event("EVT-POS-001", "POSITION.ALLOCATE.START", "开始仓位分配", overwrite=True)
    register_event("EVT-POS-002", "POSITION.ALLOCATE.SUCCESS", "仓位分配成功", overwrite=True)
    register_event("EVT-POS-003", "POSITION.BALANCE.FETCHED", "获取账户余额", overwrite=True)
    register_event("EVT-POS-004", "POSITION.MARKETS.CONVERTED", "市场数据转换完成", overwrite=True)
    register_event("EVT-POS-005", "POSITION.CONVERT.FAILED", "市场数据转换失败", overwrite=True)
    register_event("EVT-POS-006", "POSITION.EXPORT.SUCCESS", "交易指令导出成功", overwrite=True)

    # E-POS-xxx 系列错误码
    register_error("E-POS-001", "NO_VALID_MARKETS", "没有有效的市场数据", "error", overwrite=True)
    register_error("E-POS-002", "ALLOCATION_EXCEPTION", "仓位分配异常", "error", overwrite=True)
    register_error("E-POS-003", "EXPORT_FAILED", "交易指令导出失败", "error", overwrite=True)

    # ==================== CLOB API 模块事件 ====================
    # EVT-CLOB-xxx 系列
    register_event("EVT-CLOB-001", "CLOB.CLIENT.INIT", "CLOB 客户端初始化", overwrite=True)
    register_event("EVT-CLOB-002", "CLOB.ORDER.CREATE", "创建订单", overwrite=True)
    register_event("EVT-CLOB-003", "CLOB.ORDER.POST", "提交订单", overwrite=True)
    register_event("EVT-CLOB-004", "CLOB.ORDER.CANCEL", "取消订单", overwrite=True)
    register_event("EVT-CLOB-005", "CLOB.MARKET.QUERY", "查询市场数据", overwrite=True)
    register_event("EVT-CLOB-006", "CLOB.BALANCE.QUERY", "查询账户余额", overwrite=True)
    register_event("EVT-CLOB-007", "CLOB.TRADE.QUERY", "查询交易记录", overwrite=True)

    # E-CLOB-xxx 系列错误码
    register_error("E-CLOB-001", "CLIENT_INIT_ERROR", "客户端初始化失败", "error", overwrite=True)
    register_error("E-CLOB-002", "ORDER_CREATE_ERROR", "订单创建失败", "error", overwrite=True)
    register_error("E-CLOB-003", "ORDER_POST_ERROR", "订单提交失败", "error", overwrite=True)
    register_error("E-CLOB-004", "ORDER_CANCEL_ERROR", "订单取消失败", "error", overwrite=True)
    register_error("E-CLOB-005", "MARKET_QUERY_ERROR", "市场数据查询失败", "error", overwrite=True)
    register_error("E-CLOB-006", "BALANCE_QUERY_ERROR", "余额查询失败", "error", overwrite=True)
    register_error("E-CLOB-007", "TRADE_QUERY_ERROR", "交易记录查询失败", "error", overwrite=True)
    register_error("E-CLOB-008", "HTTP_ERROR", "HTTP 请求错误", "error", overwrite=True)
    register_error("E-CLOB-009", "TIMEOUT_ERROR", "请求超时", "warning", overwrite=True)
    register_error("E-CLOB-010", "JSON_DECODE_ERROR", "JSON 解析错误", "error", overwrite=True)
    register_error("E-CLOB-011", "INVALID_RESPONSE", "无效响应", "error", overwrite=True)
    register_error("E-CLOB-012", "RATE_LIMIT_ERROR", "速率限制", "warning", overwrite=True)

    # ==================== Polymarket API 模块事件 ====================
    # EVT-PM-xxx 系列
    register_event("EVT-PM-001", "API.CLIENT.INIT", "API 客户端初始化", overwrite=True)
    register_event("EVT-PM-002", "API.REQUEST.START", "API 请求开始", overwrite=True)
    register_event("EVT-PM-003", "API.REQUEST.SUCCESS", "API 请求成功", overwrite=True)
    register_event("EVT-PM-004", "API.REQUEST.ERROR", "API 请求错误", overwrite=True)
    register_event("EVT-PM-005", "API.MARKET.FETCH", "获取市场数据", overwrite=True)
    register_event("EVT-PM-006", "API.EVENT.FETCH", "获取事件数据", overwrite=True)
    register_event("EVT-PM-007", "API.TAG.FETCH", "获取标签数据", overwrite=True)

    # E-PM-xxx 系列错误码
    register_error("E-PM-001", "HTTP_ERROR", "HTTP 请求错误", "error", overwrite=True)
    register_error("E-PM-002", "TIMEOUT_ERROR", "请求超时", "warning", overwrite=True)
    register_error("E-PM-003", "JSON_DECODE_ERROR", "JSON 解析错误", "error", overwrite=True)
    register_error("E-PM-004", "INVALID_RESPONSE", "无效响应", "error", overwrite=True)
    register_error("E-PM-005", "RATE_LIMIT_ERROR", "速率限制", "warning", overwrite=True)

    # ==================== Orderbook API 模块事件 ====================
    # EVT-OB-xxx 系列
    register_event("EVT-OB-001", "ORDERBOOK.CLIENT.INIT", "Orderbook 客户端初始化", overwrite=True)
    register_event("EVT-OB-002", "ORDERBOOK.BOOK.QUERY", "查询订单簿", overwrite=True)
    register_event("EVT-OB-003", "ORDERBOOK.PRICE.QUERY", "查询价格", overwrite=True)
    register_event("EVT-OB-004", "ORDERBOOK.TRADE.QUERY", "查询交易记录", overwrite=True)
    register_event("EVT-OB-005", "ORDERBOOK.MARKET.QUERY", "查询市场数据", overwrite=True)
    register_event("EVT-OB-006", "ORDERBOOK.REQUEST.START", "API 请求开始", overwrite=True)
    register_event("EVT-OB-007", "ORDERBOOK.REQUEST.SUCCESS", "API 请求成功", overwrite=True)

    # E-OB-xxx 系列错误码
    register_error("E-OB-001", "HTTP_ERROR", "HTTP 请求错误", "error", overwrite=True)
    register_error("E-OB-002", "TIMEOUT_ERROR", "请求超时", "warning", overwrite=True)
    register_error("E-OB-003", "JSON_DECODE_ERROR", "JSON 解析错误", "error", overwrite=True)
    register_error("E-OB-004", "INVALID_RESPONSE", "无效响应", "error", overwrite=True)
    register_error("E-OB-005", "RATE_LIMIT_ERROR", "速率限制", "warning", overwrite=True)

    # ==================== 过滤器模块事件 ====================
    # 从 vlogger/events.py 中的默认事件中提取过滤器相关事件
    # EVT-8xxx 系列（过滤器事件）
    register_event("EVT-8001", "FILTER.INIT", "过滤器初始化", overwrite=True)
    register_event("EVT-8002", "FILTER.START", "过滤流程开始", overwrite=True)
    register_event("EVT-8003", "FILTER.COMPLETE", "过滤流程完成", overwrite=True)
    register_event("EVT-8011", "FILTER.CATEGORY.START", "Category 过滤开始", overwrite=True)
    register_event("EVT-8012", "FILTER.CATEGORY.COMPLETE", "Category 过滤完成", overwrite=True)
    register_event("EVT-8021", "FILTER.TAG.START", "Tag 过滤开始", overwrite=True)
    register_event("EVT-8022", "FILTER.TAG.COMPLETE", "Tag 过滤完成", overwrite=True)
    register_event("EVT-8031", "FILTER.TITLE.START", "标题关键词过滤开始", overwrite=True)
    register_event("EVT-8032", "FILTER.TITLE.COMPLETE", "标题关键词过滤完成", overwrite=True)
    register_event("EVT-8041", "FILTER.DESCRIPTION.START", "描述关键词过滤开始", overwrite=True)
    register_event("EVT-8042", "FILTER.DESCRIPTION.COMPLETE", "描述关键词过滤完成", overwrite=True)
    register_event("EVT-8051", "FILTER.DATABASE.START", "数据库去重检查开始", overwrite=True)
    register_event("EVT-8052", "FILTER.DATABASE.COMPLETE", "数据库去重检查完成", overwrite=True)
    register_event("EVT-8061", "FILTER.AI.START", "AI 过滤开始", overwrite=True)
    register_event("EVT-8062", "FILTER.AI.COMPLETE", "AI 过滤完成", overwrite=True)
    register_event("EVT-8063", "FILTER.AI.SKIP", "AI 过滤跳过", overwrite=True)
    register_event("EVT-8071", "FILTER.PROCESSED.MARK", "标记市场为已处理", overwrite=True)
    register_event("EVT-8072", "FILTER.PROCESSED.CLEAR", "清理已处理市场记录", overwrite=True)
    register_event("EVT-8081", "FILTER.DB.INIT", "数据库管理器初始化", overwrite=True)
    register_event("EVT-8082", "FILTER.DB.TABLES_CREATED", "数据库表创建完成", overwrite=True)
    register_event("EVT-8083", "FILTER.DB.DEFAULT_BLACKLIST", "默认黑名单配置插入完成", overwrite=True)

    # E-FILTER-xxx 系列错误码
    register_error("E-FILTER-001", "FILTER_DB_QUERY_ERROR", "数据库查询错误", "error", overwrite=True)
    register_error("E-FILTER-002", "FILTER_DB_UPDATE_ERROR", "数据库更新错误", "error", overwrite=True)
    register_error("E-FILTER-003", "FILTER_DB_INIT_ERROR", "数据库初始化错误", "error", overwrite=True)
    register_error("E-FILTER-004", "FILTER_CONFIG_ERROR", "过滤器配置错误", "error", overwrite=True)
    register_error("E-FILTER-005", "FILTER_AI_ERROR", "AI 过滤错误", "error", overwrite=True)
    register_error("E-FILTER-006", "FILTER_VALIDATION_ERROR", "数据验证错误", "error", overwrite=True)
    register_error("E-FILTER-007", "FILTER_PROCESSING_ERROR", "过滤处理错误", "error", overwrite=True)
    register_error("E-FILTER-008", "FILTER_CALL_FAILED", "过滤器调用失败", "error", overwrite=True)

# 在模块导入时自动注册所有事件
register_all_events()

# 记录初始化完成
vlogger.info("EVT-1003", msg="全局事件注册完成", extra={"total_events": "50+", "total_errors": "30+"})