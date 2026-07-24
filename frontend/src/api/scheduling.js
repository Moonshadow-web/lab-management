import request from '../utils/request'

// 岗位定义
export function listSchedulingPosts(params) {
  return request.get('/api/v1/scheduling/posts', { params })
}
export function createSchedulingPost(data) {
  return request.post('/api/v1/scheduling/posts', data)
}
export function updateSchedulingPost(id, data) {
  return request.put(`/api/v1/scheduling/posts/${id}`, data)
}
export function deleteSchedulingPost(id) {
  return request.delete(`/api/v1/scheduling/posts/${id}`)
}

// 排班计划
export function listSchedulingPlans(params) {
  return request.get('/api/v1/scheduling/plans', { params })
}
export function createSchedulingPlan(data) {
  return request.post('/api/v1/scheduling/plans', data)
}
export function updateSchedulingPlan(id, data) {
  return request.put(`/api/v1/scheduling/plans/${id}`, data)
}
export function deleteSchedulingPlan(id) {
  return request.delete(`/api/v1/scheduling/plans/${id}`)
}

// 每日分配
export function listSchedulingAssignments(params) {
  return request.get('/api/v1/scheduling/assignments', { params })
}
export function createSchedulingAssignment(data) {
  return request.post('/api/v1/scheduling/assignments', data)
}
export function updateSchedulingAssignment(id, data) {
  return request.put(`/api/v1/scheduling/assignments/${id}`, data)
}
export function deleteSchedulingAssignment(id) {
  return request.delete(`/api/v1/scheduling/assignments/${id}`)
}

// 排班表矩阵 / 我的今日 / 自动生成
export function getSchedulingGrid(params) {
  return request.get('/api/v1/scheduling/grid', { params })
}
export function getMyToday(params) {
  return request.get('/api/v1/scheduling/my-today', { params })
}
export function generateScheduling(data) {
  return request.post('/api/v1/scheduling/generate', data)
}

// 排班全局配置（排除人员 / 生成窗口）
export function getSchedulingConfig() {
  return request.get('/api/v1/scheduling/config')
}
export function updateSchedulingConfig(data) {
  return request.put('/api/v1/scheduling/config', data)
}

// 手动录入/修改单个单元格（夜班、休息/病假/开会/行政/质控等）
export function setSchedulingCell(data) {
  return request.post('/api/v1/scheduling/cell', data)
}
