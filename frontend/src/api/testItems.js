import request from '../utils/request'

export function listTestItems(params) {
  return request.get('/api/v1/test-items', { params })
}
export function getTestItem(id) {
  return request.get(`/api/v1/test-items/${id}`)
}
export function createTestItem(data) {
  return request.post('/api/v1/test-items', data)
}
export function updateTestItem(id, data) {
  return request.put(`/api/v1/test-items/${id}`, data)
}
export function deleteTestItem(id) {
  return request.delete(`/api/v1/test-items/${id}`)
}
export function importTestItems(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/v1/test-items/import', fd)
}
export function getTestItemStats() {
  return request.get('/api/v1/test-items/stats')
}
export function exportTestItems(params) {
  return request.get('/api/v1/test-items/export', { params, responseType: 'blob' })
}
