# -*- coding: utf-8 -*-
"""按要求重排打印 + 项目缓存 + 去掉原始分显示"""
import io, re

# ============ 1) PreJobAuth.vue ============
p = 'frontend/src/views/training/staff/PreJobAuth.vue'
s = io.open(p, encoding='utf-8').read()

# 1.1 关联项目加缓存（首次加载后记住）
if 'projCache' not in s:
    s = s.replace("const projLoading = ref(false)",
"""// 关联项目缓存：同一台仪器只请求一次（避免每点一次就刷一次）
const projCache = new Map()
const projLoading = ref(false)""", 1)
    s = s.replace("""  for (const c of instrumentCodes.value) {
    const inst = GL070_META_ALL.value.find((i) => i.code === c) || {}
    let projects = ''
    const dbInst = instByCode.value[c]
    if (dbInst) {
      try {
        const items = await getInstrumentTestItems(dbInst.id)
        projects = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
      } catch (e) { projects = '' }
    }
    rows.push({ code: c, name: inst.name || '', projects })
  }""",
"""  for (const c of instrumentCodes.value) {
    const inst = GL070_META_ALL.value.find((i) => i.code === c) || {}
    let projects = projCache.get(c)
    if (projects === undefined) {
      projects = ''
      const dbInst = instByCode.value[c]
      if (dbInst) {
        try {
          const items = await getInstrumentTestItems(dbInst.id)
          projects = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
        } catch (e) { projects = '' }
      }
      projCache.set(c, projects)
    }
    rows.push({ code: c, name: inst.name || '', projects })
  }""", 1)

# 1.2 去掉「原始 x/y」显示，仅显示百分制 + 合格线
s = s.replace('<div>实操得分：<b>{{ practicalPct(pc) }}</b> / 100 分（原始 {{ practicalScore(pc) }}/{{ pc.practicalTotal }}，合格线 80）</div>',
              '<div>实操得分：<b>{{ practicalPct(pc) }}</b> / 100 分（合格线 80）</div>', 1)
s = s.replace('<div>理论得分：<b>{{ theoryPct(pc) }}</b> / 100 分（原始 {{ theoryScore(pc) }}/{{ theoryFull(pc) }}，合格线 60）</div>',
              '<div>理论得分：<b>{{ theoryPct(pc) }}</b> / 100 分（合格线 60）</div>', 1)

