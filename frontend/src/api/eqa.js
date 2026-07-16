import request from '../utils/request'

// 室间质评（EQA）年度计划 CRUD
export function listEqaPlans(params) {
  return request.get('/api/v1/eqa-plans', { params })
}
export function createEqaPlan(data) {
  return request.post('/api/v1/eqa-plans', data)
}
export function updateEqaPlan(id, data) {
  return request.put(`/api/v1/eqa-plans/${id}`, data)
}
export function deleteEqaPlan(id) {
  return request.delete(`/api/v1/eqa-plans/${id}`)
}
// 检测提醒：未回报且临近回报截止（或已逾期）
export function getEqaAlerts() {
  return request.get('/api/v1/eqa-plans/alerts')
}
// 半年/年度总结统计
export function getEqaSummary(year, half) {
  return request.get('/api/v1/eqa-plans/summary', { params: { year, half } })
}
// 半年总结文字（可编辑）—— 按（质评部门 × 专业组）分别存
export function getEqaSummaryText(year, half, category, department) {
  return request.get('/api/v1/eqa-plans/summary-text', { params: { year, half, category, department } })
}
export function upsertEqaSummaryText(data) {
  return request.put('/api/v1/eqa-plans/summary-text', data)
}
// 按（质评部门 × 专业组）的细项合格率统计（细项已去重）
export function getEqaSummaryByCategory(year, half, category, department) {
  return request.get('/api/v1/eqa-plans/summary-by-category', { params: { year, half, category, department } })
}
// 保存某（部门×专业组）总结文字并生成 Word（自动存档）
export function generateEqaSummary(data) {
  return request.post('/api/v1/eqa-plans/summary-generate', data)
}
// 某（部门×专业组）总结 Word 下载地址
export function eqaSummaryDocUrl(year, half, category, department) {
  const cat = encodeURIComponent(category || '生化+凝血')
  const dep = encodeURIComponent(department || '卫健委')
  return `/api/v1/eqa-plans/summary-docx?year=${year}&half=${half}&department=${dep}&category=${cat}&_=${Date.now()}`
}
// 结果报告合并打印：按（年度 × 半年 × 质评部门 × 专业组）合并已导入报告 PDF，返回 blob
export function mergeEqaReports(params) {
  return request.get('/api/v1/eqa-plans/reports-merge', { params, responseType: 'blob' })
}
// 导出年度计划清单 Excel（可按机构、专业组过滤）
export function exportEqaPlans(year, org, group) {
  const params = { year }
  if (org) params.org = org
  if (group) params.group = group
  return request.get('/api/v1/eqa-plans/export', { params, responseType: 'blob' })
}
// 一键复制上一年全部质评计划到目标年（targetYear 默认今年）
export function copyPrevYearEqa(targetYear) {
  const params = {}
  if (targetYear) params.target_year = targetYear
  return request.post('/api/v1/eqa-plans/copy-prev-year', null, { params })
}

// 导入 / 下载 / 删除质评报告 PDF（卫健委 / 北京市）
// extra: { score, result, qualified } 可选，随 PDF 一并回填成绩与合格与否
export function uploadEqaReport(planId, file, extra) {
  const fd = new FormData()
  fd.append('file', file)
  if (extra) {
    if (extra.score !== undefined && extra.score !== null && extra.score !== '') {
      fd.append('score', String(extra.score))
    }
    if (extra.result !== undefined && extra.result !== null && extra.result !== '') {
      fd.append('result', String(extra.result))
    }
    if (extra.qualified !== undefined && extra.qualified !== null) {
      fd.append('qualified', extra.qualified ? 'true' : 'false')
    }
  }
  return request.post(`/api/v1/eqa-plans/report/${planId}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function downloadEqaReport(planId) {
  return request.get(`/api/v1/eqa-plans/report/${planId}`, { responseType: 'blob' })
}
export function deleteEqaReport(planId) {
  return request.delete(`/api/v1/eqa-plans/report/${planId}`)
}

// 逐项「录入结果」矩阵读写（样本×项目，可打印双人签字审核单）
export function getEqaResult(planId) {
  return request.get(`/api/v1/eqa-plans/${planId}/result`)
}
export function saveEqaResult(planId, data) {
  return request.put(`/api/v1/eqa-plans/${planId}/result`, data)
}

// 项目库与室间质评关联（只读）
export function listEqaAssociations(params) {
  return request.get('/api/v1/eqa-associations', { params })
}
