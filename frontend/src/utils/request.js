import axios from 'axios'

const API_BASE = '/'
const request = axios.create({
  baseURL: API_BASE,
  // 大文件(仪器LIS/质控 Excel)上传+服务端解析耗时较长，放宽至 120s
  timeout: 120000,
})

// 刷新锁 + 并发请求队列：多个请求同时 401 时只发一次 refresh
let isRefreshing = false
let pendingQueue = []

function flushQueue(error, token) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token)
    else reject(error)
  })
  pendingQueue = []
}

function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

function gotoLogin() {
  import('../router').then((m) => {
    const router = m.default
    const cur = router.currentRoute.value
    // 已在登录页则不重复跳转，避免循环
    if (cur.name === 'login') return
    // 记住当前页面，登录成功后回跳，避免被踢到工作台
    const redirect = cur.fullPath
    router.push({ path: '/login', query: redirect && redirect !== '/login' ? { redirect } : {} })
  })
}

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const original = error.config || {}
    const status = error.response && error.response.status

    // 仅在 access token 过期(401) 且尚未重试过时尝试用 refresh token 续期
    if (status === 401 && !original._retry) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        clearAuth()
        gotoLogin()
        return Promise.reject(error)
      }

      // 已有刷新在进行中：排队，等拿到新 token 后重试
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push({
            resolve: (token) => {
              original._retry = true
              original.headers = original.headers || {}
              original.headers.Authorization = `Bearer ${token}`
              resolve(request(original))
            },
            reject: () => reject(error),
          })
        })
      }

      original._retry = true
      isRefreshing = true
      try {
        // 用裸 axios 直连，避免落入本实例的响应拦截器造成递归
        const resp = await axios.post(
          API_BASE + 'api/v1/auth/refresh',
          { refresh_token: refreshToken },
          // 续期接口本身很快，但放宽到 30s 以免弱网/服务端抖动误断
          { baseURL: API_BASE, timeout: 30000 }
        )
        const data = resp.data
        const newAccess = data.access_token
        const newRefresh = data.refresh_token
        localStorage.setItem('token', newAccess)
        if (newRefresh) localStorage.setItem('refresh_token', newRefresh)
        flushQueue(null, newAccess)
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${newAccess}`
        return request(original)
      } catch (e) {
        flushQueue(e, null)
        clearAuth()
        gotoLogin()
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default request
