import request from '../utils/request'

export function listQC(params) {
  return request.get('/api/v1/qc-records', { params })
}
export function createQC(data) {
  return request.post('/api/v1/qc-records', data)
}
export function updateQC(id, data) {
  return request.put(`/api/v1/qc-records/${id}`, data)
}
export function deleteQC(id) {
  return request.delete(`/api/v1/qc-records/${id}`)
}
