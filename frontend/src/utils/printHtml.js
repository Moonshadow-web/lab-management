// 在新窗口中渲染 HTML 并触发打印，避免与站内 CSS 冲突。
// html: 完整的内联样式 HTML 字符串（表格等）。
export function printHtml(title, html) {
  const doc = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #1f2937; padding: 24px; }
  h2 { font-size: 18px; margin: 0 0 4px; }
  .meta { color: #6b7280; font-size: 13px; margin-bottom: 16px; }
  h3 { font-size: 15px; margin: 18px 0 6px; border-left: 4px solid #2563eb; padding-left: 8px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 8px; font-size: 13px; }
  th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }
  th { background: #f1f5f9; font-weight: 600; }
  .num { text-align: center; }
  .grp { color: #6b7280; font-size: 12px; margin: 2px 0 4px; }
  @media print { body { padding: 8px; } }
</style></head><body>${html}</body></html>`

  // 1) 首选：新窗口（用户可直接另存/预览）
  const w = window.open('', '_blank')
  if (w && w.document) {
    w.document.open()
    w.document.write(doc)
    w.document.close()
    w.focus()
    setTimeout(() => {
      try { w.print() } catch (e) { /* ignore */ }
    }, 250)
    return
  }

  // 2) 兜底：弹窗被拦截时，用隐藏 iframe 直接打印（无需弹窗权限）
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  document.body.appendChild(iframe)
  const idoc = iframe.contentWindow.document
  idoc.open()
  idoc.write(doc)
  idoc.close()
  setTimeout(() => {
    try { iframe.contentWindow.focus(); iframe.contentWindow.print() } catch (e) { /* ignore */ }
    setTimeout(() => { try { document.body.removeChild(iframe) } catch (e) { /* ignore */ } }, 1500)
  }, 300)
}
