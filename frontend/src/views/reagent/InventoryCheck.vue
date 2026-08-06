<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">盘库管理</h2>
      <p class="sub">按项目显示试剂与校准品、按仪器显示耗材（同型号多台共用一次录入）、质控品单独列示。录入余量后自动更新实时库存。</p>
    </div>
    <LibraryTabs @change="refresh" />

    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewCheck" v-if="canWrite">新建盘库</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="checks" border stripe height="calc(100vh - 360px)">
      <el-table-column type="index" width="50" />
      <el-table-column prop="library" label="责任库" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.library" size="small" :type="row.library === '免疫' ? 'warning' : 'success'">{{ row.library }}</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="check_date" label="盘库日期" width="120" />
      <el-table-column prop="check_type" label="类型" width="100" />
      <el-table-column prop="operator" label="操作人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onView(row)">详情</el-button>
          <el-button size="small" link type="primary" @click="onPrintCheck(row)">打印</el-button>
          <el-button size="small" link type="danger" @click="onDeleteCheck(row)" v-if="canWrite">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建盘库弹窗 -->
    <el-dialog v-model="dialogVisible" :title="`新建盘库（${reagentStore.library}）`" width="min(960px, 96vw)" top="3vh">
      <el-form :model="checkForm" label-width="80px" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="日期"><el-date-picker v-model="checkForm.check_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类型"><el-select v-model="checkForm.check_type" style="width:100%">
            <el-option label="月末盘库" value="月末盘库" /><el-option label="月中盘库" value="月中盘库" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="备注"><el-input v-model="checkForm.remark" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-select v-model="categoryFilter" placeholder="全部分类" clearable style="width:130px" size="default">
          <el-option label="按品牌" value="brand" />
          <el-option label="试剂 / 校准品" value="reagent" />
          <el-option label="耗材" value="consumable" />
          <el-option label="质控品" value="control" />
        </el-select>
        <el-input v-model="dialogSearch" placeholder="模糊检索试剂/规格/编码/项目名(含英文别名如ALT)..." clearable style="width:340px" />
        <el-button @click="onPrintBlank" :icon="Printer" size="small">打印空白录入页</el-button>
        <span class="muted" style="font-size:12px">共 {{ totalEntries }} 项</span>
      </div>

      <div class="entry-scroll">
        <!-- 按项目 -->
        <template v-for="grp in filteredProjects" :key="'p'+grp.test_item_id">
          <h4 class="grp-title">项目：{{ grp.test_item_name }}</h4>
          <el-table :data="grp.items" border size="small">
            <el-table-column label="试剂 / 校准品" min-width="190">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }} · {{ row.brand }}</span></template>
            </el-table-column>
            <el-table-column label="盘点余量" width="120" fixed="right">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:110px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <!-- 按仪器 -->
        <template v-for="grp in filteredInstruments" :key="'i'+grp.group">
          <h4 class="grp-title">仪器：{{ grp.group }} <span class="muted" v-if="grp.instruments.length">（{{ grp.instruments.join('、') }}）</span></h4>
          <el-table :data="grp.items" border size="small">
            <el-table-column label="耗材" min-width="190">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }} · {{ row.brand }}</span></template>
            </el-table-column>
            <el-table-column label="盘点余量" width="120" fixed="right">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:110px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <!-- 质控品 -->
        <template v-if="filteredControls.length">
          <h4 class="grp-title">质控品（单独）</h4>
          <el-table :data="filteredControls" border size="small">
            <el-table-column label="质控品" min-width="190">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }} · {{ row.brand }}</span></template>
            </el-table-column>
            <el-table-column label="盘点余量" width="120" fixed="right">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:110px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <!-- 按品牌 -->
        <template v-if="filteredByBrand.length">
          <template v-for="grp in filteredByBrand" :key="'b'+grp.brand">
            <h4 class="grp-title">品牌：{{ grp.brand }}</h4>
            <el-table :data="grp.items" border size="small">
              <el-table-column label="名称 / 规格 / 品牌" min-width="200">
                <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }} · {{ row.brand }}</span></template>
              </el-table-column>
              <el-table-column label="盘点余量" width="120" fixed="right">
                <template #default="{ row }">
                  <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:110px" controls-position="right" />
                </template>
              </el-table-column>
            </el-table>
          </template>
        </template>
        <el-empty v-if="totalEntries === 0" description="该分类/检索条件下无数据" />
      </div>

      <template #footer>
        <el-button @click="onPrintBlank" :icon="Printer">打印空白页</el-button>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交盘库</el-button>
      </template>
    </el-dialog>

    <!-- 查看盘库详情 -->
    <el-dialog v-model="viewVisible" :title="`盘库详情（${viewLibrary}）`" width="640px">
      <el-table :data="viewItems" border size="small">
        <el-table-column label="试剂/耗材" min-width="220">
          <template #default="{ row }">{{ row._name || `(id=${row.item_id})`}} <span class="muted">{{ row._spec }}</span></template>
        </el-table-column>
        <el-table-column label="批号" width="120"><template #default="{ row }">{{ row.batch_no || '-' }}</template></el-table-column>
        <el-table-column label="效期" width="110"><template #default="{ row }">{{ row.expiry_date || '-' }}</template></el-table-column>
        <el-table-column label="余量" width="80" align="center"><template #default="{ row }">{{ row.recorded_quantity }}</template></el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="onPrintView" :icon="Printer">打印盘库表</el-button>
        <el-button @click="viewVisible=false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Printer } from '@element-plus/icons-vue'
