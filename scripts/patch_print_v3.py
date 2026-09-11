# -*- coding: utf-8 -*-
"""岗位页版式重排 + 项目取数加固 + 打印考核内容"""
import io

p = 'frontend/src/views/training/staff/PreJobAuth.vue'
s = io.open(p, encoding='utf-8').read()

# ---------- 1) warmProjects 加固：先确保仪器库已加载；找不到仪器不写缓存 ----------
old_warm = """async function warmProjects(rows) {
  const codes = []
  ;(rows || []).forEach((r) => (r.instruments_json || []).forEach((i) => { if (i.code) codes.push(i.code) }))
  const todo = [...new Set(codes)].filter((c) => !projCache.has(c))
  const one = async (c) => {
    const db = instByCode.value[c]
    let pj = ''
    if (db) {
      try {
        const items = await getInstrumentTestItems(db.id)
        pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
      } catch (e) { pj = '' }
    }
    projCache.set(c, pj)
  }"""
new_warm = """async function warmProjects(rows) {
  // 仪器库未就绪时先加载（否则按编号查不到仪器 → 项目永远为空）
  if (!Object.keys(instByCode.value).length) {
    try {
      const r = await listInstruments({ page: 1, page_size: 1000 })
      instByCode.value = Object.fromEntries((r.items || []).map((x) => [x.dept_no, x]))
    } catch (e) { /* ignore */ }
  }
  const codes = []
  ;(rows || []).forEach((r) => (r.instruments_json || []).forEach((i) => { if (i.code) codes.push(i.code) }))
  const todo = [...new Set(codes)].filter((c) => !projCache.has(c))
  const one = async (c) => {
    const db = instByCode.value[c]
    if (!db) return   // 查不到仪器不写缓存，留给下次重试
    let pj = ''
    try {
      const items = await getInstrumentTestItems(db.id)
      pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
    } catch (e) { pj = '' }
    projCache.set(c, pj)
  }"""
assert old_warm in s
s = s.replace(old_warm, new_warm, 1)

