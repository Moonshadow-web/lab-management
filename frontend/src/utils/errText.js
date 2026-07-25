// 把 axios 异常转成可读的错误文本。
// 后端错误体通常是 { detail: '...' } 或校验错误 { detail: [...] }，
// 直接拼接会显示 [object Object]，这里做友好化处理。
export function errText(e) {
  if (!e) return '未知错误'
  if (e?.response?.data?.detail) {
    const d = e.response.data.detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) {
      return d.map((x) => (x?.msg || x?.loc ? `${x.loc?.join('.') || ''} ${x.msg}` : JSON.stringify(x))).join('; ')
    }
    return JSON.stringify(d)
  }
  if (e?.message) return e.message
  return String(e)
}
