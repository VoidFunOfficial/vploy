/**
 * 过滤器管理 API
 */

import request from './request'

/**
 * 获取所有黑名单配置项
 * @returns {Promise}
 */
export function getBlacklist() {
  return request({
    url: '/filter/blacklist',
    method: 'get'
  })
}

/**
 * 添加黑名单配置项
 * @param {Object} data - 黑名单数据
 * @param {String} data.blacklist_type - 黑名单类型 (tag/title_keyword/description_keyword)
 * @param {String} data.value - 黑名单值
 * @returns {Promise}
 */
export function addBlacklist(data) {
  return request({
    url: '/filter/blacklist',
    method: 'post',
    data
  })
}

/**
 * 删除黑名单配置项
 * @param {Number} id - 配置项ID
 * @returns {Promise}
 */
export function deleteBlacklist(id) {
  return request({
    url: `/filter/blacklist/${id}`,
    method: 'delete'
  })
}

/**
 * 切换黑名单配置项的激活状态
 * @param {Number} id - 配置项ID
 * @param {Boolean} isActive - 是否激活
 * @returns {Promise}
 */
export function toggleBlacklist(id, isActive) {
  return request({
    url: `/filter/blacklist/${id}/toggle`,
    method: 'put',
    data: { is_active: isActive }
  })
}

/**
 * 获取已处理的事件列表
 * @param {Object} params - 查询参数
 * @param {Number} params.limit - 返回数量限制
 * @param {Number} params.offset - 偏移量
 * @returns {Promise}
 */
export function getProcessedMarkets(params = {}) {
  return request({
    url: '/filter/processed-markets',
    method: 'get',
    params
  })
}

/**
 * 删除单个已处理事件记录
 * @param {String} marketId - Market ID
 * @returns {Promise}
 */
export function deleteProcessedMarket(marketId) {
  return request({
    url: `/filter/processed-markets/${marketId}`,
    method: 'delete'
  })
}

/**
 * 清理已处理事件记录
 * @param {Object} data - 清理参数
 * @param {String} data.before_date - 清理此日期之前的记录（可选）
 * @returns {Promise}
 */
export function clearProcessedMarkets(data = {}) {
  return request({
    url: '/filter/processed-markets/clear',
    method: 'post',
    data
  })
}