import { listInventoryChecks, getInventoryCheck, createInventoryCheck, deleteInventoryCheck, getReagentTemplate, listAllReagentItems } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'
import { useReagentStore } from '../../store/reagent'
import { errText } from '../../utils/errText'
import { printHtml } from '../../utils/printHtml'
import LibraryTabs from '../../components/reagent/LibraryTabs.vue'

const auth = useAuthStore()
const reagentStore = useReagentStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const checks = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), submitting = ref(false)
const dialogSearch = ref('')
const categoryFilter = ref('')  // '' | 'reagent' | 'consumable' | 'control'
const checkForm = ref({ check_date: '', check_type: '月末盘库', remark: '' })
const tpl = ref(null)
const quantities = reactive({})
const nameMap = ref({})

const viewVisible = ref(false), viewItems = ref([]), viewLibrary = ref('')

async function refresh() {
  loading.value = true
  try {
    const r = await listInventoryChecks({ library: reagentStore.library, page: page.value, page_size: pageSize.value })
    checks.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) } finally { loading.value = false }
}

function allItems() {
  if (!tpl.value) return []
  const out = []
  for (const g of tpl.value.by_project) out.push(...g.items)
  for (const g of tpl.value.by_instrument) out.push(...g.items)
  out.push(...tpl.value.controls)
  return out
}
const totalEntries = computed(() => {
  if (!tpl.value) return 0
  if (categoryFilter.value === 'brand') return allItems().filter(matchItem).length
  let n = 0
  if (categoryFilter.value === '' || categoryFilter.value === 'reagent')
    for (const g of tpl.value.by_project) n += g.items.filter(matchItem).length
  if (categoryFilter.value === '' || categoryFilter.value === 'consumable')
    for (const g of tpl.value.by_instrument) n += g.items.filter(matchItem).length
  if ((categoryFilter.value === '' || categoryFilter.value === 'control') && tpl.value.controls)
    n += tpl.value.controls.filter(matchItem).length
  return n
})

/** 模糊匹配：试剂名/规格/编码 + 项目中文名/英文别名 */
function matchItem(it) {
  const kw = dialogSearch.value.trim().toLowerCase()
  if (!kw) return true
  // 试剂自身字段
  if ((it.name || '').toLowerCase().includes(kw)) return true
  if ((it.spec || '').toLowerCase().includes(kw)) return true
  if ((it.material_code || '').toLowerCase().includes(kw)) return true
  // 项目名称 + 英文别名（逗号分隔，支持 ALT / ATIII 等）
  if (it.project_name && it.project_name.toLowerCase().includes(kw)) return true
  if (it.project_aliases) {
    for (const alias of it.project_aliases.split(','))
      if (alias.trim().toLowerCase().includes(kw)) return true
  }
  return false
}

