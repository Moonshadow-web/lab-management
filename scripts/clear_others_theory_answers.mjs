// 清空除金子铮外其他考核单里的理论作答（他们要用二维码重新答题）
// 保留：姓名/岗位/仪器/权限/培训信息/掌握程度等，只清 theoryAnswers
const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const KEEP_NAMES = new Set(['金子铮']) // 保留者（已归档）

const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + lg.access_token, 'Content-Type': 'application/json' }

const list = await fetch(H + '/api/v1/education/pre-job-auths?page_size=200', { headers: HDR }).then((r) => r.json())
const rows = list.items || []
console.log('考核单总数:', rows.length)

const hit = []
for (const r of rows) {
  if (KEEP_NAMES.has(r.name)) continue
  const exam = r.exam_json || {}
  let changed = 0
  for (const post of Object.keys(exam)) {
    const d = exam[post]
    if (d && d.theoryAnswers && Object.keys(d.theoryAnswers).length) {
      d.theoryAnswers = {}
      changed++
    }
  }
  if (changed) hit.push({ row: r, changed, exam })
}

console.log('需清理的记录数:', hit.length)
let okCount = 0
for (const h of hit) {
  const r = h.row
  const payload = {
    name: r.name,
    apply_date: r.apply_date,
    positions_json: r.positions_json,
    instruments_json: r.instruments_json,
    permissions_json: r.permissions_json,
    items_json: r.items_json,
    exam_json: h.exam,
    conclusion: r.conclusion,
    auth_date: r.auth_date,
    remark: r.remark,
    status: r.status,
    batch_id: r.batch_id,
  }
  const res = await fetch(H + '/api/v1/education/pre-job-auths/' + r.id, { method: 'PUT', headers: HDR, body: JSON.stringify(payload) })
  const j = await res.json()
  const ok = res.status < 300 && String(j.name || '') === String(r.name) && (j.positions_json || []).length === (r.positions_json || []).length
  if (ok) okCount++
  console.log(`  #${r.id} ${r.name} 清理 ${h.changed} 个岗位 → ${res.status}${ok ? '' : ' ⚠ 字段校验异常 ' + JSON.stringify(j).slice(0, 80)}`)
}

console.log(`清理完成：成功 ${okCount}/${hit.length}`)

// 复核：还有哪些记录残留作答
const after = await fetch(H + '/api/v1/education/pre-job-auths?page_size=200', { headers: HDR }).then((r) => r.json())
const rest = []
for (const r of after.items || []) {
  const exam = r.exam_json || {}
  const posts = Object.keys(exam).filter((p) => exam[p] && exam[p].theoryAnswers && Object.keys(exam[p].theoryAnswers).length)
  if (posts.length) rest.push(`${r.name}#${r.id}(${posts.length}岗)`)
}
console.log('复核：仍有作答的记录 →', rest.join(' | ') || '（无）')
