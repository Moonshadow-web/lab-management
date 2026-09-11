# -*- coding: utf-8 -*-
"""修复打印：instrument 无 position 时按编号反查岗位；项目后台预热缓存"""
import io

p = 'frontend/src/views/training/staff/PreJobAuth.vue'
s = io.open(p, encoding='utf-8').read()

# 1) 编号→岗位 映射（来自岗位仪器匹配接口，回退 gl070Meta）
if 'codeToPost' not in s:
    s = s.replace("const GL070_META_ALL = computed(() => POSITIONS.value.flatMap(",
"""// 编号 → 岗位（打印时用；老记录 instruments_json 可能没存 position）
const codeToPost = computed(() => {
  const m = {}
  POSITIONS.value.forEach((pp) => (pp.instruments || []).forEach((i) => { if (i.code) m[i.code] = pp.name }))
  return m
})
const GL070_META_ALL = computed(() => POSITIONS.value.flatMap(""", 1)

# 2) 项目后台预热（列表加载后把各行仪器的项目拉进缓存，打印时同步可用）
if 'warmProjects' not in s:
    s = s.replace("function fetch(params) { return listPreJobAuth(params) }",
"""// 列表加载后，后台预热各行仪器的关联项目（打印是同步的，必须提前缓存）
async function warmProjects(rows) {
  const codes = []
  ;(rows || []).forEach((r) => (r.instruments_json || []).forEach((i) => { if (i.code) codes.push(i.code) }))
  const todo = [...new Set(codes)].filter((c) => !projCache.has(c))
  for (const c of todo) {
    const db = instByCode.value[c]
    let pj = ''
    if (db) {
      try {
        const items = await getInstrumentTestItems(db.id)
        pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
      } catch (e) { pj = '' }
    }
    projCache.set(c, pj)
  }
}
async function fetch(params) {
  const res = await listPreJobAuth(params)
  warmProjects(res.items || [])
  return res
}""", 1)

# 3) printForm：项目/岗位反查
s = s.replace("""  const instsOfPost = (post) => allInsts.filter((i) => (i.position || '') === post)
  const projOf = (code) => {
    const r = (row.items_json || []).find((x) => x.code === code)
    return r ? (r.items || '') : ''
  }""",
"""  const instsOfPost = (post) => allInsts.filter((i) => (i.position || codeToPost.value[i.code] || '') === post)
  const projOf = (code) => {
    const r = (row.items_json || []).find((x) => x.code === code)
    const fromRow = r ? (r.items || '') : ''
    return fromRow || projCache.get(code) || ''
  }""", 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('PreJobAuth 打印数据修复 完成')