const filteredProjects = computed(() => {
  if (!tpl.value) return []
  if (categoryFilter.value && categoryFilter.value !== 'reagent') return []
  return tpl.value.by_project.map(g => ({ ...g, items: g.items.filter(matchItem) })).filter(g => g.items.length)
})
const filteredInstruments = computed(() => {
  if (!tpl.value) return []
  if (categoryFilter.value && categoryFilter.value !== 'consumable') return []
  return tpl.value.by_instrument.map(g => ({ ...g, items: g.items.filter(matchItem) })).filter(g => g.items.length)
})
const filteredControls = computed(() => {
  if (!tpl.value || !tpl.value.controls) return []
  if (categoryFilter.value && categoryFilter.value !== 'control') return []
  return tpl.value.controls.filter(matchItem)
})
const filteredByBrand = computed(() => {
  if (!tpl.value || categoryFilter.value !== 'brand') return []
  const map = {}
  for (const it of allItems()) {
    if (!matchItem(it)) continue
    const b = it.brand || '未标注品牌'
    if (!map[b]) map[b] = []
    map[b].push(it)
  }
  return Object.keys(map)
    .sort((a, b) => {
      if (a === '未标注品牌') return 1
      if (b === '未标注品牌') return -1
      return a.localeCompare(b, 'zh-CN')
    })
    .map(brand => ({ brand, items: map[brand] }))
})

async function onNewCheck() {
  dialogSearch.value = ''
  categoryFilter.value = ''
  checkForm.value = { check_date: new Date().toISOString().slice(0,10), check_type: '月末盘库', remark: '' }
  dialogVisible.value = true
  submitting.value = true
  try {
    const r = await getReagentTemplate({ library: reagentStore.library })
    tpl.value = r[reagentStore.library] || { by_project: [], by_instrument: [], controls: [] }
    for (const it of allItems()) quantities[it.item_id] = it.current_stock
  } catch (e) {
    ElMessage.error('加载模板失败：' + errText(e))
  } finally { submitting.value = false }
}

function buildSections(useRecorded) {
  const secs = []
  for (const g of tpl.value.by_project) {
    secs.push({ heading: '项目：' + g.test_item_name, items: g.items.map(it => ({
      name: it.name, spec: it.spec, unit: it.unit, material_code: it.material_code,
      brand: it.brand,
      current: it.current_stock,
      qty: useRecorded ? (quantities[it.item_id] || 0) : '',
    })) })
  }
  for (const g of tpl.value.by_instrument) {
    const extra = g.instruments.length ? `（${g.instruments.join('、')}）` : ''
    secs.push({ heading: '仪器：' + g.group + extra, items: g.items.map(it => ({
      name: it.name, spec: it.spec, unit: it.unit, material_code: it.material_code,
      brand: it.brand,
      current: it.current_stock,
      qty: useRecorded ? (quantities[it.item_id] || 0) : '',
    })) })
  }
  if (tpl.value.controls.length) {
    secs.push({ heading: '质控品（单独）', items: tpl.value.controls.map(it => ({
      name: it.name, spec: it.spec, unit: it.unit, material_code: it.material_code,
      brand: it.brand,
      current: it.current_stock,
      qty: useRecorded ? (quantities[it.item_id] || 0) : '',
    })) })
  }
  return secs
}

function sectionHtml(secs) {
  let h = ''
  for (const s of secs) {
    h += `<h3>${s.heading}</h3>`
    h += '<table><thead><tr><th>名称</th><th>规格</th><th>品牌</th><th>材料编码</th><th>单位</th><th class="num">当前库存</th><th class="num">盘点余量</th></tr></thead><tbody>'
    for (const it of s.items) {
      h += `<tr><td>${it.name || ''}</td><td>${it.spec || ''}</td><td>${it.brand || ''}</td><td>${it.material_code || ''}</td><td>${it.unit || ''}</td><td class="num">${it.current}</td><td class="num">${it.qty}</td></tr>`
    }
    h += '</tbody></table>'
  }
  return h
}

