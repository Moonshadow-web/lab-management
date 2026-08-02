// 报告导出工具：构造可打印/下载/预览的 HTML（兼容 Word 打开）。
export function escapeHtml(s) {
  return (s == null ? '' : String(s))
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const PAGE_STYLE = `
  <style>
    body{font-family:"Microsoft YaHei","SimSun",sans-serif;padding:24px;color:#000;font-size:13px;line-height:1.5}
    h2{text-align:center;font-size:18px;margin:0 0 6px}
    .sub{text-align:center;color:#555;margin-bottom:14px;font-size:12px}
    table{border-collapse:collapse;width:100%;font-size:12px}
    th,td{border:1px solid #333;padding:5px 7px;vertical-align:top;text-align:left}
    th{background:#f2f2f2;text-align:center}
    .meta{margin:10px 0}
    .pre{white-space:pre-wrap;word-break:break-word}
    .ok{color:#167c2b} .bad{color:#c0392b} .warn{color:#b9770e} .na{color:#888}
  </style>`

const NA_MARKS = ['', '（无）', '(无)']
function isNoRequirementRow(r) {
  const contentEmpty = NA_MARKS.includes((r.content || '').trim())
  const appEmpty = NA_MARKS.includes((r.application_requirement || '').trim()) && NA_MARKS.includes((r.check_point || '').trim())
  return contentEmpty && appEmpty
}

function clauseBody(r) {
  let body = escapeHtml(r.content || '（无）')
  const appReq = r.application_requirement || r.check_point
  if (appReq) {
    body += `<div style="margin-top:6px;color:#8b4513"><b>【应用要求】</b>${escapeHtml(appReq)}</div>`
  }
  return body
}

/**
 * 自查（条款内审）报告 HTML。
 * rows: [{clause_no,title,content,check_point,check_content,result,finding,action}]
 */
export function buildSelfInspectionHtml({ campaignTitle, year, assignee, rows, generatedAt }) {
  const trs = (rows || []).map((r, i) => {
    const na = isNoRequirementRow(r)
    const res = (r.result || '').trim() || (na ? '不适用' : '')
    const resCls = res === '符合' ? 'ok' : res === '不符合' ? 'bad'
      : res === '观察项' ? 'warn' : res === '不适用' ? 'na' : ''
    return `<tr>
      <td style="text-align:center">${i + 1}</td>
      <td><b>${escapeHtml(r.clause_no)}</b>${r.title ? ' ' + escapeHtml(r.title) : ''}</td>
      <td class="pre">${clauseBody(r)}</td>
      <td class="pre">${escapeHtml(r.check_content || (na ? '—' : '（未填写）'))}</td>
      <td class="${resCls}" style="text-align:center">${escapeHtml(res || '—')}</td>
      <td class="pre">${escapeHtml(r.finding || (na ? '—' : ''))}</td>
      <td class="pre">${escapeHtml(r.action || (na ? '—' : ''))}</td>
    </tr>`
  }).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${PAGE_STYLE}</head><body>
    <h2>自查（条款内审）报告</h2>
    <div class="sub">CNAS-AL02-07 附表3 自查表</div>
    <div class="meta">活动：${escapeHtml(campaignTitle || '')}（${escapeHtml(year || '')}）　被查人/责任人：${escapeHtml(assignee || '')}　生成时间：${escapeHtml(generatedAt || '')}</div>
    <table>
      <thead><tr>
        <th style="width:34px">序号</th><th style="width:150px">条款</th><th>条款内容 / 核查要点</th>
        <th>核查内容</th><th style="width:64px">结果</th><th>问题描述</th><th>采取措施</th>
      </tr></thead>
      <tbody>${trs || '<tr><td colspan="7" style="text-align:center">暂无数据</td></tr>'}</tbody>
    </table>
  </body></html>`
}

/**
 * 文件评审汇总（A-027）报告 HTML。
 * summaryData: [{reviewer,status,review_members,approver,problems,record_date,review_files:[{title,doc_number,version,comment,conclusion}],assign_files:[{title,status,new_version}]}]
 */
export function buildReviewSummaryHtml({ campaignTitle, year, rows }) {
  const header = `<table style="margin-bottom:8px">
    <tr><td style="width:20%;font-weight:bold">表格编号</td><td style="width:30%">KS-BG-A-027</td><td style="width:20%;font-weight:bold">科室</td><td style="width:30%">民航总医院检验科</td></tr>
    <tr><td style="font-weight:bold">生效日期</td><td>2025.04.01</td><td style="font-weight:bold">评审活动</td><td>${escapeHtml(campaignTitle || '')}（${escapeHtml(year || '')}）</td></tr>
  </table>`

  const blocks = (rows || []).map((r) => {
    const fileRows = (r.review_files || []).map(f =>
      `<tr>
        <td>${escapeHtml(f.title || '')}</td>
        <td style="width:140px">${escapeHtml(f.doc_number || '')}</td>
        <td style="width:60px;text-align:center">${escapeHtml(f.version || '')}</td>
        <td style="width:200px" class="pre">${escapeHtml(f.comment || '')}</td>
        <td style="width:80px;text-align:center">${escapeHtml(f.conclusion || '')}</td>
      </tr>`
    ).join('') || '<tr><td colspan="5" style="text-align:center">无</td></tr>'

    return `<div style="margin-bottom:18px">
      <table style="margin-bottom:8px">
        <tr>
          <td style="width:12%;font-weight:bold">记录人</td><td style="width:18%">${escapeHtml(r.reviewer || '')}</td>
          <td style="width:12%;font-weight:bold">状态</td><td style="width:18%">${escapeHtml(r.status || '')}</td>
          <td style="width:12%;font-weight:bold">审批人</td><td style="width:28%">${escapeHtml(r.approver || '金子铮')}</td>
        </tr>
        <tr>
          <td style="font-weight:bold">记录日期</td><td>${escapeHtml(r.record_date || '')}</td>
          <td colspan="2" style="font-weight:bold">评审组成员</td><td colspan="2">${escapeHtml(r.review_members || '—')}</td>
        </tr>
        <tr><td style="font-weight:bold">主要存在问题</td><td colspan="5" class="pre">${escapeHtml(r.problems || '无')}</td></tr>
      </table>
      <div style="font-weight:bold;margin:6px 0">评审文件</div>
      <table style="margin-bottom:8px">
        <thead><tr><th>文件名称</th><th style="width:140px">编号</th><th style="width:60px">版本</th><th style="width:200px">评审意见</th><th style="width:80px">结论</th></tr></thead>
        <tbody>${fileRows}</tbody>
      </table>
    </div>`
  }).join('')

  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${PAGE_STYLE}</head><body>
    <h2>文件评审汇总表（A-027）</h2>
    ${header}
    ${blocks || '<div style="text-align:center;margin-top:20px">暂无数据</div>'}
  </body></html>`
}

/**
 * 自查空表（现场检查用）：只打印条款列表，结果/问题/措施留空。
 */
export function buildEmptySelfInspectionHtml({ campaignTitle, year, assignee, rows }) {
  const trs = (rows || []).map((r, i) => {
    const na = isNoRequirementRow(r)
    return `<tr style="height:72px">
      <td style="text-align:center">${i + 1}</td>
      <td><b>${escapeHtml(r.clause_no)}</b>${r.title ? ' ' + escapeHtml(r.title) : ''}</td>
      <td class="pre">${clauseBody(r)}</td>
      <td class="pre">${escapeHtml(r.check_content || (na ? '—' : ''))}</td>
      <td style="text-align:center">${na ? '不适用' : '　'}</td>
      <td>${na ? '—' : '　'}</td>
      <td>${na ? '—' : '　'}</td>
    </tr>`
  }).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${PAGE_STYLE}</head><body>
    <h2>科室自查（条款内审）现场检查表</h2>
    <div class="sub">CNAS-AL02-07 附表3 自查表（空表）</div>
    <div class="meta">活动：${escapeHtml(campaignTitle || '')}（${escapeHtml(year || '')}）　检查人：${escapeHtml(assignee || '')}　日期：${new Date().toLocaleDateString('zh-CN')}</div>
    <table>
      <thead><tr>
        <th style="width:34px">序号</th><th style="width:150px">条款</th><th>条款内容 / 核查要点</th>
        <th>核查内容</th><th style="width:64px">结果</th><th>问题描述</th><th>采取措施</th>
      </tr></thead>
      <tbody>${trs || '<tr><td colspan="7" style="text-align:center">暂无数据</td></tr>'}</tbody>
    </table>
    <div style="margin-top:20px;display:flex;justify-content:space-between">
      <span>检查人签字：________________</span>
      <span>日期：________________</span>
    </div>
  </body></html>`
}

export function printHtml(html) {
  const w = window.open('', '_blank')
  if (!w) {
    alert('浏览器拦截了打印窗口，请允许本站点弹出窗口后重试')
    return
  }
  w.document.open()
  w.document.write(html)
  w.document.close()
  w.focus()
  setTimeout(() => { try { w.print() } catch (e) {} }, 350)
}

export function downloadDoc(html, filename) {
  // 以 .doc 形式下载（Word 可正常打开的 HTML 包装）
  const blob = new Blob(['﻿' + html], { type: 'application/msword;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { window.URL.revokeObjectURL(url); a.remove() }, 1000)
}
