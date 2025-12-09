/**
 * 钱包管理 API
 */

import request from './request'

/**
 * 获取钱包当前状态
 * @returns {Promise}
 */
export function getPurseStatus() {
  return request({
    url: '/purse/status',
    method: 'get'
  })
}

/**
 * 更新钱包状态
 * @param {Object} data - 更新数据
 * @param {number} data.total_fund - 总资金 (可选)
 * @param {number} data.locked_fund - 锁定资金 (可选)
 * @param {number} data.available_cash - 可用现金 (可选)
 * @param {number} data.loss - 总亏损 (可选)
 * @param {number} data.expect_profit - 预期盈利 (可选)
 * @param {number} data.real_profit - 实际盈利 (可选)
 * @param {number} data.success_market - 成功市场数 (可选)
 * @param {number} data.lost_market - 失败市场数 (可选)
 * @returns {Promise}
 */
export function updatePurseStatus(data) {
  return request({
    url: '/purse/status',
    method: 'put',
    data
  })
}

/**
 * 获取盈亏汇总信息
 * @returns {Promise}
 */
export function getProfitLossSummary() {
  return request({
    url: '/purse/summary',
    method: 'get'
  })
}

/**
 * 获取每日收益记录列表
 * @param {Object} params - 查询参数
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {number} params.limit - 返回记录数量限制
 * @returns {Promise}
 */
export function getDailyRecords(params = {}) {
  return request({
    url: '/purse/daily-records',
    method: 'get',
    params
  })
}

/**
 * 获取指定日期的收益记录
 * @param {string} recordDate - 记录日期 (YYYY-MM-DD)
 * @returns {Promise}
 */
export function getDailyRecord(recordDate) {
  return request({
    url: `/purse/daily-record/${recordDate}`,
    method: 'get'
  })
}

/**
 * 添加每日收益记录
 * @param {Object} data - 记录数据
 * @param {string} data.record_date - 记录日期 (YYYY-MM-DD)
 * @param {number} data.expect_profit - 预期收益
 * @param {number} data.real_profit - 实际收益
 * @param {number} data.total_fund - 总资金 (可选)
 * @param {number} data.success_market - 成功市场数 (可选)
 * @param {number} data.lost_market - 失败市场数 (可选)
 * @param {string} data.notes - 备注 (可选)
 * @returns {Promise}
 */
export function addDailyRecord(data) {
  return request({
    url: '/purse/daily-record',
    method: 'post',
    data
  })
}

/**
 * 更新每日收益记录
 * @param {string} recordDate - 记录日期 (YYYY-MM-DD)
 * @param {Object} data - 更新数据
 * @param {number} data.expect_profit - 预期收益 (可选)
 * @param {number} data.real_profit - 实际收益 (可选)
 * @param {number} data.total_fund - 总资金 (可选)
 * @param {number} data.success_market - 成功市场数 (可选)
 * @param {number} data.lost_market - 失败市场数 (可选)
 * @param {string} data.notes - 备注 (可选)
 * @returns {Promise}
 */
export function updateDailyRecord(recordDate, data) {
  return request({
    url: `/purse/daily-record/${recordDate}`,
    method: 'put',
    data
  })
}

/**
 * 删除每日收益记录
 * @param {string} recordDate - 记录日期 (YYYY-MM-DD)
 * @returns {Promise}
 */
export function deleteDailyRecord(recordDate) {
  return request({
    url: `/purse/daily-record/${recordDate}`,
    method: 'delete'
  })
}

