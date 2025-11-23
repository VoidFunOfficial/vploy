/**
 * 系统监控相关 API
 */

import request from './request'

/**
 * 获取系统监控数据
 */
export function getSystemMonitor() {
  return request({
    url: '/monitor/system',
    method: 'get'
  })
}

