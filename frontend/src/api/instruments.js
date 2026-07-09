import request from '../utils/request'

export function listInstruments(params) {
  return request.get('/api/v1/instruments', { params })
}
export function getInstrument(id) {
  return request.get(`/api/v1/instruments/${id}`)
}
export function createInstrument(data) {
  return request.post('/api/v1/instruments', data)
}
export function updateInstrument(id, data) {
  return request.put(`/api/v1/instruments/${id}`, data)
}
export function deleteInstrument(id) {
  return request.delete(`/api/v1/instruments/${id}`)
}
export function listCalibrations(instrumentId) {
  return request.get(`/api/v1/instruments/${instrumentId}/calibrations`)
}
export function createCalibration(instrumentId, data) {
  return request.post(`/api/v1/instruments/${instrumentId}/calibrations`, data)
}
export function deleteCalibration(instrumentId, recId) {
  return request.delete(`/api/v1/instruments/${instrumentId}/calibrations/${recId}`)
}
