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
