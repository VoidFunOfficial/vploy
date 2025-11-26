/**
 * 数据库管理相关 API
 */

import request from './request'

/**
 * 获取所有数据库表列表
 */
export function getTables() {
  return request({
    url: '/database/tables',
    method: 'get'
  })
}

/**
 * 获取指定表的结构信息
 * @param {string} tableName - 表名
 */
export function getTableSchema(tableName) {
  return request({
    url: `/database/schema/${tableName}`,
    method: 'get'
  })
}

/**
 * 获取指定表的数据
 * @param {string} tableName - 表名
 * @param {object} params - 查询参数 { page, page_size, order_by, order }
 */
export function getTableData(tableName, params = {}) {
  return request({
    url: `/database/data/${tableName}`,
    method: 'get',
    params
  })
}

/**
 * 创建新行
 * @param {string} tableName - 表名
 * @param {object} data - 行数据
 */
export function createRow(tableName, data) {
  return request({
    url: `/database/row/${tableName}`,
    method: 'post',
    data: { data }
  })
}

/**
 * 更新行
 * @param {string} tableName - 表名
 * @param {number} rowId - 行ID
 * @param {object} data - 更新的数据
 */
export function updateRow(tableName, rowId, data) {
  return request({
    url: `/database/row/${tableName}/${rowId}`,
    method: 'put',
    data: { data }
  })
}

/**
 * 删除行
 * @param {string} tableName - 表名
 * @param {number} rowId - 行ID
 */
export function deleteRow(tableName, rowId) {
  return request({
    url: `/database/row/${tableName}/${rowId}`,
    method: 'delete'
  })
}

