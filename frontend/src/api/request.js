/**
 * HTTP 请求封装
 */

import axios from 'axios'
import { getToken, clearAuth } from '@/utils/auth'
import router from '@/router'

const isProd = import.meta.env.PROD
const envApiUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL
const baseURL = envApiUrl
  ? envApiUrl
  : (isProd
    ? `${window.location.protocol}//${window.location.hostname}:5000/api`
    : '/api')

const request = axios.create({
  baseURL,
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
