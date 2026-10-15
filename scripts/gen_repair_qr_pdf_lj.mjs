// 临检组「维修记录二维码」PDF：A4 每页 6 联（2列×3行）
// 与生免组同版式（scripts/gen_repair_qr_pdf.mjs），数据源改为临检组账号 + 指定设备
// 运行：node scripts/gen_repair_qr_pdf_lj.mjs
import fs from 'fs'
import path from 'path'
import { createRequire } from 'module'
const require = createRequire('C:/Users/81526/.workbuddy/binaries/node/workspace/node_modules/')
const QRCode = require('qrcode')
const { chromium } = require('playwright')

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const OUT_DIR = path.resolve('outputs')
const CHROME = 'C:/Users/81526/AppData/Local/ms-playwright/chromium-1232/chrome-win64/chrome.exe'

// 临检组账号
const USER = '龚珂'
const PWD = 'gk123456'

// 按用户列出的 12 类排序：类别 → 组内 instrument id（编号升序）
// 已剔除 3 台「停用」设备：id108 AX4030、id109/110 UF1000i（与卡尤迪C/D、UC02 重号）
const PLAN = [
  ['血细胞分析仪', [78, 79, 80, 81, 82, 86, 87, 88, 89]],
  ['特定蛋白分析仪', [83, 84, 85]],
  ['循环增强荧光分析仪', [90, 91]],
  ['尿液干化学分析仪', [96, 98]],
  ['尿液分析仪', [97, 99]],
  ['血型仪', [101]],
  ['大便分析仪', [103]],
  ['卡尤迪', [106, 107, 93, 94]],
  ['推片机', [92]],
  ['钙卫蛋白仪', [104]],
  ['流式细胞仪', [102]],
  ['UC02', [95]],
]

const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `username=${encodeURIComponent(USER)}&password=${encodeURIComponent(PWD)}`,
}).then((r) => r.json())
if (!lg.access_token) { console.error('登录失败', lg); process.exit(1) }
const HDR = { Authorization: 'Bearer ' + lg.access_token }

const instRes = await fetch(H + '/api/v1/instruments?page=1&page_size=500', { headers: HDR }).then((r) => r.json())
const byId = Object.fromEntries((instRes.items || []).map((x) => [x.id, x]))

const items = []
const missing = []
for (const [cat, ids] of PLAN) {
  for (const id of ids) {
    const inst = byId[id]
    if (!inst) { missing.push(id); continue }
    if ((inst.status || '') === '停用') { console.log('跳过停用:', id, inst.name); continue }
    items.push({
      cat,
      name: inst.name,
      model: inst.model || '',
      code: inst.dept_no,
      location: inst.location || '',
      url: `${H}/repair-fill?code=${encodeURIComponent(inst.dept_no)}`,
    })
  }
}
console.log('待生成:', items.length, '台 | 缺失:', missing.length ? missing : '无')

for (const it of items) {
  it.qr = await QRCode.toDataURL(it.url, { width: 600, margin: 1, errorCorrectionLevel: 'M' })
}

const cell = (it) => `
  <div class="cell">
    <div class="qr"><img src="${it.qr}" /></div>
    <div class="info">
      <div class="cat">临检组 · ${it.cat}</div>
      <div class="name">${it.name}</div>
      <div class="model">${it.model ? '型号：' + it.model : ''}</div>
      <div class="code">编号：${it.code.replace('MHZYY-JYK-', '')}</div>
      ${it.location ? `<div class="loc">位置：${it.location}</div>` : ''}
      <div class="tip">设备故障请扫码填写维修记录<br/>（免登录 · 长期有效）</div>
    </div>
  </div>`

const pages = []
for (let i = 0; i < items.length; i += 6) {
  const chunk = items.slice(i, i + 6)
  while (chunk.length < 6) chunk.push(null)
  pages.push(`<div class="page">${chunk.map((c) => (c ? cell(c) : '<div class="cell empty"></div>')).join('')}</div>`)
}

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>临检组仪器维修二维码</title>
<style>
  @page { size: A4; margin: 8mm; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #111; }
  .page { width: 100%; height: 277mm; overflow: hidden; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, minmax(0, 1fr)); gap: 3mm; page-break-after: always; }
  .page:last-child { page-break-after: auto; }
  .cell { border: 1px dashed #999; border-radius: 3mm; padding: 3mm; display: flex; gap: 3mm; align-items: center; break-inside: avoid; overflow: hidden; }
  .cell.empty { border-color: transparent; }
  .qr img { width: 40mm; height: 40mm; display: block; }
  .info { flex: 1; min-width: 0; }
  .cat { font-size: 8.5pt; color: #1a365d; font-weight: 700; letter-spacing: .3px; }
  .name { font-size: 13pt; font-weight: 700; line-height: 1.22; margin-top: .5mm; }
  .model { font-size: 10pt; margin-top: 1mm; color: #333; }
  .code { font-size: 9pt; margin-top: .8mm; color: #555; }
  .loc { font-size: 8.5pt; margin-top: .8mm; color: #666; }
  .tip { font-size: 8pt; margin-top: 1.5mm; color: #777; border-top: 1px solid #ddd; padding-top: 1.2mm; }
</style></head><body>
${pages.join('')}
</body></html>`

const htmlPath = path.join(OUT_DIR, '临检组维修二维码_A4六联.html')
fs.writeFileSync(htmlPath, html, 'utf8')

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage()
await page.setContent(html, { waitUntil: 'load' })
const pdfPath = path.join(OUT_DIR, '临检组维修记录二维码_A4六联.pdf')
await page.pdf({ path: pdfPath, format: 'A4', printBackground: true, margin: { top: '8mm', bottom: '8mm', left: '8mm', right: '8mm' } })
await browser.close()
console.log('PDF 已生成:', pdfPath)
console.log('页数:', Math.ceil(items.length / 6))
console.log('清单:')
for (const it of items) console.log('  ', it.code.replace('MHZYY-JYK-', ''), it.name, it.model)
