// 把金子铮已有的理论作答补录进归档（source=import，第 1 次）
const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + lg.access_token, 'Content-Type': 'application/json' }

const ansStr = (a) => (Array.isArray(a) ? a.join('') : String(a == null ? '' : a))

// 题库（用于判分与试卷快照）
const banks = await fetch(H + '/api/v1/education/exam-banks?page_size=50', { headers: HDR }).then((r) => r.json())
const bankByPost = Object.fromEntries((banks.items || []).map((b) => [b.post, b]))

// 目标考核单
const list = await fetch(H + '/api/v1/education/pre-job-auths?page_size=100', { headers: HDR }).then((r) => r.json())
const rec = (list.items || []).find((x) => x.name === '金子铮' && (x.positions_json || []).length === 6)
if (!rec) { console.log('未找到金子铮的考核单'); process.exit(1) }
console.log('目标单 #' + rec.id, '岗位:', (rec.positions_json || []).join('、'))

const exam = rec.exam_json || {}
const positions = rec.positions_json || []
const papers = {}
const answers = {}
const detail = {}
let total = 0, full = 0
const pcts = []

for (const post of positions) {
  const T = (bankByPost[post] || {}).theory_json || {}
  papers[post] = T
  const a = (exam[post] || {}).theoryAnswers || {}
  answers[post] = a
  let s = 0
  ;(T.single || []).forEach((t, i) => { if (ansStr(a['s' + i]) === ansStr(t.answer).slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => {
    const g = ansStr(a['m' + i])
    if (g && g.split('').sort().join('') === ansStr(t.answer).split('').sort().join('')) s += 4
  })
  ;(T.judge || []).forEach((t, i) => { if (ansStr(a['j' + i]) === ansStr(t.answer)) s += 2 })
  const f = (T.single || []).length * 2 + (T.multi || []).length * 4 + (T.judge || []).length * 2
  const pct = f ? Math.round(s * 100 / f) : 0
  detail[post] = { score: s, full: f, pct }
  total += s; full += f; pcts.push(pct)
  console.log(`  ${post}: ${pct}/100（原始 ${s}/${f}）`)
}

const avg = pcts.length ? Math.round(pcts.reduce((x, y) => x + y, 0) / pcts.length) : 0
const payload = {
  pre_job_auth_id: rec.id,
  name: rec.name,
  posts_json: positions,
  papers_json: papers,
  answers_json: answers,
  detail_json: detail,
  score_raw: total,
  score_full: full,
  score_pct: avg,
  attempt_no: 1,
  source: 'import',
}
const r = await fetch(H + '/api/v1/education/prejob-theory-records', { method: 'POST', headers: HDR, body: JSON.stringify(payload) })
const j = await r.json()
console.log('归档写入:', r.status, r.status < 300 ? `id=${j.id} 百分制=${j.score_pct}` : JSON.stringify(j).slice(0, 120))

const chk = await fetch(H + '/api/v1/education/prejob-theory-records?page_size=10', { headers: HDR }).then((x) => x.json())
console.log('归档列表:', (chk.items || []).map((x) => `${x.name}(第${x.attempt_no}次, ${x.score_pct}/100, ${x.source})`).join(' | ') || '（空）')
