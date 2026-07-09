import request from '../utils/request'

export function listVerification(params) {
  return request.get('/api/v1/verification-records', { params })
}
export function createVerification(data) {
  return request.post('/api/v1/verification-records', data)
}
export function updateVerification(id, data) {
  return request.put(`/api/v1/verification-records/${id}`, data)
}
export function deleteVerification(id) {
  return request.delete(`/api/v1/verification-records/${id}`)
}
