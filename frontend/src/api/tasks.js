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

/**
 * 重试任务
 * @param {number} taskId - 任务ID
 */
export function retryTask(taskId) {
  return request({
    url: `/tasks/${taskId}/retry`,
    method: 'post'
  })
}

/**
 * 批量删除任务
 * @param {Array<number>} taskIds - 任务ID列表
 */
export function batchDeleteTasks(taskIds) {
  return request({
    url: '/tasks/batch-delete',
    method: 'post',
    data: { task_ids: taskIds }
  })
}

/**
 * 获取分析任务的详细状态
 * @param {number} taskId - 任务ID
 */
export function getAnalysisStatus(taskId) {
  return request({
    url: `/tasks/${taskId}/analysis-status`,
    method: 'get'
  })
}

/**
 * 获取分析任务的结果
 * @param {number} taskId - 任务ID
 */
export function getAnalysisResult(taskId) {
  return request({
    url: `/tasks/${taskId}/analysis-result`,
    method: 'get'
  })
}

/**
 * 手动轮询一次分析任务的结果
 * @param {number} taskId - 任务ID
 */
export function pollAnalysisOnce(taskId) {
  return request({
    url: `/tasks/${taskId}/poll-once`,
    method: 'post'
  })
}

/**
 * 拆分成功的analysis任务为多个decision任务
 * @param {number} taskId - 任务ID
 */
export function splitAnalysisTask(taskId) {
  return request({
    url: `/tasks/${taskId}/split`,
    method: 'post'
  })
}

/**
 * 获取待决策任务列表
 */
export function getPendingDecisionTasks() {
  return request({
    url: '/tasks/decision/pending',
    method: 'get'
  })
}

/**
 * 执行决策处理
 */
export function executeDecision() {
  return request({
    url: '/tasks/decision/execute',
    method: 'post'
  })
}

/**
 * 获取待交易任务列表
 */
export function getPendingTradeTasks() {
  return request({
    url: '/tasks/trade/pending',
    method: 'get'
  })
}

/**
 * 获取GPT请求额度状态
 */
export function getGptQuotaStatus() {
  return request({
    url: '/tasks/gpt-quota',
    method: 'get'
  })
}

/**
 * 清理GPT请求记录
 * @param {number} days - 保留天数
 */
export function cleanupGptQuotaRecords(days = 30) {
  return request({
    url: '/tasks/gpt-quota/cleanup',
    method: 'post',
    data: { days }
  })
}
