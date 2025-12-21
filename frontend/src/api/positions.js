/**
 * 持仓监控相关 API
 */

import request from './request'

/**
 * 获取持仓汇总信息
 */
export function getPositionSummary() {
  return request({
    url: '/positions/summary',
    method: 'get'
  })
}

/**
 * 获取持仓列表
 * @param {Object} params - 查询参数
 * @param {string} params.market_id - 市场ID（可选）
 * @param {string} params.status - 持仓状态（可选，open/closed/monitoring）
 */
export function getPositions(params = {}) {
  return request({
    url: '/positions/list',
    method: 'get',
    params
  })
}

/**
 * 获取单个持仓详情
 * @param {number} positionId - 持仓ID
 */
export function getPosition(positionId) {
  return request({
    url: `/positions/${positionId}`,
    method: 'get'
  })
}

/**
 * 手动监控单个持仓
 * @param {number} positionId - 持仓ID
 */
export function monitorPosition(positionId) {
  return request({
    url: `/positions/${positionId}/monitor`,
    method: 'post'
  })
}

/**
 * 获取订单列表
 * @param {Object} params - 查询参数
 * @param {string} params.status - 订单状态（可选，pending/filled/cancelled/failed）
 */
export function getOrders(params = {}) {
  return request({
    url: '/positions/orders',
    method: 'get',
    params
  })
}

/**
 * 获取单个订单详情
 * @param {string} orderId - 订单ID
 */
export function getOrder(orderId) {
  return request({
    url: `/positions/orders/${orderId}`,
    method: 'get'
  })
}

/**
 * 手动监控单个订单
 * @param {string} orderId - 订单ID
 */
export function monitorOrder(orderId) {
  return request({
    url: `/positions/orders/${orderId}/monitor`,
    method: 'post'
  })
}

/**
 * 获取市场价格历史数据
 * @param {string} marketId - 市场ID（token_id）
 * @param {Object} params - 查询参数
 * @param {string} params.interval - 时间间隔（1h/6h/1d/1w/1m/max），默认1d
 * @param {number} params.fidelity - 数据分辨率（分钟），默认60
 */
export function getMarketPriceHistory(marketId, params = {}) {
  return request({
    url: `/positions/market/${marketId}/price-history`,
    method: 'get',
    params
  })
}

/**
 * 获取指定市场的所有持仓及价格历史（用于绘制买点）
 * @param {string} marketId - 市场ID
 * @param {Object} params - 查询参数
 * @param {string} params.interval - 时间间隔（1h/6h/1d/1w/1m/max），默认1d
 * @param {number} params.fidelity - 数据分辨率（分钟），默认60
 */
export function getMarketPositions(marketId, params = {}) {
  return request({
    url: `/positions/market/${marketId}/positions`,
    method: 'get',
    params
  })
}

/**
 * 获取单个持仓的价格曲线数据（以购买时刻为基准）
 * @param {number} positionId - 持仓ID
 * @param {Object} params - 查询参数
 * @param {number} params.before_hours - 购买前的小时数，默认24
 * @param {number} params.after_hours - 购买后的小时数，默认24
 * @param {number} params.fidelity - 数据分辨率（分钟），默认60
 */
export function getPositionPriceCurve(positionId, params = {}) {
  return request({
    url: `/positions/${positionId}/price-curve`,
    method: 'get',
    params
  })
}

/**
 * 更新持仓信息
 * @param {number} positionId - 持仓ID
 * @param {Object} data - 更新数据
 * @param {number} data.current_price - 当前价格（可选）
 * @param {string} data.status - 状态（可选，open/closed/monitoring）
 * @param {string} data.settlement_result - 结算结果（可选，YES/NO）
 * @param {number} data.settlement_payout - 结算收益（可选）
 */
export function updatePosition(positionId, data) {
  return request({
    url: `/positions/${positionId}`,
    method: 'put',
    data
  })
}

/**
 * 删除持仓记录
 * @param {number} positionId - 持仓ID
 */
export function deletePosition(positionId) {
  return request({
    url: `/positions/${positionId}`,
    method: 'delete'
  })
}

/**
 * 更新订单信息
 * @param {string} orderId - 订单ID
 * @param {Object} data - 更新数据
 * @param {string} data.status - 状态（可选，pending/filled/cancelled/failed）
 * @param {number} data.filled_size - 已成交数量（可选）
 */
export function updateOrder(orderId, data) {
  return request({
    url: `/positions/orders/${orderId}`,
    method: 'put',
    data
  })
}

/**
 * 删除订单记录
 * @param {string} orderId - 订单ID
 */
export function deleteOrder(orderId) {
  return request({
    url: `/positions/orders/${orderId}`,
    method: 'delete'
  })
}

