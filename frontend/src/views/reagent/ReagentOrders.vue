<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">订购管理</h2>
      <p class="sub">按项目显示试剂、按仪器显示耗材、质控品单独列示。录入需订购数量，生成订购表可导出 Excel 或打印（含材料编码）。</p>
    </div>
    <LibraryTabs @change="refresh" />

    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewOrder" v-if="canWrite">新建订购</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="orders" border stripe height="calc(100vh - 360px)">
      <el-table-column type="index" width="50" />
      <el-table-column prop="library" label="责任库" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.library" size="small" :type="row.library === '免疫' ? 'warning' : 'success'">{{ row.library }}</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column prop="order_date" label="日期" width="110" />
      <el-table-column prop="order_type" label="类型" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === '完成' ? 'success' : row.status === '已提交' ? 'primary' : 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="细项数" width="70" align="center">
        <template #default="{ row }">{{ row.items?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="operator" label="操作人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column prop="created_by" label="创建人" width="100" />
      <el-table-column label="操作" width="230" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onExport(row)">导出</el-button>
          <el-button size="small" link type="primary" @click="onPrint(row)">打印</el-button>
          <el-button v-if="canEditRow(row)" size="small" link type="primary" @click="onEdit(row)">编辑</el-button>
          <el-button v-if="!row.is_confirmed" size="small" link type="success" @click="onConfirm(row)">确认</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建/编辑订购弹窗 -->
    <el-dialog v-model="dialogVisible" :title="(editingId ? '编辑订购' : '新建订购') + `（${reagentStore.library}）`" width="min(960px, 96vw)" top="3vh">
      <el-form :model="orderForm" label-width="80px" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="订单号"><el-input v-model="orderForm.order_no" placeholder="ORD-202607-001" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="日期"><el-date-picker v-model="orderForm.order_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类型"><el-select v-model="orderForm.order_type" style="width:100%">
            <el-option label="月初订购" value="月初订购" /><el-option label="加订" value="加订" />
          </el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="orderForm.remark" /></el-form-item>
      </el-form>
      <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-select v-model="categoryFilter" placeholder="全部分类" clearable style="width:130px" size="default">
          <el-option label="试剂 / 校准品" value="reagent" />
          <el-option label="耗材" value="consumable" />
          <el-option label="质控品" value="control" />
        </el-select>
        <el-input v-model="dialogSearch" placeholder="模糊检索试剂/规格/编码/项目名(含英文别名如ALT)..." clearable style="width:340px" />
        <span class="muted" style="font-size:12px">共 {{ totalEntries }} 项</span>
      </div>

      <div class="entry-scroll">
        <template v-for="grp in filteredProjects" :key="'p'+grp.test_item_id">
          <h4 class="grp-title">项目：{{ grp.test_item_name }}</h4>
          <div class="entry-card-list">
            <div class="entry-card" v-for="it in grp.items" :key="it.item_id">
              <div class="entry-card-name">
                <div>{{ it.name }} <span class="muted">{{ it.spec }}</span></div>
                <div class="card-stock">实时库存：{{ it.current_stock }} {{ it.unit }}<span v-if="it.min_stock">（最低 {{ it.min_stock }}）</span></div>
              </div>
              <div class="entry-card-input">
                <span class="muted">订购数量</span>
                <el-input-number v-model="quantities[it.item_id]" :min="0" size="small" controls-position="right" />
              </div>
            </div>
          </div>
        </template>
        <template v-for="grp in filteredInstruments" :key="'i'+grp.group">
          <h4 class="grp-title">仪器：{{ grp.group }} <span class="muted" v-if="grp.instruments.length">（{{ grp.instruments.join('、') }}）</span></h4>
          <div class="entry-card-list">
            <div class="entry-card" v-for="it in grp.items" :key="it.item_id">
              <div class="entry-card-name">
                <div>{{ it.name }} <span class="muted">{{ it.spec }}</span></div>
                <div class="card-stock">实时库存：{{ it.current_stock }} {{ it.unit }}<span v-if="it.min_stock">（最低 {{ it.min_stock }}）</span></div>
              </div>
              <div class="entry-card-input">
                <span class="muted">订购数量</span>
                <el-input-number v-model="quantities[it.item_id]" :min="0" size="small" controls-position="right" />
              </div>
            </div>
          </div>
        </template>
        <template v-if="filteredControls.length">
          <h4 class="grp-title">质控品（单独）</h4>
          <div class="entry-card-list">
            <div class="entry-card" v-for="it in filteredControls" :key="it.item_id">
              <div class="entry-card-name">
                <div>{{ it.name }} <span class="muted">{{ it.spec }}</span></div>
                <div class="card-stock">实时库存：{{ it.current_stock }} {{ it.unit }}<span v-if="it.min_stock">（最低 {{ it.min_stock }}）</span></div>
              </div>
              <div class="entry-card-input">
                <span class="muted">订购数量</span>
                <el-input-number v-model="quantities[it.item_id]" :min="0" size="small" controls-position="right" />
              </div>
            </div>
          </div>
        </template>
        <el-empty v-if="totalEntries === 0" description="该分类/检索条件下无数据" />
      </div>

      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  listReagentOrders, createReagentOrder, updateReagentOrder,
  exportOrderForm, getReagentTemplate, listAllReagentItems,
  getNextOrderNo, confirmReagentOrder,
} from '../../api/reagent'
import { useAuthStore } from '../../store/auth'
import { useReagentStore } from '../../store/reagent'
import { errText } from '../../utils/errText'
import { printHtml } from '../../utils/printHtml'
import LibraryTabs from '../../components/reagent/LibraryTabs.vue'

