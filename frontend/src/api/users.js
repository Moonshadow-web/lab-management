import request from '../utils/request'

export function listUsers(params = {}) {
  return request.get('/api/v1/users', { params })
}

export function createUser(data) {
  return request.post('/api/v1/users', data)
}

export function updateUser(uid, data) {
  return request.put(`/api/v1/users/${uid}`, data)
}

export function deleteUser(uid) {
  return request.delete(`/api/v1/users/${uid}`)
}

export function resetPassword(uid) {
  return request.post(`/api/v1/users/${uid}/reset-password`)
}

export function getRoleOptions() {
  return request.get('/api/v1/users/role-options')
}
