import request from '../utils/request'

const BASE = '/api/v1/review'

export function listCampaigns(params) {
  return request.get(`${BASE}/campaigns`, { params })
}
export function createCampaign(data) {
  return request.post(`${BASE}/campaigns`, data)
}
export function updateCampaign(id, data) {
  return request.put(`${BASE}/campaigns/${id}`, data)
}
export function deleteCampaign(id) {
  return request.delete(`${BASE}/campaigns/${id}`)
}
export function listAssignments(params) {
  return request.get(`${BASE}/assignments`, { params })
}
export function createAssignment(data) {
  return request.post(`${BASE}/assignments`, data)
}
export function updateAssignment(id, data) {
  return request.put(`${BASE}/assignments/${id}`, data)
}
export function deleteAssignment(id) {
  return request.delete(`${BASE}/assignments/${id}`)
}
export function assignBatch(cid, items) {
  return request.post(`${BASE}/campaigns/${cid}/assign-batch`, items)
}
export function myAssignments(campaign_id) {
  return request.get(`${BASE}/my-assignments`, { params: { campaign_id } })
}
export function uploadRevision(aid, file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`${BASE}/assignments/${aid}/upload-revision`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function downloadRevisionBlob(aid) {
  return request.get(`${BASE}/assignments/${aid}/download-revision`, { responseType: 'blob' })
}
export function submitReview(aid, record) {
  return request.post(`${BASE}/assignments/${aid}/submit`, record || {})
}
export function myRecord(campaign_id) {
  return request.get(`${BASE}/my-record`, { params: { campaign_id } })
}
export function upsertMyRecord(campaign_id, record_json, submit) {
  return request.post(`${BASE}/my-record`, { record_json }, { params: { campaign_id, submit: submit ? 'true' : 'false' } })
}
export function receiveRevision(aid) {
  return request.post(`${BASE}/assignments/${aid}/receive`)
}
export function reviewSummary(cid) {
  return request.get(`${BASE}/campaigns/${cid}/summary`)
}
export function downloadDocumentBlob(docId) {
  return request.get(`/api/v1/documents/${docId}/download`, { responseType: 'blob' })
}
