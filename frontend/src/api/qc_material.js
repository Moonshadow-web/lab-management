import request from '../utils/request'

// 质控品主数据（含项目清单）
export function listQcMaterials(params) {
  return request.get('/api/v1/qc-materials', { params })
}
export function createQcMaterial(data) {
  return request.post('/api/v1/qc-materials', data)
}
export function updateQcMaterial(id, data) {
  return request.put(`/api/v1/qc-materials/${id}`, data)
}
export function deleteQcMaterial(id) {
  return request.delete(`/api/v1/qc-materials/${id}`)
}
