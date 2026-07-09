import request from '../utils/request'

export function login(username, password) {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return request.post('/api/v1/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function getMe() {
  return request.get('/api/v1/auth/me')
}
