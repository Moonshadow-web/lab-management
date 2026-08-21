import request from '../utils/request'

// 测量不确定度评定（BG-SM-CZ-072）
export function listUncertainty(params) {
  return request.get('/api/v1/uncertainty', { params })
}
export function createUncertainty(data) {
  return request.post('/api/v1/uncertainty', data)
}
export function updateUncertainty(id, data) {
  return request.put(`/api/v1/uncertainty/${id}`, data)
}
export function deleteUncertainty(id) {
  return request.delete(`/api/v1/uncertainty/${id}`)
}