# ---------- 2) printForm：岗位页改为 仪器一个框 + 项目一个框（无编号），并打印考核内容 ----------
start = s.index('async function printForm(row) {')
end = s.index('// 某岗位理论得分（按 job 快照判分）')
new_print = '''async function printForm(row) {
  const bankMap = banks.value || {}
  if (!Object.keys(bankMap).length) loadBanks()
  const missing = (row.instruments_json || []).some((i) => i.code && !projCache.has(i.code))
  await warmProjects([row])

  const posts = row.positions_json || []
  const allInsts = row.instruments_json || []
  const instsOfPost = (post) => allInsts.filter((i) => (i.position || codeToPost.value[i.code] || '') === post)
  const projOf = (code) => {
    const r = (row.items_json || []).find((x) => x.code === code)
    const fromRow = r ? (r.items || '') : ''
    return fromRow || projCache.get(code) || ''
  }
  const projOfPost = (post) => [...new Set(instsOfPost(post).map((i) => projOf(i.code)).filter(Boolean))].join('；')
  const boxRow = (label, value, fs) => `<tr><td style="width:80px;text-align:center;background:#f7f7f7;border:1px solid #333;padding:5px;">${label}</td><td style="border:1px solid #333;padding:5px;font-size:${fs || 12}px;">${value || ''}</td></tr>`
  const pageBreak = '<div style="page-break-after: always;"></div>'

  const instNamesAll = [...new Set(allInsts.map((i) => i.name).filter(Boolean))].join('、')
  const allProjText = [...new Set(allInsts.map((i) => projOf(i.code)).filter(Boolean))].join('；')

  // ===== 第一页 =====
  const page1 = `
    <h2 style="text-align:center;letter-spacing:3px;margin:0 0 4px;">岗前培训考核及授权表</h2>
    <div class="meta" style="text-align:center;">表格编号：BG-SM-PX-002　　检验科生化免疫组</div>
    <table style="border:1.5px solid #333;font-size:13px;">
      <tr><td style="width:90px;text-align:center;background:#f7f7f7;">申请人</td><td style="width:180px;text-align:center;">${esc(row.name)}</td><td style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td><td style="text-align:center;">${esc(row.apply_date)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3" style="padding:4px 8px;">${esc(posts.join('、'))}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">仪器</td><td colspan="3" style="padding:4px 8px;">${esc(instNamesAll)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">项目</td><td colspan="3" style="padding:4px 8px;font-size:12px;">${esc(allProjText)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">授权权限</td><td colspan="3" style="padding:4px 8px;">${esc((row.permissions_json || []).join('、'))}</td></tr>
    </table>
    <h3>考核意见</h3>
    <table style="border:1.5px solid #333;font-size:13px;">
      <tr><td style="width:130px;text-align:center;background:#f7f7f7;">考核意见（授权）</td><td style="padding:6px 10px;">${esc(row.conclusion)}${row.auth_date ? '　授权日期：' + esc(row.auth_date) : ''}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">备注</td><td style="padding:6px 10px;min-height:36px;">${esc(row.remark)}</td></tr>
    </table>
    <div style="margin-top:34px;text-align:center;font-size:14px;letter-spacing:1px;">
      员工签字：　　　　　　　　组长签字：　　　　　　　　日期：
    </div>
    ${pageBreak}`

  // ===== 每岗位一页 =====
  const pages = posts.map((post) => {
    const bank = bankMap[post] || {}
    const methods = bank.methods_json && bank.methods_json.length ? bank.methods_json : ['实操考核']
    const d = (row.exam_json || {})[post] || {}
    const pTotal = (bank.practical_json || []).reduce((x, y) => x + (y.score || 0), 0)
    const tFull = ((bank.theory_json && (bank.theory_json.single || []).length) || 0) * 2
      + ((bank.theory_json && (bank.theory_json.multi || []).length) || 0) * 4
      + ((bank.theory_json && (bank.theory_json.judge || []).length) || 0) * 2
    const pGot = (bank.practical_json || []).reduce((x, y, i) => x + (Number((d.practicalScores || {})[i]) || 0), 0)
    const pPct = pTotal ? Math.round(pGot * 100 / pTotal) : 0
    const tPct = tFull ? Math.round(theoryScoreOf2(row, post, bank) * 100 / tFull) : 0

    // 口头问答：问题清单
    const qaList = (bank.qa_json || []).map((q, i) => `<div>${i + 1}. ${esc(q.q)}</div>`).join('')
    // 实操：要点 + 分值 + 得分
    const prRows = (bank.practical_json || []).map((x, i) => `<tr><td style="border:1px solid #333;padding:4px;">${i + 1}. ${esc(x.point)}</td><td style="border:1px solid #333;padding:4px;width:60px;text-align:center;">${x.score}</td><td style="border:1px solid #333;padding:4px;width:60px;text-align:center;">${(d.practicalScores || {})[i] || ''}</td></tr>`).join('')
    // 理论：题目 + 选项（不含答案）
    const th = []
    ;((bank.theory_json || {}).single || []).forEach((t, i) => th.push(`<div style="margin-bottom:3px;">${i + 1}. ${esc(t.q)}<br>${(t.options || []).map((o) => esc(o)).join('　　')}</div>`))
    ;((bank.theory_json || {}).multi || []).forEach((t, i) => th.push(`<div style="margin-bottom:3px;">${i + 1}. ${esc(t.q)}<br>${(t.options || []).map((o) => esc(o)).join('　　')}</div>`))
    ;((bank.theory_json || {}).judge || []).forEach((t, i) => th.push(`<div style="margin-bottom:3px;">${i + 1}. ${esc(t.q)}　（对 / 错）</div>`))

    return `
    <h3 style="margin:0 0 6px;">岗位：${esc(post)}</h3>
    <table style="border:1.5px solid #333;font-size:12px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;">培训时间</td><td style="text-align:center;">${esc(d.trainTime || '')}</td><td style="width:70px;text-align:center;background:#f7f7f7;">培训人</td><td style="text-align:center;">${esc(d.trainPerson || '')}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">培训内容</td><td colspan="3" style="padding:4px 8px;">${esc(d.trainContent || '')}</td></tr>
    </table>
    <table style="border-collapse:collapse;width:100%;font-size:12px;">
      ${boxRow('仪器', esc(instsOfPost(post).map((i) => i.name).join('、')))}
      ${boxRow('项目', esc(projOfPost(post)), 11)}
    </table>
    ${methods.includes('口头问答') ? `<h4 style="margin:10px 0 4px;">一、口头问答（考核结果：${esc(d.qaResult || '')}）</h4>${qaList}` : ''}
    ${prRows ? `<h4 style="margin:10px 0 4px;">二、实操考核（${pPct} / 100 分，合格线 80）</h4>
      <table style="border-collapse:collapse;width:100%;font-size:12px;">
        <tr><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">考核要点</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;width:60px;">分值</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;width:60px;">得分</th></tr>
        ${prRows}</table>` : ''}
    ${th.length ? `<h4 style="margin:10px 0 4px;">三、理论考核（${tPct} / 100 分，合格线 60）</h4>${th.join('')}` : ''}
    <table style="border-collapse:collapse;width:100%;font-size:12px;margin-top:8px;">
      ${boxRow('考核方式', esc(methods.join('、')))}
      ${boxRow('掌握程度', esc(d.mastery || ''))}
    </table>
    ${pageBreak}`
  }).join('')

  printHtml('岗前培训考核及授权表', page1 + pages)
}
'''
s = s[:start] + new_print + s[end:]
io.open(p, 'w', encoding='utf-8').write(s)
print('printForm 版式与内容重排完成')
