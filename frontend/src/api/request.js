/**
 * HTTP 请求封装
 */

import axios from 'axios'
import { getToken, clearAuth } from '@/utils/auth'
import router from '@/router'

// 创建 axios 实例（直接指向后端 5000 端口，避免转发问题）
const request = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 10000
})

// 请求拦截器 - 添加认证令牌
request.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    // 处理 401 未授权错误
    if (error.response && error.response.status === 401) {
      clearAuth()
      router.push('/login')
    }
    
    return Promise.reject(error)
  }
)

export default request

