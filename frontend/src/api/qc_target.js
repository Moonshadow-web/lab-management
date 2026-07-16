import request from '../utils/request'

// 批号累积靶值
export function listTargetBatches(params) {
  return request.get('/api/v1/qc-target-batches', { params })
}
export function createTargetBatch(data) {
  return request.post('/api/v1/qc-target-batches', data)
}
export function updateTargetBatch(id, data) {
  return request.put(`/api/v1/qc-target-batches/${id}`, data)
}
export function deleteTargetBatch(id) {
  return request.delete(`/api/v1/qc-target-batches/${id}`)
}
export function getMaterialPresets() {
  return request.get('/api/v1/qc-target-batches/materials/presets')
}
export function addTargetResult(batchId, data) {
  return request.post(`/api/v1/qc-target-batches/${batchId}/results`, data)
}
export function listTargetResults(batchId) {
  return request.get(`/api/v1/qc-target-batches/${batchId}/results`)
}
export function deleteTargetResult(batchId, rid) {
  return request.delete(`/api/v1/qc-target-batches/${batchId}/results/${rid}`)
}
export function toggleTargetResult(batchId, rid) {
  return request.post(`/api/v1/qc-target-batches/${batchId}/results/${rid}/toggle`)
}
export function establishTarget(batchId) {
  return request.post(`/api/v1/qc-target-batches/${batchId}/establish`)
}
export function uploadTargetArchive(batchId, file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`/api/v1/qc-target-batches/${batchId}/archive`, fd)
}
export function downloadTargetArchive(batchId) {
  return request.get(`/api/v1/qc-target-batches/${batchId}/archive`, { responseType: 'blob' })
}
