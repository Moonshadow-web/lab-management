import request from '../utils/request'

export function listQualityRequirements(params) {
  return request.get('/api/v1/quality-requirements', { params })
}
export function getQualityRequirement(id) {
  return request.get(`/api/v1/quality-requirements/${id}`)
}
export function createQualityRequirement(data) {
  return request.post('/api/v1/quality-requirements', data)
}
export function updateQualityRequirement(id, data) {
  return request.put(`/api/v1/quality-requirements/${id}`, data)
}
export function deleteQualityRequirement(id) {
  return request.delete(`/api/v1/quality-requirements/${id}`)
}
export function listQualitySources() {
  return request.get('/api/v1/quality-requirements/_meta/sources')
}
export function seedQualityRequirements() {
  return request.post('/api/v1/quality-requirements/_meta/seed')
}
export function getQualityMatrix(params) {
  return request.get('/api/v1/quality-requirements/_meta/matrix', { params })
}
