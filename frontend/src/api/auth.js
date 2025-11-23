/**
 * 认证相关 API
 */

import request from './request'

/**
 * 用户登录
 */
export function login(username, password) {
  return request({
    url: '/auth/login',
    method: 'post',
    data: {
      username,
      password
    }
  })
}

/**
 * 用户登出
 */
export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}

/**
 * 验证令牌
 */
export function verifyToken() {
  return request({
    url: '/auth/verify',
    method: 'get'
  })
}

