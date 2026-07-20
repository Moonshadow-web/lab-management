import request from '../utils/request'

export function listNotifications(params) {
  return request.get('/api/v1/notifications', { params })
}
export function markRead(nid) {
  return request.post(`/api/v1/notifications/${nid}/read`)
}
export function markAllRead() {
  return request.post('/api/v1/notifications/read-all')
}
export function testEmail(to) {
  return request.post('/api/v1/notifications/test-email', to ? { to } : {})
}
