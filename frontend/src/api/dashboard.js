import request from '../utils/request'

/** 工作台聚合统计——一次请求返回所有模块计数 */
export function getDashboardStats() {
  return request.get('/api/v1/dashboard/stats')
}
