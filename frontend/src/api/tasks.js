/**
 * 异步任务管理 API
 */

import request from './request'

/**
 * 获取异步任务列表
 * @param {Object} params - 查询参数
 * @param {string} params.stage - 任务阶段 (mark/analysis/decision/trade/listen)
 * @param {string} params.status - 任务状态 (waiting/processing/success/failed/cancelled)
 * @param {number} params.limit - 返回数量限制
 * @param {number} params.offset - 偏移量
 */
export function getTasks(params = {}) {
  return request({
    url: '/tasks/',
    method: 'get',
    params
  })
}

/**
 * 获取单个任务详情
 * @param {number} taskId - 任务ID
 */
export function getTask(taskId) {
  return request({
    url: `/tasks/${taskId}`,
    method: 'get'
  })
}

/**
 * 创建异步任务
 * @param {Object} data - 任务数据
 * @param {string} data.stage - 任务阶段
 * @param {string} data.status - 任务状态
 * @param {Object} data.metadata - 任务元数据
 */
export function createTask(data) {
  return request({
    url: '/tasks/',
    method: 'post',
    data
  })
}

/**
 * 更新任务
 * @param {number} taskId - 任务ID
 * @param {Object} data - 更新数据
 */
export function updateTask(taskId, data) {
  return request({
    url: `/tasks/${taskId}`,
    method: 'put',
    data
  })
}

/**
 * 删除任务
 * @param {number} taskId - 任务ID
 */
export function deleteTask(taskId) {
  return request({
    url: `/tasks/${taskId}`,
    method: 'delete'
  })
}

