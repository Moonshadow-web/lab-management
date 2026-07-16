import request from '../utils/request'

export function listDocuments(params) {
  return request.get('/api/v1/documents', { params })
}
export function getDocument(id) {
  return request.get(`/api/v1/documents/${id}`)
}
export function updateDocument(id, data) {
  return request.patch(`/api/v1/documents/${id}`, data)
}
export function uploadDocument(formData) {
  return request.post('/api/v1/documents/upload', formData)
}
export function newVersion(docId, formData) {
  return request.post(`/api/v1/documents/${docId}/new-version`, formData)
}
export function listVersions(docId) {
  return request.get(`/api/v1/documents/${docId}/versions`)
}
export function deleteDocument(id) {
  return request.delete(`/api/v1/documents/${id}`)
}
// 项目说明书 → 项目查询 关联（卡片预览用）
export function listProjectManuals() {
  return request.get('/api/v1/documents/project-manuals')
}

// 文件更改日志
export function listChangeLogs(params) {
  return request.get('/api/v1/change-logs', { params })
}
export function exportChangeLogs(params = {}) {
  return request.get('/api/v1/change-logs/export', { params, responseType: 'blob' })
}
export function setChangeLogHandled(id, handled) {
  return request.patch(`/api/v1/change-logs/${id}`, { handled })
}

// 下载/预览需要携带鉴权头，故用 axios 取 blob 再处理（直接 window.open 会被 401 拦截）
// 追加时间戳 query 以绕过浏览器/代理对文件响应的缓存（避免预览到旧的/未转换文件）
export async function fetchDocumentBlob(id, action = 'download') {
  return request.get(`/api/v1/documents/${id}/${action}?_=${Date.now()}`, { responseType: 'blob' })
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'download'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function previewBlob(blob) {
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}