function onPrintBlank() {
  if (!tpl.value) return
  const html = sectionHtml(buildSections(false))
  printHtml(`盘库空白录入页（${reagentStore.library}）`,
    `<h2>试剂盘库录入页（空白）</h2><div class="meta">责任库：${reagentStore.library}　打印日期：${new Date().toLocaleDateString('zh-CN')}</div>${html}`)
}

async function onSubmit() {
  if (!checkForm.value.check_date) { ElMessage.warning('请选择盘库日期'); return }
  submitting.value = true
  try {
    const items = allItems().map(it => ({
      item_id: it.item_id, batch_no: '', expiry_date: null,
      recorded_quantity: Number(quantities[it.item_id] || 0),
    }))
    await createInventoryCheck({ library: reagentStore.library, ...checkForm.value, items })
    ElMessage.success('盘库成功，实时库存已更新')
    dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('盘库失败：' + errText(e)) } finally { submitting.value = false }
}

async function onView(row) {
  try {
    const r = await getInventoryCheck(row.id)
    if (Object.keys(nameMap.value).length === 0) {
      // 加载全库名称映射（含停用项），避免因责任库不同导致跨库盘库解析不到名称而回退成 (id=…)
      const all = await listAllReagentItems()
      for (const it of all) nameMap.value[it.id] = it
    }
    // 只展示实际盘点过且有余量的条目；数量为 0 / 空 视为“未盘”，详情与打印均不显示
    viewItems.value = (r.items || [])
      .filter(i => (i.recorded_quantity ?? 0) > 0)
      .map(i => ({
        ...i,
        _name: nameMap.value[i.item_id]?.name || '',
        _spec: nameMap.value[i.item_id]?.spec || '',
      }))
    viewLibrary.value = row.library || reagentStore.library
    viewVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败：' + errText(e)) }
}

function onPrintView() {
  let h = '<table><thead><tr><th>名称</th><th>规格</th><th>批号</th><th>效期</th><th class="num">余量</th></tr></thead><tbody>'
  for (const it of viewItems.value) {
    const qty = (it.recorded_quantity === null || it.recorded_quantity === undefined) ? '-' : it.recorded_quantity
    h += `<tr><td>${it._name || it.item_id}</td><td>${it._spec || ''}</td><td>${it.batch_no || ''}</td><td>${it.expiry_date || ''}</td><td class="num">${qty}</td></tr>`
  }
  h += '</tbody></table>'
  printHtml(`盘库表（${viewLibrary.value}）`,
    `<h2>试剂盘库表</h2><div class="meta">责任库：${viewLibrary.value}　打印日期：${new Date().toLocaleDateString('zh-CN')}</div>${h}`)
}

function onPrintCheck(row) { onView(row).then(() => { if (viewVisible.value) onPrintView() }) }

async function onDeleteCheck(row) {
  await ElMessageBox.confirm(
    `确认删除「${row.check_date} ${row.check_type}」盘库记录？该操作不可恢复。`,
    '删除盘库', { type: 'warning' }
  )
  await deleteInventoryCheck(row.id); ElMessage.success('已删除'); refresh()
}

onMounted(refresh)
</script>
<style scoped>
.page { padding: 16px 20px 0; display: flex; flex-direction: column; height: 100%; }
.page-header { margin-bottom: 8px; }
.title { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0; color: #64748b; font-size: 13px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin: 8px 0 12px; flex-wrap: wrap; }
.pager { margin: 10px 0 16px; display: flex; justify-content: flex-end; }
.muted { color: #94a3b8; }
.entry-scroll { max-height: 56vh; overflow: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px; }
.grp-title { margin: 14px 0 6px; font-size: 14px; color: #0f172a; border-left: 4px solid #2563eb; padding-left: 8px; }
.grp-title:first-child { margin-top: 4px; }
</style>
