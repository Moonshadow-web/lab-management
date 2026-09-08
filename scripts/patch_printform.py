# -*- coding: utf-8 -*-
"""一次性补丁：重写 PreJobAuth.vue 的 printForm 为按岗位叙事 + 试卷附页"""
import io

p = r'frontend/src/views/training/staff/PreJobAuth.vue'
src = io.open(p, encoding='utf-8').read()
start = src.index('function printForm(row) {')
end = src.index('</script>', start)
new_fn = '''async function printForm(row) {
  let bankMap = {}
  try { const res = await listExamBank({ page_size: 50 }); bankMap = Object.fromEntries((res.items || []).map((b) => [b.post, b])) } catch (e) {}
  const posts = row.positions_json || []
  const projOf = (code) => { const r = (row.items_json || []).find((x) => x.code === code); return r ? (r.items || '') : '' }
  const perPost = posts.map((post) => {
    const bank = bankMap[post] || {}
    const insts = (row.instruments_json || []).filter((i) => i.position === post)
    const instRows = insts.map((i) => `<tr><td>${esc(i.name)}</td><td style="text-align:center;">${esc(i.code.replace('MHZYY-JYK-', ''))}</td><td>${esc(projOf(i.code))}</td></tr>`).join('')
    const d = (row.exam_json || {})[post] || {}
    const qaQ = (bank.qa_json || []).map((x, i) => `<div style="margin-bottom:4px;">${i + 1}. ${esc(x.q)}</div>`).join('')
    const prRows = (bank.practical_json || []).map((x, i) => `<tr><td>${i + 1}. ${esc(x.point)}</td><td style="width:70px;text-align:center;">${x.score}</td><td style="width:70px;"></td></tr>`).join('')
    const th = []
    ;((bank.theory_json || {}).single || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;">${i + 1}. ${esc(t.q)}<br>${t.options.map((o) => esc(o)).join('　　')}<br>答：＿＿＿＿＿</div>`))
    ;((bank.theory_json || {}).multi || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;">${i + 1}. ${esc(t.q)}<br>${t.options.map((o) => esc(o)).join('　　')}<br>答：＿＿＿＿＿</div>`))
    ;((bank.theory_json || {}).judge || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;">${i + 1}. ${esc(t.q)}　答：＿＿＿</div>`))
    return { post, bank, instRows, d, qaQ, prRows, th }
  })

  const main = perPost.map((pp) => `
    <h3 style="margin:12px 0 4px;">岗位：${esc(pp.post)}</h3>
    <table style="border:1.5px solid #333;font-size:12px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;">培训时间</td><td style="text-align:center;">${esc(pp.d.trainTime || '')}</td><td style="width:70px;text-align:center;background:#f7f7f7;">培训人</td><td style="text-align:center;">${esc(pp.d.trainPerson || '')}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">培训内容</td><td colspan="3" style="padding:4px 8px;">${esc(pp.d.trainContent || '')}</td></tr>
    </table>
    <table style="border-collapse:collapse;width:100%;font-size:12px;margin-top:4px;">
      <tr><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">仪器</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">编号</th><th style="border:1px solid #333;background:#f1f5f9;padding:4px;">关联项目</th></tr>
      ${pp.instRows}
    </table>
    <table style="border-collapse:collapse;width:100%;font-size:12px;margin-top:4px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">考核方式</td><td style="border:1px solid #333;padding:4px;">${esc(pp.methods.join('、'))}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">口头问答</td><td style="border:1px solid #333;padding:4px;">${esc(pp.d.qaResult || '')}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">实操得分</td><td style="border:1px solid #333;padding:4px;">${pp.bank.practical_json && pp.bank.practical_json.length ? practicalScoreOf(row, pp) + ' / ' + pp.practicalTotal : ''}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">理论得分</td><td style="border:1px solid #333;padding:4px;">${pp.bank.theory_json ? theoryScoreOf(row, pp) + ' / ' + pp.theoryFull : ''}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;border:1px solid #333;padding:4px;">掌握程度</td><td style="border:1px solid #333;padding:4px;">${esc(pp.d.mastery || '')}</td></tr>
    </table>`).join('')

  const appendix = perPost.map((pp) => `
    <h3 style="margin:14px 0 4px;">附：${esc(pp.post)} 考核题</h3>
    ${pp.qaQ ? '<h4>一、口头问答</h4>' + pp.qaQ : ''}
    ${pp.prRows ? '<h4>二、实操要点与打分（满分 ' + pp.practicalTotal + '）</h4><table style="border-collapse:collapse;width:100%;font-size:12px;"><tr><th style="border:1px solid #333;padding:4px;">要点</th><th style="border:1px solid #333;padding:4px;width:70px;">分值</th><th style="border:1px solid #333;padding:4px;width:70px;">得分</th></tr>' + pp.prRows + '</table>' : ''}
    ${pp.th.length ? '<h4>三、理论考核</h4>' + pp.th.join('') : ''}
  `).join('')

  const html = `
  <h2 style="text-align:center;font-size:20px;letter-spacing:3px;margin:0 0 6px;">岗前培训考核及授权表</h2>
  <div style="text-align:center;color:#555;font-size:12px;margin-bottom:10px;">表格编号：BG-SM-PX-002　　检验科生化免疫组</div>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td style="width:90px;text-align:center;background:#f7f7f7;">申请人</td><td style="width:180px;text-align:center;height:30px;">${esc(row.name)}</td><td style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td><td style="text-align:center;">${esc(row.apply_date)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3" style="padding:6px 10px;">${esc(posts.join('、'))}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">授权权限</td><td colspan="3" style="padding:6px 10px;">${esc((row.permissions_json || []).join('、'))}</td></tr>
  </table>
  ${main}
  <h3>四、考核意见</h3>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td style="width:120px;text-align:center;background:#f7f7f7;">考核意见（授权）</td><td style="padding:6px 10px;">${esc(row.conclusion)}${row.auth_date ? '　授权日期：' + esc(row.auth_date) : ''}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">备注</td><td style="padding:6px 10px;min-height:36px;">${esc(row.remark)}</td></tr>
  </table>
  <div style="margin-top:26px;font-size:13px;text-align:right;">
    员工签字：　　　　　　组长签字：　　　　　　日期：　　　　
  </div>
  ${appendix}`
  printHtml('岗前培训考核及授权表', html)
}
function practicalScoreOf(row, pp) {
  const d = (row.exam_json || {})[pp.post] || {}
  return (pp.bank.practical_json || []).reduce((s, p, i) => s + (Number(d.practicalScores?.[i]) || 0), 0)
}
function theoryScoreOf(row, pp) {
  let s = 0
  const d = (row.exam_json || {})[pp.post] || {}
  const T = pp.bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (d.theoryAnswers?.['s' + i] === t.answer.slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => { const g = (d.theoryAnswers?.['m' + i] || []).slice().sort().join(''); if (g && g === t.answer.split('').sort().join('')) s += 4 })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === t.answer) s += 2 })
  return s
}
</script>'''
src = src[:start] + new_fn + src[end:]
io.open(p, 'w', encoding='utf-8').write(src)
print('printForm 重写完成')
