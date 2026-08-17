import request from '../utils/request'

// 报告归档（独立文件库，来源：generated / uploaded）
export function listReportArchives(params) {
  return request.get('/api/v1/report-archives', { params })
}
export function deleteReportArchive(id) {
  return request.delete(`/api/v1/report-archives/${id}`)
}
export function downloadReportArchive(id) {
  return request.get(`/api/v1/report-archives/${id}/download`, { responseType: 'blob' })
}
export function uploadReportArchive(formData) {
  return request.post('/api/v1/report-archives/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
// 老数据回填：重新解析已上传归档 → 新建 verification_reports 记录并关联
export function reparseReportArchive(id) {
  return request.post(`/api/v1/report-archives/${id}/reparse`)
}
