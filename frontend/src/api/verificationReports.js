import request from '../utils/request'

// 性能验证报告归档（模板驱动生成 xlsx）
export function listVerificationReports(params) {
  return request.get('/api/v1/verification-reports', { params })
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