# 1.3 重排 printForm
start = s.index('// 同步打印：')
end = s.index('function practicalPctOf(row, pp)')
new_print = '''// 同步打印：必须用已缓存的题库（await 之后再 window.open 会被浏览器当弹窗拦截）
function printForm(row) {
  const bankMap = banks.value || {}
  if (!Object.keys(bankMap).length) loadBanks()

  const posts = row.positions_json || []
  const allInsts = row.instruments_json || []
  const instsOfPost = (post) => allInsts.filter((i) => (i.position || '') === post)
  const projOf = (code) => {
    const r = (row.items_json || []).find((x) => x.code === code)
    return r ? (r.items || '') : ''
  }
  const instTable = (list) => `<table style="border-collapse:collapse;width:100%;font-size:12px;">
      <tr><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">仪器</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">编号</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">关联项目</th></tr>
      ${list.map((i) => `<tr><td>${esc(i.name)}</td><td style="text-align:center;">${esc(String(i.code || '').replace('MHZYY-JYK-', ''))}</td><td style="font-size:11px;">${esc(projOf(i.code))}</td></tr>`).join('')}
    </table>`
  const allProjText = [...new Set(allInsts.map((i) => projOf(i.code)).filter(Boolean))].join('；')
  const instNamesAll = [...new Set(allInsts.map((i) => i.name).filter(Boolean))].join('、')

  // ===== 第一页：基本信息（含仪器、项目）+ 考核意见 + 签字（居中）=====
  const page1 = `
    <h2 style="text-align:center;letter-spacing:3px;margin:0 0 4px;">岗前培训考核及授权表</h2>
    <div class="meta" style="text-align:center;">表格编号：BG-SM-PX-002　　检验科生化免疫组</div>
    <table style="border:1.5px solid #333;font-size:13px;">
      <tr><td style="width:90px;text-align:center;background:#f7f7f7;">申请人</td><td style="width:180px;text-align:center;">${esc(row.name)}</td><td style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td><td style="text-align:center;">${esc(row.apply_date)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3" style="padding:4px 8px;">${esc(posts.join('、'))}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;height:40px;">仪器</td><td colspan="3" style="padding:4px 8px;">${esc(instNamesAll)}</td></tr>
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
    <div style="page-break-after: always;"></div>`

  // ===== 之后：每个岗位一页 =====
  const pages = posts.map((post) => {
    const bank = bankMap[post] || {}
    const methods = bank.methods_json && bank.methods_json.length ? bank.methods_json : ['实操考核']
    const d = (row.exam_json || {})[post] || {}
    const list = instsOfPost(post)
    const pTotal = (bank.practical_json || []).reduce((x, y) => x + (y.score || 0), 0)
    const tFull = ((bank.theory_json && (bank.theory_json.single || []).length) || 0) * 2
      + ((bank.theory_json && (bank.theory_json.multi || []).length) || 0) * 4
      + ((bank.theory_json && (bank.theory_json.judge || []).length) || 0) * 2
    const pGot = (bank.practical_json || []).reduce((x, y, i) => x + (Number((d.practicalScores || {})[i]) || 0), 0)
    const pPct = pTotal ? Math.round(pGot * 100 / pTotal) : 0
    const tPct = tFull ? Math.round(theoryScoreOf2(row, post, bank) * 100 / tFull) : 0
    return `
    <h3 style="margin:0 0 6px;">岗位：${esc(post)}</h3>
    <table style="border:1.5px solid #333;font-size:12px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;">培训时间</td><td style="text-align:center;">${esc(d.trainTime || '')}</td><td style="width:70px;text-align:center;background:#f7f7f7;">培训人</td><td style="text-align:center;">${esc(d.trainPerson || '')}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">培训内容</td><td colspan="3" style="padding:4px 8px;">${esc(d.trainContent || '')}</td></tr>
    </table>
    ${instTable(list)}
    <table style="border-collapse:collapse;width:100%;font-size:12px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">考核方式</td><td style="border:1px solid #333;padding:4px;">${esc(methods.join('、'))}</td></tr>
      ${methods.includes('口头问答') ? `<tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">口头问答</td><td style="border:1px solid #333;padding:4px;">${esc(d.qaResult || '')}</td></tr>` : ''}
      ${(bank.practical_json || []).length ? `<tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">实操得分</td><td style="border:1px solid #333;padding:4px;">${pPct} / 100 分（合格线 80）</td></tr>` : ''}
      ${tFull ? `<tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">理论得分</td><td style="border:1px solid #333;padding:4px;">${tPct} / 100 分（合格线 60）</td></tr>` : ''}
      <tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">掌握程度</td><td style="border:1px solid #333;padding:4px;">${esc(d.mastery || '')}</td></tr>
    </table>
    <div style="page-break-after: always;"></div>`
  }).join('')

  printHtml('岗前培训考核及授权表', page1 + pages)
}
// 某岗位理论得分（按 job 快照判分）
function theoryScoreOf2(row, post, bank) {
  let s = 0
  const d = (row.exam_json || {})[post] || {}
  const T = bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (ansStr(d.theoryAnswers?.['s' + i]) === ansStr(t.answer).slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => { const g = (d.theoryAnswers?.['m' + i] || []).slice().sort().join(''); if (g && g === ansStr(t.answer).split('').sort().join('')) s += 4 })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === ansStr(t.answer)) s += 2 })
  return s
}
'''
s = s[:start] + new_print + s[end:]
io.open(p, 'w', encoding='utf-8').write(s)
print('PreJobAuth 打印重排 + 缓存 + 去原始分 完成')

# ============ 2) AuthSheet.vue：项目缓存 ============
p2 = 'frontend/src/views/training/staff/AuthSheet.vue'
s2 = io.open(p2, encoding='utf-8').read()
if 'projCache' not in s2:
    s2 = s2.replace("const projText = ref('')",
"""const projCache = new Map()
const projText = ref('')""", 1)
    s2 = s2.replace("""  for (const c of instCodes.value) {
    const db = instByCode.value[c]
    if (db) {
      try {
        const items = await getInstrumentTestItems(db.id)
        names.push(...(items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()))
      } catch (e) {}
    }
  }""",
"""  for (const c of instCodes.value) {
    let pj = projCache.get(c)
    if (pj === undefined) {
      pj = []
      const db = instByCode.value[c]
      if (db) {
        try {
          const items = await getInstrumentTestItems(db.id)
          pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim())
        } catch (e) { pj = [] }
      }
      projCache.set(c, pj)
    }
    names.push(...pj)
  }""", 1)
    s2 = s2.replace("""  for (const i of current.value.instruments_json || []) {
    const db = instByCode.value[i.code]
    if (db) {
      try {
        const items = await getInstrumentTestItems(db.id)
        names.push(...(items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()))
      } catch (e) {}
    }
  }""",
"""  for (const i of current.value.instruments_json || []) {
    let pj = projCache.get(i.code)
    if (pj === undefined) {
      pj = []
      const db = instByCode.value[i.code]
      if (db) {
        try {
          const items = await getInstrumentTestItems(db.id)
          pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim())
        } catch (e) { pj = [] }
      }
      projCache.set(i.code, pj)
    }
    names.push(...pj)
  }""", 1)
    io.open(p2, 'w', encoding='utf-8').write(s2)
    print('AuthSheet 项目缓存 完成')
