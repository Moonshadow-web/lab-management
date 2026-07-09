import request from '../utils/request'

export function listReagents(params) {
  return request.get('/api/v1/reagents', { params })
}
export function createReagent(data) {
  return request.post('/api/v1/reagents', data)
}
export function updateReagent(id, data) {
  return request.put(`/api/v1/reagents/${id}`, data)
}
export function deleteReagent(id) {
  return request.delete(`/api/v1/reagents/${id}`)
}
