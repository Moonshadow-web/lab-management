function p(d,r){const n=`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${d}</title>
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
  /* 受控表格页脚：用 table-footer-group 保证【每页】都打印（position:fixed 在 Chrome 打印时只在首页出现） */
  table.doc { border: 0; margin: 0; }
  table.doc > * > tr > td { border: 0; padding: 0; }
  .doc-foot { font-size: 12px; color: #374151; padding-top: 10px; }
  @media print {
    body { padding: 8px; }
    thead { display: table-header-group; }
    tfoot { display: table-footer-group; }
  }
</style></head><body>${r}</body></html>`,e=window.open("","_blank");if(e&&e.document){e.document.open(),e.document.write(n),e.document.close(),e.focus(),setTimeout(()=>{try{e.print()}catch{}},250);return}const t=document.createElement("iframe");t.style.position="fixed",t.style.right="0",t.style.bottom="0",t.style.width="0",t.style.height="0",t.style.border="0",document.body.appendChild(t);const o=t.contentWindow.document;o.open(),o.write(n),o.close(),setTimeout(()=>{try{t.contentWindow.focus(),t.contentWindow.print()}catch{}setTimeout(()=>{try{document.body.removeChild(t)}catch{}},1500)},300)}export{p};
