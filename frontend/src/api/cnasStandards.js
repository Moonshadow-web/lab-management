import request from '../utils/request'
import { downloadBlob, previewBlob } from './documents'

export function listCnasStandards() {
  return request.get('/api/v1/cnas-standards')
}

// 预览/下载需携带鉴权头，故用 axios 取 blob 再处理（直接 window.open 会被 401 拦截）
// 追加时间戳 query 绕过浏览器/代理对文件响应的缓存
export async function fetchCnasStandardBlob(id, action = 'download') {
  return request.get(`/api/v1/cnas-standards/${id}/${action}?_=${Date.now()}`, { responseType: 'blob' })
}

export async function previewStandard(id) {
  const blob = await fetchCnasStandardBlob(id, 'preview')
  previewBlob(blob)
}

export async function downloadStandard(id, filename) {
  const blob = await fetchCnasStandardBlob(id, 'download')
  downloadBlob(blob, filename)
}
