// 生成「维修记录二维码」PDF：A4 每页 6 联（2列×3行），含二维码+仪器名称+型号+提示
// 运行：NODE_PATH=<workspace node_modules> node scripts/gen_repair_qr_pdf.mjs
import fs from 'fs'
import path from 'path'
import { createRequire } from 'module'
const require = createRequire('C:/Users/81526/.workbuddy/binaries/node/workspace/node_modules/')
const QRCode = require('qrcode')
const { chromium } = require('playwright')

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const OUT_DIR = path.resolve('outputs')
const CHROME = 'C:/Users/81526/AppData/Local/ms-playwright/chromium-1232/chrome-win64/chrome.exe'

// 1) 登录 + 取岗位仪器映射（7 个岗位涉及的全部仪器）
const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + lg.access_token }

const mapRes = await fetch(H + '/api/v1/education/post-instrument-maps?page_size=300', { headers: HDR }).then((r) => r.json())
const maps = mapRes.items || []
const codes = [...new Set(maps.map((m) => m.instrument_code).filter(Boolean))]

// 仪器档案（取名称/型号）
const instRes = await fetch(H + '/api/v1/instruments?page_size=1000', { headers: HDR }).then((r) => r.json())
const byCode = Object.fromEntries((instRes.items || []).map((x) => [x.dept_no, x]))

// 组装：按岗位顺序、岗位内按 sort_no
const items = []
const seen = new Set()
// 兼容一行里写了多个编号（如 MHZYY-JYK-SM-1015/1023）：拆成多条，各自独立二维码
const expand = (codeStr) => {
  const parts = String(codeStr || '').split('/').map((x) => x.trim()).filter(Boolean)
  if (parts.length <= 1) return parts
  const out = []
  const prefix = (parts[0].match(/^(.*?)(?:SM-)?\d+$/) || [])[1] || ''
  for (const p of parts) out.push(p.includes('-') ? p : prefix + 'SM-' + p)
  return out
}
for (const m of maps) {
  for (const code of expand(m.instrument_code)) {
    if (!code || seen.has(code)) continue
    seen.add(code)
    const inst = byCode[code] || {}
    items.push({
      post: m.post,
      name: m.instrument_name || inst.name || '',
      model: inst.model || '',
      code,
      url: `${H}/repair-fill?code=${encodeURIComponent(code)}`,
    })
  }
}
console.log('仪器总数:', items.length, '（唯一编号', codes.length, '）')

// 2) 生成二维码 dataURL
for (const it of items) {
  it.qr = await QRCode.toDataURL(it.url, { width: 600, margin: 1, errorCorrectionLevel: 'M' })
}

// 3) 拼 A4 六联 HTML
const cell = (it) => `
  <div class="cell">
    <div class="qr"><img src="${it.qr}" /></div>
    <div class="info">
      <div class="name">${it.name}</div>
      <div class="model">${it.model ? '型号：' + it.model : ''}</div>
      <div class="code">编号：${it.code.replace('MHZYY-JYK-', '')}</div>
      <div class="tip">设备故障请扫码填写维修记录<br/>（免登录 · 长期有效）</div>
    </div>
  </div>`

const pages = []
for (let i = 0; i < items.length; i += 6) {
  const chunk = items.slice(i, i + 6)
  while (chunk.length < 6) chunk.push(null)
  pages.push(`<div class="page">${chunk.map((c) => (c ? cell(c) : '<div class="cell empty"></div>')).join('')}</div>`)
}

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>维修记录二维码</title>
<style>
  @page { size: A4; margin: 8mm; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #111; }
  .page { width: 100%; height: 277mm; overflow: hidden; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, minmax(0, 1fr)); gap: 3mm; page-break-after: always; }
  .page:last-child { page-break-after: auto; }
  .cell { border: 1px dashed #999; border-radius: 3mm; padding: 3mm; display: flex; gap: 3mm; align-items: center; break-inside: avoid; overflow: hidden; }
  .cell.empty { border-color: transparent; }
  .qr img { width: 42mm; height: 42mm; display: block; }
  .info { flex: 1; min-width: 0; }
  .name { font-size: 13pt; font-weight: 700; line-height: 1.25; }
  .model { font-size: 10pt; margin-top: 1mm; color: #333; }
  .code { font-size: 9pt; margin-top: 1mm; color: #555; }
  .tip { font-size: 8.5pt; margin-top: 2mm; color: #666; border-top: 1px solid #ddd; padding-top: 1.5mm; }
</style></head><body>
${pages.join('')}
</body></html>`

fs.writeFileSync(path.join(OUT_DIR, '维修二维码_A4六联.html'), html, 'utf8')

// 4) 转 PDF
const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage()
await page.setContent(html, { waitUntil: 'load' })
const pdfPath = path.join(OUT_DIR, '维修记录二维码_A4六联_v2.pdf')
await page.pdf({ path: pdfPath, format: 'A4', printBackground: true, margin: { top: '8mm', bottom: '8mm', left: '8mm', right: '8mm' } })
await browser.close()
console.log('PDF 已生成:', pdfPath)
console.log('内容示例:', items.slice(0, 3).map((i) => `${i.name}/${i.model}`).join(' | '))
