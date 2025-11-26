"""
全局事件注册和 VLogger 实例管理

统一管理所有模块的事件注册码和错误码，提供全局 VLogger 实例。
"""

from ..vlogger import get_logger, register_event, register_error

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

    # ==================== 自动交易模块事件 ====================
    # EVT-AT-xxx 系列
    register_event("EVT-AT-001", "AUTO_TRADE.INIT", "自动交易器初始化", overwrite=True)
    register_event("EVT-AT-002", "AUTO_TRADE.GET_INSTRUCTIONS", "获取交易决策指令", overwrite=True)
    register_event("EVT-AT-003", "AUTO_TRADE.GET_INSTRUCTIONS_SUCCESS", "获取交易指令成功", overwrite=True)
    register_event("EVT-AT-004", "AUTO_TRADE.ANALYZE_ORDERBOOK", "分析订单簿", overwrite=True)
    register_event("EVT-AT-005", "AUTO_TRADE.ANALYZE_ORDERBOOK_SUCCESS", "订单簿分析完成", overwrite=True)
    register_event("EVT-AT-006", "AUTO_TRADE.CALCULATE_SLIPPAGE", "计算滑点", overwrite=True)
    register_event("EVT-AT-007", "AUTO_TRADE.CALCULATE_SLIPPAGE_SUCCESS", "滑点计算完成", overwrite=True)
    register_event("EVT-AT-008", "AUTO_TRADE.EXECUTE_TRADE", "开始执行交易", overwrite=True)
    register_event("EVT-AT-009", "AUTO_TRADE.EXECUTE_TRADE_SUCCESS", "交易执行成功", overwrite=True)
    register_event("EVT-AT-010", "AUTO_TRADE.EXECUTE_BATCH", "开始批量执行交易", overwrite=True)
    register_event("EVT-AT-011", "AUTO_TRADE.EXECUTE_BATCH_COMPLETE", "批量交易执行完成", overwrite=True)
    register_event("EVT-AT-012", "AUTO_TRADE.EXECUTE_AUTO_TRADING", "开始自动交易流程", overwrite=True)
    register_event("EVT-AT-013", "AUTO_TRADE.EXECUTE_AUTO_TRADING_SUCCESS", "自动交易流程完成", overwrite=True)

    # E-AT-xxx 系列错误码
    register_error("E-AT-001", "GET_INSTRUCTIONS_ERROR", "获取交易指令失败", "error", overwrite=True)
    register_error("E-AT-002", "GET_INSTRUCTIONS_EXCEPTION", "获取交易指令异常", "error", overwrite=True)
    register_error("E-AT-003", "ANALYZE_ORDERBOOK_ERROR", "订单簿分析失败", "error", overwrite=True)
    register_error("E-AT-004", "CALCULATE_SLIPPAGE_ERROR", "滑点计算异常", "error", overwrite=True)
    register_error("E-AT-005", "TOKEN_ID_ERROR", "无法获取token_id", "error", overwrite=True)
    register_error("E-AT-006", "EXECUTE_TRADE_ERROR", "交易执行异常", "error", overwrite=True)
    register_error("E-AT-007", "GET_TOKEN_ID_ERROR", "获取token_id失败", "error", overwrite=True)
    register_error("E-AT-008", "EXECUTE_AUTO_TRADING_ERROR", "自动交易流程异常", "error", overwrite=True)

    # 自动交易配置相关事件
    register_event("EVT-AT-014", "AUTO_TRADE.CONFIG.INIT", "自动交易配置管理器初始化", overwrite=True)
    register_event("EVT-AT-015", "AUTO_TRADE.CONFIG.LOADED", "配置加载成功", overwrite=True)
    register_event("EVT-AT-016", "AUTO_TRADE.CONFIG.SAVED", "配置保存成功", overwrite=True)
    register_event("EVT-AT-017", "AUTO_TRADE.CONFIG.UPDATED", "配置项更新", overwrite=True)
    register_event("EVT-AT-018", "AUTO_TRADE.CONFIG.REFRESHED", "配置已刷新", overwrite=True)
    register_event("EVT-AT-019", "AUTO_TRADE.CONFIG.USE_DEFAULT", "使用默认配置", overwrite=True)
    register_event("EVT-AT-020", "AUTO_TRADE.CONFIG.TABLE_CREATED", "配置表创建成功", overwrite=True)

    # 自动交易配置相关错误码
    register_error("E-AT-CONFIG-001", "TABLE_ERROR", "创建配置表失败", "error", overwrite=True)
    register_error("E-AT-CONFIG-002", "LOAD_ERROR", "配置加载失败", "error", overwrite=True)
    register_error("E-AT-CONFIG-003", "SAVE_ERROR", "配置保存失败", "error", overwrite=True)
    register_error("E-AT-CONFIG-004", "UPDATE_ERROR", "配置更新失败", "error", overwrite=True)
    register_error("E-AT-CONFIG-005", "GET_ERROR", "获取配置失败", "error", overwrite=True)
    register_error("E-AT-CONFIG-006", "DB_LOAD_ERROR", "数据库配置加载失败", "error", overwrite=True)
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

    # ==================== 健康检查模块事件 ====================
    # EVT-HC-xxx 系列
    register_event("EVT-HC-001", "HEALTH.CHECKER.INIT", "健康检查器初始化", overwrite=True)
    register_event("EVT-HC-002", "HEALTH.ENDPOINT.ADD", "添加端点配置", overwrite=True)
    register_event("EVT-HC-003", "HEALTH.ENDPOINT.REMOVE", "移除端点配置", overwrite=True)
    register_event("EVT-HC-004", "HEALTH.CHECK.START", "开始健康检查", overwrite=True)
    register_event("EVT-HC-005", "HEALTH.CHECK.SUCCESS", "端点检查成功", overwrite=True)
    register_event("EVT-HC-006", "HEALTH.CHECK.FAILED", "端点检查失败", overwrite=True)
    register_event("EVT-HC-007", "HEALTH.CHECK.COMPLETE", "健康检查完成", overwrite=True)
    register_event("EVT-HC-008", "HEALTH.LOOP.START", "定时健康检查循环启动", overwrite=True)
    register_event("EVT-HC-009", "HEALTH.LOOP.CANCEL", "定时健康检查循环被取消", overwrite=True)
    register_event("EVT-HC-010", "HEALTH.LOOP.ERROR", "定时健康检查循环异常", overwrite=True)
    register_event("EVT-HC-011", "HEALTH.LOOP.STOP", "定时健康检查循环已停止", overwrite=True)
    register_event("EVT-HC-012", "HEALTH.CHECKER.ALREADY_RUNNING", "健康检查器已在运行中", overwrite=True)
    register_event("EVT-HC-013", "HEALTH.CHECKER.START", "健康检查器已启动", overwrite=True)
    register_event("EVT-HC-014", "HEALTH.CHECKER.NOT_RUNNING", "健康检查器未在运行", overwrite=True)
    register_event("EVT-HC-015", "HEALTH.CHECKER.STOP", "健康检查器已停止", overwrite=True)

    # E-HC-xxx 系列错误码
    register_error("E-HC-001", "HEALTH_CHECK_LOOP_ERROR", "定时健康检查循环异常", "error", overwrite=True)
    register_error("E-HC-002", "HEALTH_CHECK_TIMEOUT", "健康检查超时", "warning", overwrite=True)
    register_error("E-HC-003", "HEALTH_CHECK_CONNECTION_ERROR", "健康检查连接错误", "warning", overwrite=True)
    register_error("E-HC-004", "HEALTH_CHECK_UNKNOWN_ERROR", "健康检查未知错误", "error", overwrite=True)

    # ==================== 持仓监听模块事件 ====================
    # EVT-PL-xxx 系列
    register_event("EVT-PL-001", "POSITION.LISTEN.ADD_START", "开始添加持仓监听", overwrite=True)
    register_event("EVT-PL-002", "POSITION.LISTEN.ADD_SUCCESS", "持仓监听添加成功", overwrite=True)
    register_event("EVT-PL-003", "POSITION.LISTEN.UPDATE", "更新持仓监听", overwrite=True)
    register_event("EVT-PL-004", "POSITION.LISTEN.REMOVE", "移除持仓监听", overwrite=True)
    register_event("EVT-PL-005", "POSITION.LISTEN.QUERY", "查询持仓监听列表", overwrite=True)
    register_event("EVT-PL-006", "POSITION.CHECK.START", "开始检查持仓监听列表", overwrite=True)
    register_event("EVT-PL-007", "POSITION.CHECK.NO_RECORDS", "没有找到激活的监听记录", overwrite=True)
    register_event("EVT-PL-008", "POSITION.CHECK.RECORDS_FOUND", "找到监听记录", overwrite=True)
    register_event("EVT-PL-009", "POSITION.CHECK.PROCESS_RECORD", "处理监听记录", overwrite=True)
    register_event("EVT-PL-010", "POSITION.CHECK.MARKET_NOT_FOUND", "未找到市场数据", overwrite=True)
    register_event("EVT-PL-011", "POSITION.CHECK.NO_TOKEN_IDS", "市场缺少clobTokenIds", overwrite=True)
    register_event("EVT-PL-012", "POSITION.CHECK.PRICE_FETCHED", "获取当前价格成功", overwrite=True)
    register_event("EVT-PL-013", "POSITION.CHECK.RECORD_SUCCESS", "监听记录处理成功", overwrite=True)
    register_event("EVT-PL-014", "POSITION.CHECK.COMPLETE", "持仓检查完成", overwrite=True)
    register_event("EVT-PL-015", "POSITION.PROCESS", "处理持仓信息", overwrite=True)

    # E-POSITION-xxx 系列错误码
    register_error("E-POSITION-001", "INVALID_MARKET_ID", "market_id不能为空", "error", overwrite=True)
    register_error("E-POSITION-002", "INVALID_BUY_SIDE", "buy_side参数无效", "error", overwrite=True)
    register_error("E-POSITION-003", "INVALID_BUY_PRICE", "buy_price参数无效", "error", overwrite=True)
    register_error("E-POSITION-004", "ADD_FAILED", "持仓监听添加失败", "error", overwrite=True)
    register_error("E-POSITION-005", "ADD_ERROR", "添加持仓监听时发生异常", "error", overwrite=True)
    register_error("E-POSITION-006", "PRICE_ERROR", "获取价格失败", "error", overwrite=True)
    register_error("E-POSITION-007", "RECORD_ERROR", "处理监听记录时发生异常", "error", overwrite=True)
    register_error("E-POSITION-008", "CHECK_ERROR", "检查持仓监听列表时发生异常", "error", overwrite=True)
    register_error("E-POSITION-009", "INVALID_SHARES", "shares参数无效", "error", overwrite=True)
def register_need_to_alert():
    register_alert_rule(AlertRule("E-TOKEN-001", AlertLevel.P0, enabled=True))
# 在模块导入时自动注册所有事件
register_all_events()

# 记录初始化完成
vlogger.info("EVT-1003", msg="全局事件注册完成", extra={"total_events": "70+", "total_errors": "39+"})