/**
 * 认证工具函数
 */

const TOKEN_KEY = 'voidpoly_token'
const USER_KEY = 'voidpoly_user'

/**
 * 获取存储的令牌
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 设置令牌
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 移除令牌
 */
export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 获取用户信息
 */
export function getUser() {
  const userStr = localStorage.getItem(USER_KEY)
  return userStr ? JSON.parse(userStr) : null
}

/**
 * 设置用户信息
 */
export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * 移除用户信息
 */
export function removeUser() {
  localStorage.removeItem(USER_KEY)
}

/**
 * 清除所有认证信息
 */
export function clearAuth() {
  removeToken()
  removeUser()
}

