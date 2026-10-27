import request from '../utils/request'

// 方法学比对（EP9-A3）：新方法 vs 现行方法
export function listMethodComparisons(params) {
  return request.get('/api/v1/method-comparison', { params })
}
export function createMethodComparison(data) {
  return request.post('/api/v1/method-comparison', data)
}
export function updateMethodComparison(id, data) {
  return request.put(`/api/v1/method-comparison/${id}`, data)
}
export function deleteMethodComparison(id) {
  return request.delete(`/api/v1/method-comparison/${id}`)
}
export function computeMethodComparison(id) {
  return request.post(`/api/v1/method-comparison/${id}/compute`)
}
export function generateMethodComparison(id) {
  return request.post(`/api/v1/method-comparison/${id}/generate`)
}
export function downloadMethodComparison(id) {
  return request.get(`/api/v1/method-comparison/${id}/download`, { responseType: 'blob' })
}
export function summaryMethodComparisons(params) {
  return request.get('/api/v1/method-comparison/summary', { params })
}
export function downloadMethodComparisonSummary(params) {
  return request.get('/api/v1/method-comparison/summary/download', { params, responseType: 'blob' })
}
