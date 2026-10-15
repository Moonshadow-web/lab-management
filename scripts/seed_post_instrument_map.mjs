// 将 gl070Meta 内置映射导入 post_instrument_map（幂等：已存在的 instrument_code 跳过）
import fs from 'fs'
import path from 'path'

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const metaPath = path.resolve('frontend/src/views/training/staff/gl070Meta.js')
const src = fs.readFileSync(metaPath, 'utf8').replace(/export /g, '')
const { GL070_POSITIONS } = new Function(src + '\nreturn { GL070_POSITIONS };')()

const login = await fetch(H + '/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + login.access_token, 'Content-Type': 'application/json' }

const cur = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
const exist = new Set((cur.items || []).map((x) => x.instrument_code))
let n = 0
for (const p of GL070_POSITIONS) {
  let i = 0
  for (const inst of p.instruments) {
    if (exist.has(inst.code)) { i++; continue }
    const r = await fetch(H + '/api/v1/education/post-instrument-maps', {
      method: 'POST', headers: HDR,
      body: JSON.stringify({
        post: p.name, instrument_name: inst.name, instrument_code: inst.code,
        manager: inst.manager || '', methods_json: p.methods || [], sort_no: i++,
      }),
    })
    if (r.ok) n++
  }
}
const after = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
console.log('新导入', n, '条；当前共', (after.items || []).length, '条')
const byPost = {}
;(after.items || []).forEach((x) => { byPost[x.post] = (byPost[x.post] || 0) + 1 })
console.log(byPost)
