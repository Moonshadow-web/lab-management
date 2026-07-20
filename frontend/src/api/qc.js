import request from '../utils/request'

// ---- 原始质控记录（qc_records 通用 CRUD）----
export function listQC(params) {
  return request.get('/api/v1/qc-records', { params })
}
export function createQC(data) {
  return request.post('/api/v1/qc-records', data)
}
export function updateQC(id, data) {
  return request.put(`/api/v1/qc-records/${id}`, data)
}
export function deleteQC(id) {
  return request.delete(`/api/v1/qc-records/${id}`)
}

// ---- 室内质控月结（qc_monthly_summaries）----
export function listQCSummaries(params) {
  return request.get('/api/v1/qc-summaries', { params })
}
export function uploadQCSummary(file, instrumentId) {
  const form = new FormData()
  form.append('file', file)
  if (instrumentId) form.append('instrument_id', instrumentId)
  return request.post('/api/v1/qc-summaries/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function getQCDaily(id) {
  return request.get(`/api/v1/qc-summaries/${id}/daily`)
}
export function updateQCSummary(id, data) {
  return request.put(`/api/v1/qc-summaries/${id}`, data)
}
export function deleteQCSummary(id) {
  return request.delete(`/api/v1/qc-summaries/${id}`)
}
export function uploadQCPdf(id, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/api/v1/qc-summaries/${id}/pdf`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function downloadQCPdf(id) {
  return request.get(`/api/v1/qc-summaries/${id}/pdf`, { responseType: 'blob' })
}
export function deleteQCPdf(id) {
  return request.delete(`/api/v1/qc-summaries/${id}/pdf`)
}
// 月结文字报告（CZ-012 文字部分）
export function getQCReport(instrumentId, year, month) {
  const params = { year, month }
  if (instrumentId) params.instrument_id = instrumentId
  return request.get('/api/v1/qc-summaries/report', { params })
}
export function upsertQCReport(data) {
  return request.put('/api/v1/qc-summaries/report', data)
}
export function regenerateQCReport(instrumentId, year, month) {
  const params = { year, month }
  if (instrumentId) params.instrument_id = instrumentId
  return request.post('/api/v1/qc-summaries/report/regenerate', null, { params })
}
export function exportQCSummary(year, month, instrumentId) {
  const params = { year, month }
  if (instrumentId) params.instrument_id = instrumentId
  return request.get('/api/v1/qc-summaries/export', {
    params,
    responseType: 'blob',
  })
}
export function exportQCReportDocx(year, month, instrumentId) {
  const params = { year, month }
  if (instrumentId) params.instrument_id = instrumentId
  return request.get('/api/v1/qc-summaries/report/docx', {
    params,
    responseType: 'blob',
  })
}
export function getQCProjectDaily(year, month, instrumentId, testItem) {
  const params = { year, month, instrument_id: instrumentId, test_item: testItem }
  return request.get('/api/v1/qc-summaries/daily/project', { params })
}

export function getQCInstruments() {
  return request.get('/api/v1/qc-summaries/instruments')
}
