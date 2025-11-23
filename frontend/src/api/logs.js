/**
 * 日志管理 API
 */

import request from './request'

/**
 * 查询日志
 * @param {Object} params - 查询参数
 * @param {Number} params.limit - 返回最后N条日志
 * @param {Array} params.level - 日志等级过滤
 * @param {String} params.event - 事件类型过滤
 * @param {String} params.keyword - 关键词搜索
 * @param {String} params.trace_id - trace_id精确查询
 * @param {String} params.start_time - 开始时间
 * @param {String} params.end_time - 结束时间
 * @returns {Promise}
 */
export function queryLogs(params = {}) {
  return request({
    url: '/logs/query',
    method: 'post',
    data: params
  })
}

/**
 * 导出日志
 * @param {Object} params - 导出参数
 * @param {String} params.format - 导出格式: json/csv/txt
 * @param {Object} params.filters - 过滤条件
 * @returns {Promise}
 */
export function exportLogs(params = {}) {
  return request({
    url: '/logs/export',
    method: 'post',
    data: params,
    responseType: params.format === 'json' ? 'json' : 'blob'
  })
}

