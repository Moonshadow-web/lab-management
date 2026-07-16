import request from '../utils/request'

// 仪器（计划对话框用）
export function interlabInstruments() {
  return request.get('/api/v1/interlab/instruments')
}
// 候选项目（按仪器 + 室间比对可用）
export function interlabProjects(instrumentId) {
  return request.get('/api/v1/interlab/projects', { params: { instrument_id: instrumentId } })
}
// 必做项目总览（无室间质评、需做室间比对的项目及其所属仪器）
export function interlabMandatory() {
  return request.get('/api/v1/interlab/mandatory')
}

// 计划
export function listInterlabPlans(params) {
  return request.get('/api/v1/interlab/plans', { params })
}
export function createInterlabPlan(data) {
  return request.post('/api/v1/interlab/plans', data)
}
export function updateInterlabPlan(id, data) {
  return request.put(`/api/v1/interlab/plans/${id}`, data)
}
export function deleteInterlabPlan(id) {
  return request.delete(`/api/v1/interlab/plans/${id}`)
}

// 结果
export function getInterlabResults(planId) {
  return request.get(`/api/v1/interlab/plans/${planId}/results`)
}
export function saveInterlabResults(planId, data) {
  return request.put(`/api/v1/interlab/plans/${planId}/results`, data)
}

// 报告：预览 / 生成 / 下载 / 上传 / 删除
export function previewInterlabReport(planId) {
  return request.get(`/api/v1/interlab/plans/${planId}/report/preview`)
}
export function generateInterlabReport(planId) {
  return request.post(`/api/v1/interlab/plans/${planId}/report/generate`)
}
export function downloadInterlabReport(planId) {
  return request.get(`/api/v1/interlab/plans/${planId}/report`, { responseType: 'blob' })
}
export function uploadInterlabReport(planId, file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`/api/v1/interlab/plans/${planId}/report/upload`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function deleteInterlabReport(planId) {
  return request.delete(`/api/v1/interlab/plans/${planId}/report`)
}
