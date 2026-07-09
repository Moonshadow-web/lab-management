import request from '../utils/request'

export function listNC(params) {
  return request.get('/api/v1/nonconformities', { params })
}
export function createNC(data) {
  return request.post('/api/v1/nonconformities', data)
}
export function updateNC(id, data) {
  return request.put(`/api/v1/nonconformities/${id}`, data)
}
export function deleteNC(id) {
  return request.delete(`/api/v1/nonconformities/${id}`)
}
