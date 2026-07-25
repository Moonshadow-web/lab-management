// 在新窗口中渲染 HTML 并触发打印，避免与站内 CSS 冲突。
// html: 完整的内联样式 HTML 字符串（表格等）。
export function printHtml(title, html) {
  const w = window.open('', '_blank')
  if (!w) {
    alert('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    return
  }
  w.document.open()
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
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
</style></head><body>${html}</body></html>`)
  w.document.close()
  w.focus()
  setTimeout(() => {
    w.print()
    // 部分浏览器打印后保留窗口供查看，延迟关闭
    setTimeout(() => { try { w.close() } catch (e) { /* ignore */ } }, 500)
  }, 250)
}
