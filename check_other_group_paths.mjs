// 自检：AppLayout.vue 的 OTHER_GROUP_PATHS 与 router/index.js 的 OTHER_GROUP_ALLOWED
// 两份「非生免组可访问路径」白名单必须完全一致，否则会出现
// 「菜单看得到 → 点进去被路由守卫弹回工作台」。
// 用法：node outputs/wjx/check_other_group_paths.mjs
import fs from 'node:fs'

const layout = fs.readFileSync('frontend/src/layout/AppLayout.vue', 'utf8')
const router = fs.readFileSync('frontend/src/router/index.js', 'utf8')

const pick = (src, name) => {
  const m = src.match(new RegExp(`const ${name} = new Set\\(\\[([\\s\\S]*?)\\]\\)`))
  if (!m) { console.error(`✗ 找不到 ${name}`); process.exit(1) }
  return new Set([...m[1].matchAll(/'([^']+)'/g)].map((x) => x[1]))
}

const a = pick(layout, 'OTHER_GROUP_PATHS')   // 菜单
const b = pick(router, 'OTHER_GROUP_ALLOWED') // 路由守卫

const onlyMenu = [...a].filter((x) => !b.has(x))
const onlyGuard = [...b].filter((x) => !a.has(x))

console.log(`菜单白名单 ${a.size} 条 / 守卫白名单 ${b.size} 条`)
if (onlyMenu.length || onlyGuard.length) {
  if (onlyMenu.length) console.log('✗ 只在菜单里（会被守卫弹回）:', onlyMenu.join(', '))
  if (onlyGuard.length) console.log('✗ 只在守卫里（菜单看不到）:', onlyGuard.join(', '))
  process.exit(1)
}
console.log('✓ 两份白名单一致')
