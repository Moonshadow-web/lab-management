import request from '../utils/request'

// 比对分组
export function listGroups() {
  return request.get('/api/v1/comparison/groups')
}
// 仪器选择列表（显示型号）
export function instrumentOptions() {
  return request.get('/api/v1/comparison/instruments/options')
}
// 按仪器档案解析给定仪器组的共有项目（含每项适用仪器→遮蔽依据）
export function resolveItems(data) {
  return request.post('/api/v1/comparison/groups/resolve-items', data)
}
export function createGroup(data) {
  return request.post('/api/v1/comparison/groups', data)
}
export function updateGroup(id, data) {
  return request.put(`/api/v1/comparison/groups/${id}`, data)
}
export function deleteGroup(id) {
  return request.delete(`/api/v1/comparison/groups/${id}`)
}

// 比对计划
export function listPlans(params) {
  return request.get('/api/v1/comparison/plans', { params })
}
export function createPlan(data) {
  return request.post('/api/v1/comparison/plans', data)
}
export function updatePlan(id, data) {
  return request.put(`/api/v1/comparison/plans/${id}`, data)
}
export function deletePlan(id) {
  return request.delete(`/api/v1/comparison/plans/${id}`)
}

// 结果录入
export function getResults(planId) {
  return request.get(`/api/v1/comparison/plans/${planId}/results`)
}
// 某分组在某(年份,半年)下尚未比对的项目（同半年补录用）
export function getUncompared(groupId, params) {
  return request.get(`/api/v1/comparison/groups/${groupId}/uncompared`, { params })
}
export function saveResults(planId, data) {
  return request.put(`/api/v1/comparison/plans/${planId}/results`, data)
}
// 从填好的定量比对结果 Excel（如 BG-SM-CZ-025）批量导入
export function importResults(planId, formData) {
  return request.post(`/api/v1/comparison/plans/${planId}/results/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 报告：预览 / 生成 / 下载 / 上传 / 删除
export function previewReport(planId) {
  return request.get(`/api/v1/comparison/plans/${planId}/report/preview`)
}
export function generateReport(planId) {
  return request.post(`/api/v1/comparison/plans/${planId}/report/generate`)
}
export function downloadReport(planId) {
  return request.get(`/api/v1/comparison/plans/${planId}/report`, { responseType: 'blob' })
}
export function uploadReport(planId, file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`/api/v1/comparison/plans/${planId}/report/upload`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function deleteReport(planId) {
  return request.delete(`/api/v1/comparison/plans/${planId}/report`)
}

// 原始结果附件：列表 / 上传(多文件) / 预览 / 下载 / 删除
export function listAttachments(planId) {
  return request.get(`/api/v1/comparison/plans/${planId}/attachments`)
}
export function uploadAttachments(planId, files) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  return request.post(`/api/v1/comparison/plans/${planId}/attachments`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function attachmentUrl(id, inline = true) {
  return `/api/v1/comparison/attachments/${id}${inline ? '?inline=true' : '?inline=false'}`
}
export function deleteAttachment(id) {
  return request.delete(`/api/v1/comparison/attachments/${id}`)
}
