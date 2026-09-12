// 拆分「西门子RapidPoint 1/2」这种合并映射为两条（各自独立二维码）
const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + lg.access_token, 'Content-Type': 'application/json' }

const ins = await fetch(H + '/api/v1/instruments?page_size=1000', { headers: HDR }).then((r) => r.json())
const findIns = (code) => (ins.items || []).find((x) => x.dept_no === code)

const maps = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
const bad = (maps.items || []).filter((x) => String(x.instrument_code).includes('/'))
console.log('含斜杠的合并行数:', bad.length)

for (const row of bad) {
  const codes = String(row.instrument_code).split('/').map((c) => c.trim()).filter(Boolean)
  console.log('拆分行:', row.post, '|', row.instrument_name, '|', row.instrument_code, '→', codes)
  let i = 0
  for (const c of codes) {
    const full = c.startsWith('MHZYY-JYK-') ? c : 'MHZYY-JYK-' + c
    const inst = findIns(full) || {}
    const r = await fetch(H + '/api/v1/education/post-instrument-maps', {
      method: 'POST', headers: HDR,
      body: JSON.stringify({
        post: row.post,
        instrument_name: inst.name || row.instrument_name,
        instrument_code: full,
        manager: row.manager || '',
        methods_json: row.methods_json || [],
        sort_no: (row.sort_no || 0) + i,
        remark: row.remark || '',
      }),
    })
    console.log('  新增', full, inst.name || '', '→', r.status)
    i++
  }
  const d = await fetch(H + '/api/v1/education/post-instrument-maps/' + row.id, { method: 'DELETE', headers: HDR })
  console.log('  删除原合并行 →', d.status)
}

const after = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
console.log('拆分后映射总数:', (after.items || []).length)
console.log('急诊岗仪器:', (after.items || []).filter((x) => x.post === '急诊岗').map((x) => x.instrument_name + '(' + x.instrument_code.replace('MHZYY-JYK-', '') + ')').join(' / '))
