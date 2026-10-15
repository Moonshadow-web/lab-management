// 分子组「维修记录二维码」PDF：A4 每页 6 联（2列×3行）
// 数据源：管理员登录 → 切到分子组(fz) → 取本组仪器 → 排除生物安全柜/离心机/工作台
// 运行：node scripts/gen_repair_qr_pdf_fz.mjs
import fs from 'fs'
import path from 'path'
import { createRequire } from 'module'
const require = createRequire('C:/Users/81526/.workbuddy/binaries/node/workspace/node_modules/')
const QRCode = require('qrcode')
const { chromium } = require('playwright')

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'
const OUT_DIR = path.resolve('outputs')
const CHROME = 'C:/Users/81526/AppData/Local/ms-playwright/chromium-1232/chrome-win64/chrome.exe'
const GROUP = 'fz'
const GROUP_LABEL = '分子组'

// 这些辅助设备不生成维修二维码（按设备名称关键词排除）
const EXCLUDE = ['生物安全柜', '离心机', '工作台']

const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=jinzizheng&password=Jzz6827556',
}).then((r) => r.json())
if (!lg.access_token) { console.error('登录失败', lg); process.exit(1) }

const sw = await fetch(H + '/api/v1/auth/switch-group?group_code=' + GROUP, {
  method: 'POST', headers: { Authorization: 'Bearer ' + lg.access_token },
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + (sw.access_token || lg.access_token) }
console.log('已切换到:', sw.group_code)

const instRes = await fetch(H + '/api/v1/instruments?page=1&page_size=300', { headers: HDR }).then((r) => r.json())
const all = (instRes.items || []).filter((x) => (x.status || '') !== '停用')
const keep = all.filter((x) => !EXCLUDE.some((k) => (x.name || '').includes(k)))
const drop = all.filter((x) => EXCLUDE.some((k) => (x.name || '').includes(k)))
console.log(`本组在用 ${all.length} 台；排除 ${drop.length} 台（${drop.map((d) => d.name).join('、')}）；生成 ${keep.length} 台`)

// 按科室编号自然序
keep.sort((a, b) => String(a.dept_no).localeCompare(String(b.dept_no), 'zh'))

const items = keep.map((x) => ({
  name: x.name,
  model: x.model || '',
  code: x.dept_no,
  location: x.location || '',
  owner: x.owner || '',
  url: `${H}/repair-fill?code=${encodeURIComponent(x.dept_no)}`,
}))
for (const it of items) {
  it.qr = await QRCode.toDataURL(it.url, { width: 600, margin: 1, errorCorrectionLevel: 'M' })
}

const cell = (it) => `
  <div class="cell">
    <div class="qr"><img src="${it.qr}" /></div>
    <div class="info">
      <div class="cat">${GROUP_LABEL} · ${it.code.replace('MHZYY-JYK-', '')}</div>
      <div class="name">${it.name}</div>
      <div class="model">${it.model ? '型号：' + it.model : ''}</div>
      <div class="loc">${it.location ? '位置：' + it.location : ''}</div>
      <div class="tip">设备故障请扫码填写维修记录<br/>（免登录 · 长期有效）</div>
    </div>
  </div>`

const pages = []
for (let i = 0; i < items.length; i += 6) {
  const chunk = items.slice(i, i + 6)
  while (chunk.length < 6) chunk.push(null)
  pages.push(`<div class="page">${chunk.map((c) => (c ? cell(c) : '<div class="cell empty"></div>')).join('')}</div>`)
}

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>分子组仪器维修二维码</title>
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
  .loc { font-size: 8.5pt; margin-top: .8mm; color: #666; }
  .tip { font-size: 8pt; margin-top: 1.5mm; color: #777; border-top: 1px solid #ddd; padding-top: 1.2mm; }
</style></head><body>
${pages.join('')}
</body></html>`

fs.writeFileSync(path.join(OUT_DIR, '分子组维修二维码_A4六联.html'), html, 'utf8')

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage()
await page.setContent(html, { waitUntil: 'load' })
const pdfPath = path.join(OUT_DIR, '分子组维修记录二维码_A4六联.pdf')
await page.pdf({ path: pdfPath, format: 'A4', printBackground: true, margin: { top: '8mm', bottom: '8mm', left: '8mm', right: '8mm' } })
await page.waitForTimeout(300)
const n = await page.locator('.page').count()
await page.locator('.page').first().screenshot({ path: path.join(OUT_DIR, '分子组二维码_第1页.png') })
await page.locator('.page').nth(n - 1).screenshot({ path: path.join(OUT_DIR, `分子组二维码_第${n}页.png`) })
await browser.close()
console.log('PDF 已生成:', pdfPath, '| 页数:', Math.ceil(items.length / 6))
for (const it of items) console.log('  ', it.code.replace('MHZYY-JYK-', ''), it.name, it.model)
