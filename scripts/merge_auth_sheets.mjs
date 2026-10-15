// 将授权表按「人」合并为一条：岗位/仪器/权限去重合并，保留最早生效、最晚到期、有效状态优先
import fs from 'fs'

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const login = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + login.access_token, 'Content-Type': 'application/json' }

const before = await fetch(H + '/api/v1/education/auth-sheets?page_size=500', { headers: HDR }).then((r) => r.json())
const all = before.items || []
console.log('合并前记录数:', all.length)

const split = (s) => String(s || '').split('、').map((x) => x.trim()).filter(Boolean)
const uniq = (a) => [...new Set(a.filter(Boolean))]
const normCode = (c) => (String(c || '').startsWith('MHZYY-JYK-') ? String(c) : 'MHZYY-JYK-' + String(c || ''))

// 解析 "名称（CODE）" 或 "名称(SM-xxxx)"
function parseInst(s) {
  const str = String(s || '').trim()
  if (!str) return null
  let m = str.match(/^(.+?)\s*[（(]([^）)]+)[）)]\s*$/)
  if (m) return { name: m[1].trim(), code: normCode(m[2].trim()) }
  if (/^MHZYY-JYK-SM-\d+/.test(str)) return { name: str, code: str }
  return { name: str, code: '' }
}
const cmpDate = (a, b) => (a && b ? (a < b ? a : b) : (a || b))

const groups = new Map()
for (const r of all) {
  const key = (r.name || '').trim() + '@' + (r.department || '').trim()
  if (!groups.has(key)) groups.set(key, [])
  groups.get(key).push(r)
}

let merged = 0
let removed = 0
for (const [key, rows] of groups) {
  if (rows.length <= 1) continue
  rows.sort((a, b) => (a.id || 0) - (b.id || 0))
  const keep = rows[0]
  const posts = []
  const insts = []
  const scopes = []
  const projs = []
  let validFrom = ''
  let validUntil = ''
  let authorizer = ''
  let qual = ''
  let status = ''
  for (const r of rows) {
    posts.push(...split(r.post), ...(r.posts_json || []))
    ;(r.instruments_json || []).forEach((i) => insts.push({ name: i.name || '', code: normCode(i.code) }))
    split(r.instrument).forEach((s) => { const p = parseInst(s); if (p) insts.push(p) })
    scopes.push(...split(r.auth_scope), ...(r.scopes_json || []))
    if (r.project) projs.push(r.project)
    validFrom = cmpDate(validFrom, r.valid_from)
    if (r.valid_until && (!validUntil || r.valid_until > validUntil)) validUntil = r.valid_until
    if (!authorizer && r.authorizer) authorizer = r.authorizer
    if (!qual && r.authorizer_qualification) qual = r.authorizer_qualification
    if (r.status === '有效') status = '有效'
    else if (!status && r.status) status = r.status
  }
  // 仪器去重（按 code，无 code 按 name）
  const seen = new Set()
  const instList = insts.filter((i) => {
    const k = i.code || i.name
    if (!k || seen.has(k)) return false
    seen.add(k)
    return true
  })
  const payload = {
    posts_json: uniq(posts),
    instruments_json: instList,
    scopes_json: uniq(scopes),
    post: uniq(posts).join('、').slice(0, 95),
    instrument: instList.map((i) => i.name).join('、').slice(0, 190),
    auth_scope: uniq(scopes).join('、').slice(0, 18),
    project: uniq(projs).join('、'),
    valid_from: validFrom || keep.valid_from,
    valid_until: validUntil || keep.valid_until,
    authorizer: authorizer || '金子铮',
    authorizer_qualification: qual || '免疫组组长/主治医师/本领域6年',
    status: status || '有效',
  }
  // 新后端支持多选字段则全量写；旧后端不支持则退化为只写字符串字段
  let upd = await fetch(H + '/api/v1/education/auth-sheets/' + keep.id, {
    method: 'PUT', headers: HDR, body: JSON.stringify(payload),
  }).then((r) => r.json())
  if (!upd || upd.id === undefined) {
    const { posts_json, instruments_json, scopes_json, ...plain } = payload
    upd = await fetch(H + '/api/v1/education/auth-sheets/' + keep.id, {
      method: 'PUT', headers: HDR, body: JSON.stringify(plain),
    }).then((r) => r.json())
    if (!upd || upd.id === undefined) { console.log('合并失败', key, JSON.stringify(upd).slice(0, 120)); continue }
    console.log('  (旧后端：仅写入字符串字段，多选数组待新版本上线后同步)')
  }
  for (const r of rows.slice(1)) {
    await fetch(H + '/api/v1/education/auth-sheets/' + r.id, { method: 'DELETE', headers: HDR })
    removed++
  }
  merged++
  console.log(`合并 ${rows[0].name}：${rows.length} 条 → 1 条 | 岗位 ${payload.posts_json.length} / 仪器 ${instList.length} / 权限 ${payload.scopes_json.join('、')}`)
}

const after = await fetch(H + '/api/v1/education/auth-sheets?page_size=500', { headers: HDR }).then((r) => r.json())
console.log('完成：合并', merged, '人，删除', removed, '条；合并后记录数:', (after.items || []).length)
for (const r of after.items || []) {
  console.log(' -', r.name, '| 岗位', (r.posts_json || []).length, '| 仪器', (r.instruments_json || []).length, '| 权限', (r.scopes_json || []).join('/'), '| 状态', r.status)
}
