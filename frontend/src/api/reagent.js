/**
 * 试剂管理模块 API 调用
 */

import request from '../utils/request'

// ── 试剂目录 ──
export function listReagentItems(params) {
  return request.get('/api/v1/reagent/items', { params })
}

// 分页拉全试剂目录（后端 page_size 上限 200，超 200 触发 422）。
// 用于在库存/月消耗等页面一次性拿到全部试剂映射，避免 [object Object] 报错。
// 默认包含停用项（show_inactive=true），保证盘库详情/打印的名称映射完整。
export async function listAllReagentItems(extra = {}) {
  let page = 1
  const all = []
  while (true) {
    const r = await listReagentItems({ page, page_size: 200, show_inactive: true, ...extra })
    all.push(...(r.items || []))
    if (all.length >= (r.total || 0) || (r.items || []).length === 0) break
    page += 1
    if (page > 100) break
  }
  return all
}

// 盘库/订购录入模板：按项目、仪器家族、质控品分组（含实时库存）
export function getReagentTemplate(params) {
  return request.get('/api/v1/reagent/template', { params })
}

export function getReagentItem(id) {
  return request.get(`/api/v1/reagent/items/${id}`)
}

export function createReagentItem(data) {
  return request.post('/api/v1/reagent/items', data)
}

export function updateReagentItem(id, data) {
  return request.put(`/api/v1/reagent/items/${id}`, data)
}

export function deleteReagentItem(id) {
  return request.delete(`/api/v1/reagent/items/${id}`)
}

export function importReagentFromExcel(formData) {
  return request.post('/api/v1/reagent/items/_import-excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── 实时库存 ──
export function listReagentStock(params) {
  return request.get('/api/v1/reagent/stock', { params })
}

// ── 盘库 ──
export function listInventoryChecks(params) {
  return request.get('/api/v1/reagent/inventory-checks', { params })
}

export function getInventoryCheck(id) {
  return request.get(`/api/v1/reagent/inventory-checks/${id}`)
}

export function createInventoryCheck(data) {
  return request.post('/api/v1/reagent/inventory-checks', data)
}

export function deleteInventoryCheck(id) {
  return request.delete(`/api/v1/reagent/inventory-checks/${id}`)
}

// ── 订购 ──
export function listReagentOrders(params) {
  return request.get('/api/v1/reagent/orders', { params })
}

export function getReagentOrder(id) {
  return request.get(`/api/v1/reagent/orders/${id}`)
}

export function createReagentOrder(data) {
  return request.post('/api/v1/reagent/orders', data)
}

export function updateReagentOrder(id, data) {
  return request.put(`/api/v1/reagent/orders/${id}`, data)
}

export function deleteReagentOrder(id) {
  return request.delete(`/api/v1/reagent/orders/${id}`)
}

export function exportOrderForm(id) {
  return request.get(`/api/v1/reagent/orders/${id}/export-form`, { responseType: 'blob' })
}

// ── 到货接收 ──
export function listReagentReceivings(params) {
  return request.get('/api/v1/reagent/receivings', { params })
}

export function getReagentReceiving(id) {
  return request.get(`/api/v1/reagent/receivings/${id}`)
}

export function createReagentReceiving(data) {
  return request.post('/api/v1/reagent/receivings', data)
}

export function updateReagentReceiving(id, data) {
  return request.put(`/api/v1/reagent/receivings/${id}`, data)
}

export function confirmReagentReceiving(id) {
  return request.post(`/api/v1/reagent/receivings/${id}/confirm`)
}

// ── 月消耗 ──
export function listReagentConsumption(params) {
  return request.get('/api/v1/reagent/consumption', { params })
}

export function calculateConsumption(yearMonth) {
  return request.post(`/api/v1/reagent/consumption/_calculate?year_month=${yearMonth}`)
}

// ── 项目↔试剂 / 仪器↔耗材 关联 ──
export function listTestItemReagents(params) {
  return request.get('/api/v1/reagent/associations/test-items', { params })
}
export function createTestItemReagent(data) {
  return request.post('/api/v1/reagent/associations/test-items', data)
}
export function updateTestItemReagent(id, data) {
  return request.put(`/api/v1/reagent/associations/test-items/${id}`, data)
}
export function deleteTestItemReagent(id) {
  return request.delete(`/api/v1/reagent/associations/test-items/${id}`)
}
export function listInstrumentReagents(params) {
  return request.get('/api/v1/reagent/associations/instruments', { params })
}
export function createInstrumentReagent(data) {
  return request.post('/api/v1/reagent/associations/instruments', data)
}
export function updateInstrumentReagent(id, data) {
  return request.put(`/api/v1/reagent/associations/instruments/${id}`, data)
}
export function deleteInstrumentReagent(id) {
  return request.delete(`/api/v1/reagent/associations/instruments/${id}`)
}
export function autoMatchAssociations(reset = false) {
  return request.post(`/api/v1/reagent/associations/_auto-match?reset=${reset}`)
}

// 待关联建议：返回未关联但可匹配 / 真正无候选的试剂，供人工审核采纳
export function getAssociationSuggestions(params = {}) {
  return request.get('/api/v1/reagent/associations/suggestions', { params })
}
