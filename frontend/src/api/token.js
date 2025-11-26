/**
 * Token 管理 API
 */

import request from './request'

/**
 * 获取所有 Token 状态
 */
export function getAllTokenStatus() {
  return request({
    url: '/token/status',
    method: 'get'
  })
}

/**
 * 更新 Token 信息
 * @param {Object} data - Token 数据
 * @param {string} data.token_type - Token 类型
 * @param {string} data.token_value - Token 值
 * @param {string} data.expires_at - 过期时间 (可选)
 */
export function updateToken(data) {
  return request({
    url: '/token/update',
    method: 'post',
    data
  })
}

/**
 * 手动检查所有 Token 过期状态
 */
export function checkAllTokens() {
  return request({
    url: '/token/check',
    method: 'post'
  })
}

/**
 * 手动标记 Token 为过期
 * @param {string} tokenType - Token 类型
 */
export function expireToken(tokenType) {
  return request({
    url: '/token/expire',
    method: 'post',
    data: {
      token_type: tokenType
    }
  })
}

/**
 * 设置检查间隔
 * @param {number} minutes - 检查间隔（分钟）
 */
export function setCheckInterval(minutes) {
  return request({
    url: '/token/config/interval',
    method: 'post',
    data: {
      minutes
    }
  })
}

