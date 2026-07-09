import request from '../utils/request'

export function listTraining(params) {
  return request.get('/api/v1/training-records', { params })
}
export function createTraining(data) {
  return request.post('/api/v1/training-records', data)
}
export function updateTraining(id, data) {
  return request.put(`/api/v1/training-records/${id}`, data)
}
export function deleteTraining(id) {
  return request.delete(`/api/v1/training-records/${id}`)
}
