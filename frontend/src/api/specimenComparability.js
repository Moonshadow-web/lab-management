import request from '../utils/request'

// 样本类型可比性验证（CNAS-CL02:2023 7.3.7.4）
export function listSpecimenComparisons(params) {
  return request.get('/api/v1/specimen-comparability', { params })
}
export function createSpecimenComparison(data) {
  return request.post('/api/v1/specimen-comparability', data)
}
export function updateSpecimenComparison(id, data) {
  return request.put(`/api/v1/specimen-comparability/${id}`, data)
}
export function deleteSpecimenComparison(id) {
  return request.delete(`/api/v1/specimen-comparability/${id}`)
}
export function computeSpecimenComparison(id) {
  return request.post(`/api/v1/specimen-comparability/${id}/compute`)
}
export function generateSpecimenComparison(id) {
  return request.post(`/api/v1/specimen-comparability/${id}/generate`)
}
export function downloadSpecimenComparison(id) {
  return request.get(`/api/v1/specimen-comparability/${id}/download`, { responseType: 'blob' })
}
export function specimenCharts(id) {
  return request.get(`/api/v1/specimen-comparability/${id}/charts`)
}
export function summarySpecimenComparisons(params) {
  return request.get('/api/v1/specimen-comparability/summary', params ? { params } : undefined)
}