const auth = useAuthStore()
const reagentStore = useReagentStore()
const canWrite = computed(() => auth.canWrite('reagent-orders'))
// 编辑权限：管理员/试剂管理员可改任意；试剂配送仅能改自己创建的；已确认的不可改（后端再兜底）
function canEditRow(row) {
  if (auth.isAdmin) return true
  return !!(row.created_by && row.created_by === auth.user?.username)
}
const orders = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), editingId = ref(null), submitting = ref(false)
const dialogSearch = ref('')
const categoryFilter = ref('')
const orderForm = ref({ order_no: '', order_date: new Date().toISOString().slice(0,10), order_type: '月初订购', remark: '' })
const tpl = ref(null)
const quantities = reactive({})

async function refresh() {
  loading.value = true
  try {
    const r = await listReagentOrders({ library: reagentStore.library, page: page.value, page_size: pageSize.value })
    orders.value = r.items; total.value = r.total
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
  if ((it.name || '').toLowerCase().includes(kw)) return true
  if ((it.spec || '').toLowerCase().includes(kw)) return true
  if ((it.material_code || '').toLowerCase().includes(kw)) return true
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

async function loadTemplate() {
  const r = await getReagentTemplate({ library: reagentStore.library })
  tpl.value = r[reagentStore.library] || { by_project: [], by_instrument: [], controls: [] }
  for (const it of allItems()) if (quantities[it.item_id] == null) quantities[it.item_id] = 0
}

async function onNewOrder() {
  dialogSearch.value = ''
  categoryFilter.value = ''
  let nextNo = ''
  try { const r = await getNextOrderNo(); nextNo = r.order_no || '' } catch (_) {}
  orderForm.value = { order_no: nextNo, order_date: new Date().toISOString().slice(0,10), order_type: '月初订购', remark: '' }
  editingId.value = null
  for (const k in quantities) delete quantities[k]
  dialogVisible.value = true
  loadTemplate().catch(e => ElMessage.error('加载模板失败：' + errText(e)))
}

function onEdit(row) {
  dialogSearch.value = ''
  categoryFilter.value = ''
  editingId.value = row.id
  orderForm.value = { order_no: row.order_no, order_date: row.order_date, order_type: row.order_type, remark: row.remark || '' }
  for (const k in quantities) delete quantities[k]
  dialogVisible.value = true
  loadTemplate().then(() => {
    for (const it of (row.items || [])) quantities[it.item_id] = it.ordered_quantity || 0
  }).catch(e => ElMessage.error('加载模板失败：' + errText(e)))
}

async function onSubmit() {
  if (!orderForm.value.order_no) { ElMessage.warning('请填写订单号'); return }
  submitting.value = true
  try {
    const items = allItems()
      .filter(it => Number(quantities[it.item_id] || 0) > 0)
      .map(it => ({ item_id: it.item_id, ordered_quantity: Number(quantities[it.item_id] || 0) }))
    const data = { library: reagentStore.library, ...orderForm.value, status: '草稿', items }
    if (editingId.value) await updateReagentOrder(editingId.value, data)
    else await createReagentOrder(data)
    ElMessage.success('已保存'); dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败：' + errText(e)) } finally { submitting.value = false }
}

async function onConfirm(row) {
  try {
    await ElMessageBox.confirm(`确认提交订购单「${row.order_no}」？提交后将不可再修改。`, '确认订购单', { type: 'warning' })
    await confirmReagentOrder(row.id)
    ElMessage.success('已确认提交'); refresh()
  } catch (e) { if (e !== 'cancel') ElMessage.error('确认失败：' + errText(e)) }
}

function onExport(row) {
  exportOrderForm(row.id).then((blob) => {
    const url = window.URL.createObjectURL(new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = `设备科订购表_${row.order_no}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('已导出订购表')
  }).catch(() => ElMessage.error('导出失败'))
}

async function onPrint(row) {
  try {
    const r = await listAllReagentItems({ library: row.library || reagentStore.library })
    const nm = {}
    for (const it of r) nm[it.id] = it
    let h = '<table><thead><tr><th>材料编码</th><th>名称</th><th>规格</th><th>单位</th><th class="num">订购数量</th></tr></thead><tbody>'
    for (const it of (row.items || [])) {
      const m = nm[it.item_id] || {}
      h += `<tr><td>${m.material_code || ''}</td><td>${m.name || it.item_id}</td><td>${m.spec || ''}</td><td>${m.unit || ''}</td><td class="num">${it.ordered_quantity}</td></tr>`
    }
    h += '</tbody></table>'
    printHtml(`试剂订购表 ${row.order_no}`,
      `<h2>试剂订购表</h2><div class="meta">订单号：${row.order_no}　日期：${row.order_date}　责任库：${row.library || ''}　类型：${row.order_type}</div>${h}`)
  } catch (e) { ElMessage.error('打印失败：' + errText(e)) }
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
/* 移动端卡片式录入：名称换行 + 数量输入在右，避免横向滑动 */
.entry-card-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.entry-card { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; }
.entry-card-name { flex: 1; min-width: 0; font-size: 13px; color: #0f172a; line-height: 1.4; word-break: break-word; }
.card-stock { font-size: 12px; color: #2563eb; margin-top: 2px; }
.entry-card-input { display: flex; align-items: center; gap: 6px; white-space: nowrap; flex-shrink: 0; }
@media (max-width: 480px) {
  .entry-card { flex-direction: column; align-items: stretch; }
  .entry-card-input { justify-content: space-between; }
}
</style>
