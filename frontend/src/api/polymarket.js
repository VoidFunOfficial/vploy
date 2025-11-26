/**
 * Polymarket API 接口
 */

import request from './request'

/**
 * 通过 slug 获取事件
 * @param {string} slug - 事件 slug
 */
export function getEventBySlug(slug) {
  return request({
    url: `/polymarket/event/slug/${slug}`,
    method: 'get'
  })
}

/**
 * 通过 ID 获取事件
 * @param {string} eventId - 事件 ID
 */
export function getEventById(eventId) {
  return request({
    url: `/polymarket/event/id/${eventId}`,
    method: 'get'
  })
}

/**
 * 通过 slug 获取市场
 * @param {string} slug - 市场 slug
 */
export function getMarketBySlug(slug) {
  return request({
    url: `/polymarket/market/slug/${slug}`,
    method: 'get'
  })
}

/**
 * 通过 ID 获取市场
 * @param {string} marketId - 市场 ID
 */
export function getMarketById(marketId) {
  return request({
    url: `/polymarket/market/id/${marketId}`,
    method: 'get'
  })
}

/**
 * 获取事件列表
 * @param {Object} params - 查询参数
 */
export function getEvents(params = {}) {
  return request({
    url: '/polymarket/events',
    method: 'get',
    params
  })
}

/**
 * 获取市场列表
 * @param {Object} params - 查询参数
 */
export function getMarkets(params = {}) {
  return request({
    url: '/polymarket/markets',
    method: 'get',
    params
  })
}

