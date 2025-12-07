/**
 * 系统设置管理 API
 */

import request from './request'

/**
 * 获取所有系统设置项
 * @returns {Promise}
 */
export function getAllSettings() {
  return request({
    url: '/sys_settings',
    method: 'get'
  })
}

/**
 * 获取指定key的系统设置项
 * @param {String} key - 设置键
 * @returns {Promise}
 */
export function getSetting(key) {
  return request({
    url: `/sys_settings/${key}`,
    method: 'get'
  })
}

/**
 * 新增系统设置项
 * @param {Object} data - 设置数据
 * @param {String} data.key - 设置键
 * @param {Any} data.value - 设置值
 * @param {String} data.value_type - 值类型（可选）
 * @param {String} data.description - 描述（可选）
 * @returns {Promise}
 */
export function createSetting(data) {
  return request({
    url: '/sys_settings',
    method: 'post',
    data
  })
}

/**
 * 更新系统设置项
 * @param {String} key - 设置键
 * @param {Object} data - 设置数据
 * @param {Any} data.value - 设置值
 * @param {String} data.value_type - 值类型（可选）
 * @param {String} data.description - 描述（可选）
 * @returns {Promise}
 */
export function updateSetting(key, data) {
  return request({
    url: `/sys_settings/${key}`,
    method: 'put',
    data
  })
}

/**
 * 删除系统设置项
 * @param {String} key - 设置键
 * @returns {Promise}
 */
export function deleteSetting(key) {
  return request({
    url: `/sys_settings/${key}`,
    method: 'delete'
  })
}

