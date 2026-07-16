import request from '../utils/request'

export function listAuditLogs(params = {}) {
  return request.get('/api/v1/audit-logs', { params })
}

export function listActions() {
  return request.get('/api/v1/audit-logs/actions')
}

export function listTables() {
  return request.get('/api/v1/audit-logs/tables')
}
