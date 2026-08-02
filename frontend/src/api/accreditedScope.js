import request from '../utils/request'

const BASE = '/api/v1/accredited-scope'

export function listScopes(params) {
  return request.get(BASE, { params })
}
export function createScope(data) {
  return request.post(BASE, data)
}
export function updateScope(id, data) {
  return request.put(`${BASE}/${id}`, data)
}
export function deleteScope(id) {
  return request.delete(`${BASE}/${id}`)
}
// 批量导入（xlsx 种子脚本调用；前端暂未直接调用）
export function batchImportScopes(items, replace = false) {
  return request.post(`${BASE}/batch?replace=${replace ? 'true' : 'false'}`, items)
}
