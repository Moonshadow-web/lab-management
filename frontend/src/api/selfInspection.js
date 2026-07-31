import request from '../utils/request'

const BASE = '/api/v1'

export function listClauses(params) {
  return request.get(`${BASE}/audit-clauses`, { params })
}
export function createClause(data) {
  return request.post(`${BASE}/audit-clauses`, data)
}
export function updateClause(id, data) {
  return request.put(`${BASE}/audit-clauses/${id}`, data)
}
export function deleteClause(id) {
  return request.delete(`${BASE}/audit-clauses/${id}`)
}
export function batchImportClauses(items) {
  return request.post(`${BASE}/audit-clauses/batch-import`, items)
}
export function listCampaigns(params) {
  return request.get(`${BASE}/self-inspection/campaigns`, { params })
}
export function createCampaign(data) {
  return request.post(`${BASE}/self-inspection/campaigns`, data)
}
export function updateCampaign(id, data) {
  return request.put(`${BASE}/self-inspection/campaigns/${id}`, data)
}
export function deleteCampaign(id) {
  return request.delete(`${BASE}/self-inspection/campaigns/${id}`)
}
export function listAssignments(params) {
  return request.get(`${BASE}/self-inspection/assignments`, { params })
}
export function createAssignment(data) {
  return request.post(`${BASE}/self-inspection/assignments`, data)
}
export function updateAssignment(id, data) {
  return request.put(`${BASE}/self-inspection/assignments/${id}`, data)
}
export function deleteAssignment(id) {
  return request.delete(`${BASE}/self-inspection/assignments/${id}`)
}
export function assignClausesBatch(cid, items) {
  return request.post(`${BASE}/self-inspection/campaigns/${cid}/assign-batch`, items)
}
export function myAssignments(campaign_id) {
  return request.get(`${BASE}/self-inspection/my-assignments`, { params: { campaign_id } })
}
export function assignmentClauses(aid) {
  return request.get(`${BASE}/self-inspection/assignments/${aid}/clauses`)
}
export function upsertRecord(payload) {
  return request.post(`${BASE}/self-inspection/records/upsert`, payload)
}
export function submitAssignment(aid) {
  return request.post(`${BASE}/self-inspection/assignments/${aid}/submit`)
}
export function selfInspectionSummary(cid) {
  return request.get(`${BASE}/self-inspection/campaigns/${cid}/summary`)
}
