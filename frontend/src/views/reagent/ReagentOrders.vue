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
      <el-table-column label="操作" width="200" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onExport(row)">导出</el-button>
          <el-button size="small" link type="primary" @click="onPrint(row)">打印</el-button>
          <el-button size="small" link type="primary" @click="onEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建/编辑订购弹窗 -->
    <el-dialog v-model="dialogVisible" :title="(editingId ? '编辑订购' : '新建订购') + `（${reagentStore.library}）`" width="960px" top="3vh">
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
      <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
        <el-input v-model="dialogSearch" placeholder="模糊检索试剂/规格/编码..." clearable style="width:280px" />
        <span class="muted" style="font-size:12px">共 {{ totalEntries }} 项</span>
      </div>

      <div class="entry-scroll">
        <template v-for="grp in filteredProjects" :key="'p'+grp.test_item_id">
          <h4 class="grp-title">项目：{{ grp.test_item_name }}</h4>
          <el-table :data="grp.items" border size="small">
            <el-table-column label="试剂 / 校准品" min-width="200">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }}</span></template>
            </el-table-column>
            <el-table-column label="材料编码" width="110"><template #default="{ row }">{{ row.material_code || '-' }}</template></el-table-column>
            <el-table-column label="单位" width="70"><template #default="{ row }">{{ row.unit || '-' }}</template></el-table-column>
            <el-table-column label="当前库存" width="90" align="center"><template #default="{ row }">{{ row.current_stock }}</template></el-table-column>
            <el-table-column label="订购数量" width="130">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:120px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <template v-for="grp in filteredInstruments" :key="'i'+grp.group">
          <h4 class="grp-title">仪器：{{ grp.group }} <span class="muted" v-if="grp.instruments.length">（{{ grp.instruments.join('、') }}）</span></h4>
          <el-table :data="grp.items" border size="small">
            <el-table-column label="耗材" min-width="200">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }}</span></template>
            </el-table-column>
            <el-table-column label="材料编码" width="110"><template #default="{ row }">{{ row.material_code || '-' }}</template></el-table-column>
            <el-table-column label="单位" width="70"><template #default="{ row }">{{ row.unit || '-' }}</template></el-table-column>
            <el-table-column label="当前库存" width="90" align="center"><template #default="{ row }">{{ row.current_stock }}</template></el-table-column>
            <el-table-column label="订购数量" width="130">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:120px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <template v-if="filteredControls.length">
          <h4 class="grp-title">质控品（单独）</h4>
          <el-table :data="filteredControls" border size="small">
            <el-table-column label="质控品" min-width="200">
              <template #default="{ row }">{{ row.name }} <span class="muted">{{ row.spec }}</span></template>
            </el-table-column>
            <el-table-column label="材料编码" width="110"><template #default="{ row }">{{ row.material_code || '-' }}</template></el-table-column>
            <el-table-column label="单位" width="70"><template #default="{ row }">{{ row.unit || '-' }}</template></el-table-column>
            <el-table-column label="当前库存" width="90" align="center"><template #default="{ row }">{{ row.current_stock }}</template></el-table-column>
            <el-table-column label="订购数量" width="130">
              <template #default="{ row }">
                <el-input-number v-model="quantities[row.item_id]" :min="0" size="small" style="width:120px" controls-position="right" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-if="totalEntries === 0" description="该责任库暂无试剂/耗材（请先在试剂目录维护）" />
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
  listReagentOrders, createReagentOrder, updateReagentOrder, deleteReagentOrder,
  exportOrderForm, getReagentTemplate, listAllReagentItems,
} from '../../api/reagent'
import { useAuthStore } from '../../store/auth'
import { useReagentStore } from '../../store/reagent'
import { errText } from '../../utils/errText'
import { printHtml } from '../../utils/printHtml'
import LibraryTabs from '../../components/reagent/LibraryTabs.vue'

const auth = useAuthStore()
const reagentStore = useReagentStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const orders = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), editingId = ref(null), submitting = ref(false)
const dialogSearch = ref('')
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
const totalEntries = computed(() => allItems().length)

function matchItem(it) {
  const kw = dialogSearch.value.trim().toLowerCase()
  if (!kw) return true
  return (it.name || '').toLowerCase().includes(kw)
    || (it.spec || '').toLowerCase().includes(kw)
    || (it.material_code || '').toLowerCase().includes(kw)
}
const filteredProjects = computed(() => tpl.value ? tpl.value.by_project.map(g => ({ ...g, items: g.items.filter(matchItem) })).filter(g => g.items.length) : [])
const filteredInstruments = computed(() => tpl.value ? tpl.value.by_instrument.map(g => ({ ...g, items: g.items.filter(matchItem) })).filter(g => g.items.length) : [])
const filteredControls = computed(() => tpl.value ? tpl.value.controls.filter(matchItem) : [])

async function loadTemplate() {
  const r = await getReagentTemplate({ library: reagentStore.library })
  tpl.value = r[reagentStore.library] || { by_project: [], by_instrument: [], controls: [] }
  for (const it of allItems()) if (quantities[it.item_id] == null) quantities[it.item_id] = 0
}

function onNewOrder() {
  dialogSearch.value = ''
  orderForm.value = { order_no: 'ORD-' + new Date().toISOString().slice(0,7) + '-001', order_date: new Date().toISOString().slice(0,10), order_type: '月初订购', remark: '' }
  editingId.value = null
  for (const k in quantities) delete quantities[k]
  dialogVisible.value = true
  loadTemplate().catch(e => ElMessage.error('加载模板失败：' + errText(e)))
}

function onEdit(row) {
  dialogSearch.value = ''
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

async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除订单「${row.order_no}」？`, '提示', { type: 'warning' })
  await deleteReagentOrder(row.id); ElMessage.success('已删除'); refresh()
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
</style>
