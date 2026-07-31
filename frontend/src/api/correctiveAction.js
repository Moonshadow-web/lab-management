import request from '../utils/request'

const BASE = '/api/v1/corrective-actions'

export function listCorrective(params) {
  return request.get(BASE, { params })
}
export function createCorrective(data) {
  return request.post(BASE, data)
}
export function updateCorrective(id, data) {
  return request.put(`${BASE}/${id}`, data)
}
export function deleteCorrective(id) {
  return request.delete(`${BASE}/${id}`)
}
