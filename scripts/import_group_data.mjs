// 其他专业组数据导入模板（等你提供 Excel/CSV 后按此改造即可）
//
// 设计要点：
//  1) 必须以目标组的管理员身份、并把令牌切到该组后导入 → 数据自动落到该组（group_code）
//  2) 只导入目标组自己的数据；**禁止**把生免组数据复制过去
//  3) 先 dryRun 预览，再实际写入；逐条打印成功/失败
//
// 用法：node scripts/import_group_data.mjs --group=lj --kind=test-items --file=outputs/临检项目.xlsx --dry-run
//
const args = Object.fromEntries(process.argv.slice(2).map((a) => a.replace(/^--/, '').split('=')))
const GROUP = args.group || 'lj'
const KIND = args.kind || 'test-items'
const FILE = args.file || ''
const DRY = 'dry-run' in args

const H = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'

// 1) 管理员登录并切换到目标组
const lg = await fetch(H + '/api/v1/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `username=${process.env.ADMIN_USER || 'jinzizheng'}&password=${process.env.ADMIN_PASS || ''}`,
}).then((r) => r.json())
if (!lg.access_token) throw new Error('管理员登录失败（请设置 ADMIN_PASS 环境变量）')
const sw = await fetch(`${H}/api/v1/auth/switch-group?group_code=${GROUP}`, {
  method: 'POST', headers: { Authorization: 'Bearer ' + lg.access_token },
}).then((r) => r.json())
const HDR = { Authorization: 'Bearer ' + sw.access_token, 'Content-Type': 'application/json' }
console.log(`已切到专业组：${GROUP}（导入数据将归属该组）`)

// 2) 读取源文件（Excel/CSV）→ rows
//    TODO: 收到实际数据后在此解析；以下为结构示例
const rows = [] // [{ code, name, category, specimen, method, instrument, brand, ... }]
if (!rows.length) {
  console.log('源文件:', FILE || '(未提供)')
  console.log('提示：请先提供数据文件，我再按其列结构补全解析逻辑（支持 xlsx/csv）。')
}

// 3) 校验：不得与生免组重号（跨组同号会因唯一约束被拒；共享编号须含 KS）
const existing = await fetch(`${H}/api/v1/test-items?page_size=1000`, { headers: HDR })
  .then((r) => r.json())
  .catch(() => ({ items: [] }))
console.log(`目标组现有记录：${existing.total ?? 0} 条`)

// 4) 导入
let ok = 0, fail = 0
for (const row of rows) {
  if (DRY) { console.log('[dry-run]', JSON.stringify(row)); continue }
  const map = { 'test-items': '/api/v1/test-items', 'instruments': '/api/v1/instruments', 'documents': '/api/v1/documents' }
  const url = H + (map[KIND] || map['test-items'])
  const res = await fetch(url, { method: 'POST', headers: HDR, body: JSON.stringify(row) })
  if (res.status < 300) ok++
  else { fail++; console.log('失败:', row.code || row.dept_no, res.status, (await res.text()).slice(0, 120)) }
}
console.log(DRY ? `预览完成（${rows.length} 条，未写入）` : `导入完成：成功 ${ok}，失败 ${fail}`)
