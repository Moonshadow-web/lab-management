import request from '../utils/request'

export function listRecipients() {
  return request.get('/api/v1/reminders/recipients')
}
export function createRecipient(data) {
  return request.post('/api/v1/reminders/recipients', data)
}
export function updateRecipient(id, data) {
  return request.put(`/api/v1/reminders/recipients/${id}`, data)
}
export function deleteRecipient(id) {
  return request.delete(`/api/v1/reminders/recipients/${id}`)
}
export function getRecipientWxTest(id) {
  return request.post(`/api/v1/reminders/recipients/${id}/wx-test`)
}

export function listRules() {
  return request.get('/api/v1/reminders/rules')
}
export function createRule(data) {
  return request.post('/api/v1/reminders/rules', data)
}
export function updateRule(id, data) {
  return request.put(`/api/v1/reminders/rules/${id}`, data)
}
export function deleteRule(id) {
  return request.delete(`/api/v1/reminders/rules/${id}`)
}

export function runReminders(params) {
  return request.post('/api/v1/reminders/run', null, { params })
}
export function listSendLog(params) {
  return request.get('/api/v1/reminders/send-log', { params })
}
export function initReminderDefaults() {
  return request.post('/api/v1/reminders/init-defaults')
}
