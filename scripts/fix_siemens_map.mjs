// 修正西门子两台仪器的映射（SM-1015 / SM-1023 各自独立）
const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + lg.access_token, 'Content-Type': 'application/json' }

const ins = await fetch(H + '/api/v1/instruments?page_size=1000', { headers: HDR }).then((r) => r.json())
const findIns = (code) => (ins.items || []).find((x) => x.dept_no === code)
for (const c of ['MHZYY-JYK-SM-1015', 'MHZYY-JYK-SM-1023']) {
  const i = findIns(c)
  console.log(c, '→', i ? `${i.name} | 型号 ${i.model} | 编号 ${i.dept_no} | 管理 ${i.daily_manager}` : '未在仪器档案中找到')
}

const maps = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
const rows = maps.items || []
console.log('当前急诊岗:', rows.filter((x) => x.post === '急诊岗').map((x) => `${x.id}:${x.instrument_name}(${x.instrument_code})`).join(' | '))

// 删除错误编号行（MHZYY-JYK-1023）和名称仍为合并名的行
for (const r of rows) {
  const bad = r.instrument_code === 'MHZYY-JYK-1023' || (r.instrument_code === 'MHZYY-JYK-SM-1015' && /1\/2/.test(r.instrument_name || ''))
  if (bad) {
    const d = await fetch(H + '/api/v1/education/post-instrument-maps/' + r.id, { method: 'DELETE', headers: HDR })
    console.log('删除错误行', r.id, r.instrument_name, r.instrument_code, '→', d.status)
  }
}

// 正确新增两条
const cur = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
const exist = new Set((cur.items || []).map((x) => x.instrument_code))
let n = 0
for (const [c, fallback] of [['MHZYY-JYK-SM-1015', '西门子RapidPoint 1'], ['MHZYY-JYK-SM-1023', '西门子RapidPoint 2']]) {
  if (exist.has(c)) { console.log('已存在', c, '跳过'); continue }
  const i = findIns(c) || {}
  const r = await fetch(H + '/api/v1/education/post-instrument-maps', {
    method: 'POST', headers: HDR,
    body: JSON.stringify({
      post: '急诊岗',
      instrument_name: i.name || fallback,
      instrument_code: c,
      manager: i.daily_manager || '',
      methods_json: ['实操考核', '口头问答'],
      sort_no: 100 + n,
      remark: '',
    }),
  })
  console.log('新增', c, i.name || fallback, '→', r.status)
  n++
}

const after = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
console.log('最终映射总数:', (after.items || []).length)
console.log('急诊岗仪器:', (after.items || []).filter((x) => x.post === '急诊岗').map((x) => `${x.instrument_name}(${x.instrument_code.replace('MHZYY-JYK-', '')})`).join(' / '))
