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

/**
 * 自查（条款内审）报告 HTML。
 * rows: [{clause_no,title,content,check_content,result,finding,action}]
 */
export function buildSelfInspectionHtml({ campaignTitle, year, assignee, rows, generatedAt }) {
  const trs = (rows || []).map((r, i) => {
    const res = (r.result || '').trim()
    const resCls = res === '符合' ? 'ok' : res === '不符合' ? 'bad'
      : res === '观察项' ? 'warn' : res === '不适用' ? 'na' : ''
    return `<tr>
      <td style="text-align:center">${i + 1}</td>
      <td><b>${escapeHtml(r.clause_no)}</b>${r.title ? ' ' + escapeHtml(r.title) : ''}</td>
      <td class="pre">${escapeHtml(r.content || '（无）')}</td>
      <td class="pre">${escapeHtml(r.check_content || '（未填写）')}</td>
      <td class="${resCls}" style="text-align:center">${escapeHtml(res || '—')}</td>
      <td class="pre">${escapeHtml(r.finding || '')}</td>
      <td class="pre">${escapeHtml(r.action || '')}</td>
    </tr>`
  }).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${PAGE_STYLE}</head><body>
    <h2>科室自查（条款内审）报告</h2>
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
  const blocks = (rows || []).map((r) => {
    const files = (r.review_files || []).map(f =>
      `<li>${escapeHtml(f.title || '')}　编号：${escapeHtml(f.doc_number || '')}　版本：${escapeHtml(f.version || '')}　意见：${escapeHtml(f.comment || '')}　结论：${escapeHtml(f.conclusion || '')}</li>`
    ).join('') || '<li>无</li>'
    return `<div style="margin-bottom:14px">
      <h3 style="margin:6px 0;font-size:14px">${escapeHtml(r.reviewer || '')}　<span style="font-weight:normal;color:#555">（${escapeHtml(r.status || '')}）</span></h3>
      <div>评审组成员：${escapeHtml(r.review_members || '—')}　审批人：${escapeHtml(r.approver || '—')}　记录日期：${escapeHtml(r.record_date || '—')}</div>
      <div>主要存在问题：${escapeHtml(r.problems || '无')}</div>
      <div>评审文件：</div>
      <ul style="margin:4px 0">${files}</ul>
    </div>`
  }).join('')
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">${PAGE_STYLE}</head><body>
    <h2>文件评审汇总表（A-027）</h2>
    <div class="sub">${escapeHtml(campaignTitle || '')}（${escapeHtml(year || '')}）</div>
    ${blocks || '<div style="text-align:center">暂无数据</div>'}
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
