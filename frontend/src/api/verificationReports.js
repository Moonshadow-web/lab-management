import request from '../utils/request'

// 性能验证报告归档（模板驱动生成 xlsx）
// 走 conclusion-records：后端用最新引擎重算 result_summary，保证老记录也按最新格式展示
export function listVerificationReports(params) {
  return request.get('/api/v1/project-verification-archive/conclusion-records', { params })
}
export function createVerificationReport(data) {
  return request.post('/api/v1/verification-reports', data)
}
export function updateVerificationReport(id, data) {
  return request.put(`/api/v1/verification-reports/${id}`, data)
}
export function deleteVerificationReport(id) {
  return request.delete(`/api/v1/verification-reports/${id}`)
}
export function generateVerificationReport(id) {
  return request.post(`/api/v1/verification-reports/${id}/generate`)
}
export function downloadVerificationReport(id) {
  return request.get(`/api/v1/verification-reports/${id}/download`, { responseType: 'blob' })
}

// 项目查询 ↔ 性能验证联动：按检验项目名/别名/标本匹配验证记录
export function matchVerificationByTestItem(data) {
  return request.post('/api/v1/verification-reports/match-by-test-item', data)
}
