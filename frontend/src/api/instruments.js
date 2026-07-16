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
export function uploadCalibrationReport(instrumentId, recId, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/api/v1/instruments/${instrumentId}/calibrations/${recId}/report`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function downloadCalibrationReport(instrumentId, recId) {
  return request.get(`/api/v1/instruments/${instrumentId}/calibrations/${recId}/report`, { responseType: 'blob' })
}
export function deleteCalibrationReport(instrumentId, recId) {
  return request.delete(`/api/v1/instruments/${instrumentId}/calibrations/${recId}/report`)
}
export function getCalibrationsStatus() {
  return request.get('/api/v1/instruments/calibrations/status')
}

// 仪器档案文件
export function uploadInstrumentArchive(id, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/api/v1/instruments/${id}/archive`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function getInstrumentArchiveInfo(id) {
  return request.get(`/api/v1/instruments/${id}/archive/info`)
}
export function downloadInstrumentArchive(id) {
  return request.get(`/api/v1/instruments/${id}/archive`, { responseType: 'blob' })
}
export function deleteInstrumentArchive(id) {
  return request.delete(`/api/v1/instruments/${id}/archive`)
}
export function getArchivesStatus() {
  return request.get('/api/v1/instruments/archives/status')
}
export function importArchivesFolder(path) {
  return request.post('/api/v1/instruments/archives/import-folder', { path })
}

// 项目「使用仪器」总型号 → 对应仪器档案清单（一对多）
export function getInstrumentFamilyMap() {
  return request.get('/api/v1/instruments/family-map')
}

// 反向索引：仪器 → 对应的项目列表
export function getInstrumentTestItems(id) {
  return request.get(`/api/v1/instruments/${id}/test-items`)
}

// 反向索引：仪器 → 关联文档（操作+保养记录等）
export function getInstrumentDocuments(id) {
  return request.get(`/api/v1/instruments/${id}/documents`)
}

// ---- 总型号 ↔ 仪器 关联管理 ----
export function listInstrumentFamilies() {
  return request.get('/api/v1/instrument-families')
}
export function getInstrumentFamily(id) {
  return request.get(`/api/v1/instrument-families/${id}`)
}
export function createInstrumentFamily(data) {
  return request.post('/api/v1/instrument-families', data)
}
export function updateInstrumentFamily(id, data) {
  return request.put(`/api/v1/instrument-families/${id}`, data)
}
export function deleteInstrumentFamily(id) {
  return request.delete(`/api/v1/instrument-families/${id}`)
}
export function setFamilyMembers(id, instrumentIds) {
  return request.put(`/api/v1/instrument-families/${id}/members`, { instrument_ids: instrumentIds })
}
