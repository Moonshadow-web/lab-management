import axios from 'axios'

const request = axios.create({
  baseURL: '/',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      import('../router').then((m) => m.default.push('/login'))
    }
    return Promise.reject(error)
  }
)

export default request
