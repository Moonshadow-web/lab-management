function i(e,o){const t=window.open("","_blank");if(!t){alert("浏览器拦截了打印窗口，请允许弹出窗口后重试");return}t.document.open(),t.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${e}</title>
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
</style></head><body>${o}</body></html>`),t.document.close(),t.focus(),setTimeout(()=>{t.print(),setTimeout(()=>{try{t.close()}catch{}},500)},250)}export{i as p};
