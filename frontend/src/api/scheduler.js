/**
 * 定时任务管理 API
 */

import request from './request'

/**
 * 获取定时任务列表
 * @param {Object} params - 查询参数
 * @param {string} params.enabled - 是否启用 (true/false/all)
 * @param {number} params.limit - 返回数量限制
 * @param {number} params.offset - 偏移量
 */
export function getScheduledTasks(params = {}) {
  return request({
    url: '/scheduler/tasks',
    method: 'get',
    params
  })
}

/**
 * 获取单个定时任务详情
 * @param {number} taskId - 任务ID
 */
export function getScheduledTask(taskId) {
  return request({
    url: `/scheduler/tasks/${taskId}`,
    method: 'get'
  })
}

/**
 * 创建定时任务
 * @param {Object} data - 任务数据
 * @param {string} data.name - 任务名称
 * @param {string} data.task_type - 任务类型 (interval/cron)
 * @param {string} data.schedule - 调度配置
 * @param {boolean} data.enabled - 是否启用
 * @param {Object} data.metadata - 任务元数据
 */
export function createScheduledTask(data) {
  return request({
    url: '/scheduler/tasks',
    method: 'post',
    data
  })
}

/**
 * 更新定时任务
 * @param {number} taskId - 任务ID
 * @param {Object} data - 更新数据
 */
export function updateScheduledTask(taskId, data) {
  return request({
    url: `/scheduler/tasks/${taskId}`,
    method: 'put',
    data
  })
}

/**
 * 删除定时任务
 * @param {number} taskId - 任务ID
 */
export function deleteScheduledTask(taskId) {
  return request({
    url: `/scheduler/tasks/${taskId}`,
    method: 'delete'
  })
}

/**
 * 立即执行定时任务一次
 * @param {number} taskId - 任务ID
 */
export function runScheduledTaskNow(taskId) {
  return request({
    url: `/scheduler/tasks/${taskId}/run`,
    method: 'post'
  })
}

