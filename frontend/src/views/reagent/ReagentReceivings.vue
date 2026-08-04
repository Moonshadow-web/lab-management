<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">到货接收</h2>
      <p class="sub">试剂送货到货录入，确认接收后才会进入实时库存。接收人默认为当前登录人员。</p>
    </div>
    <LibraryTabs @change="refresh" />
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewReceiving" v-if="canWrite">新增收货</el-button>
      <el-radio-group v-model="confirmedFilter" @change="refresh" size="small">
        <el-radio-button label="全部" value="" />
        <el-radio-button label="待确认" value="false" />
        <el-radio-button label="已确认" value="true" />
      </el-radio-group>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="receivings" border stripe height="calc(100vh - 360px)">
      <el-table-column type="index" width="50" />
      <el-table-column prop="receipt_no" label="收货单号" width="180" />
      <el-table-column prop="receipt_date" label="日期" width="110" />
      <el-table-column label="细项数" width="70" align="center">
        <template #default="{ row }">{{ row.items?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="delivery_person" label="送货人" width="100" />
      <el-table-column prop="receiver" label="接收人" width="100" />
      <el-table-column prop="created_by" label="创建人" width="100" />
      <el-table-column label="状态" width="160">
        <template #default="{ row }">
          <el-tag :type="row.is_confirmed ? 'success' : 'warning'" size="small">
            {{ row.is_confirmed ? '已确认' : '待确认' }}
          </el-tag>
          <div v-if="row.is_confirmed" class="sub-text">
            {{ row.confirmed_by }} · {{ fmt(row.confirmed_at) }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onView(row)">详情</el-button>
          <el-button size="small" link type="success" @click="onConfirm(row)"
            v-if="!row.is_confirmed" :disabled="!canConfirm(row)">确认接收</el-button>
          <el-button size="small" link type="warning" @click="onEdit(row)"
            v-if="canEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)"
            v-if="auth.isAdmin">删除</el-button>
          <el-button size="small" link type="info" @click="onPrint(row)">打印</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建/编辑收货弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑收货' : '新增收货'" width="820px">
      <el-form :model="form" label-width="80px" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="收货单号"><el-input v-model="form.receipt_no" placeholder="RCV-202607-001" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="日期"><el-date-picker v-model="form.receipt_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="送货人"><el-input v-model="form.delivery_person" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="接收人"><el-input v-model="form.receiver" placeholder="确认接收时自动填入当前登录人" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
        <span class="label">搜索添加试剂：</span>
        <el-select v-model="searchSel" filterable remote :remote-method="onSearchItem" :loading="searching"
          placeholder="输入名称/品牌/编码模糊搜索" style="flex:1" value-key="id" clearable
          @change="onPickItem">
          <el-option v-for="o in searchResults" :key="o.id" :label="o.name + (o.spec ? ' ' + o.spec : '')" :value="o.id" />
        </el-select>
        <span class="hint">（模糊搜索后点选即可加入下方明细）</span>
      </div>
      <el-table :data="items" border size="small" max-height="360">
        <el-table-column label="试剂" min-width="200">
          <template #default="{ row }">
            <el-select v-model="row.item_id" filterable placeholder="选试剂" style="width:100%">
              <el-option v-for="it in allItems" :key="it.id" :label="it.name+(it.spec?' '+it.spec:'')" :value="it.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="批号" width="130"><template #default="{row}"><el-input v-model="row.batch_no" size="small" /></template></el-table-column>
        <el-table-column label="效期" width="120"><template #default="{row}"><el-date-picker v-model="row.expiry_date" type="date" value-format="YYYY-MM-DD" size="small" style="width:100%" /></template></el-table-column>
        <el-table-column label="数量" width="90"><template #default="{row}"><el-input-number v-model="row.quantity" :min="1" size="small" style="width:90px" /></template></el-table-column>
        <el-table-column width="50"><template #default="{row,$index}"><el-button link type="danger" :icon="Delete" @click="items.splice($index,1)" /></template></el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 打印收货单 -->
    <el-dialog v-model="printVisible" title="收货单打印预览" width="720px" class="no-print-dialog">
      <div id="print-area" class="receipt">
        <h2 class="receipt-title">试剂到货接收单</h2>
        <table class="receipt-head">
          <tr>
            <td>收货单号：{{ printData.receipt_no }}</td>
            <td>日期：{{ printData.receipt_date }}</td>
          </tr>
          <tr>
            <td>送货人：{{ printData.delivery_person || '—' }}</td>
            <td>接收人：{{ printData.receiver || '—' }}</td>
          </tr>
          <tr>
            <td>状态：{{ printData.is_confirmed ? '已确认' : '待确认' }}</td>
            <td>创建人：{{ printData.created_by || '—' }}</td>
          </tr>
          <tr v-if="printData.is_confirmed">
            <td colspan="2">确认：{{ printData.confirmed_by }} · {{ fmt(printData.confirmed_at) }}</td>
          </tr>
          <tr>
            <td colspan="2">备注：{{ printData.remark || '—' }}</td>
          </tr>
        </table>
        <table class="receipt-items">
          <thead>
            <tr><th>序号</th><th>试剂名称</th><th>批号</th><th>效期</th><th>数量</th></tr>
          </thead>
          <tbody>
            <tr v-for="(it, i) in printData.items || []" :key="it.id">
              <td>{{ i + 1 }}</td>
              <td>{{ itemName(it.item_id) }}</td>
              <td>{{ it.batch_no || '—' }}</td>
              <td>{{ it.expiry_date || '—' }}</td>
              <td>{{ it.quantity }}</td>
            </tr>
          </tbody>
        </table>
        <div class="receipt-foot">
          <span>收货人签字：________________</span>
          <span>日期：______年____月____日</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="printVisible=false">关闭</el-button>
        <el-button type="primary" :icon="Printer" @click="doPrint">打印</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete, Printer } from '@element-plus/icons-vue'
import {
  listReagentReceivings, createReagentReceiving, getReagentReceiving,
  updateReagentReceiving, confirmReagentReceiving, deleteReagentReceiving, listAllReagentItems, listReagentItems,
} from '../../api/reagent'
import { useAuthStore } from '../../store/auth'
import { useReagentStore } from '../../store/reagent'
import { errText } from '../../utils/errText'
import LibraryTabs from '../../components/reagent/LibraryTabs.vue'

const auth = useAuthStore()
const reagentStore = useReagentStore()
const canWrite = computed(() => auth.canWrite('reagent-receivings'))
const currentUser = computed(() => auth.user?.username || '')

const receivings = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const confirmedFilter = ref('')
const dialogVisible = ref(false), submitting = ref(false), editingId = ref(null)
const allItems = ref([]), searchSel = ref(''), searchResults = ref([]), searching = ref(false)
const form = ref({ receipt_no: '', receipt_date: '', delivery_person: '', receiver: '', remark: '' })
const items = ref([])
const printVisible = ref(false), printData = ref({})

function fmt(v) {
  if (!v) return ''
  return String(v).slice(0, 16).replace('T', ' ')
}
function itemName(id) {
  const it = allItems.value.find(x => x.id === id) || searchResults.value.find(x => x.id === id)
  return it ? (it.name + (it.spec ? ' ' + it.spec : '')) : ('ID#' + id)
}

async function refresh() {
  loading.value = true
  try {
    const params = { library: reagentStore.library, page: page.value, page_size: pageSize.value }
    if (confirmedFilter.value !== '') params.confirmed = confirmedFilter.value === 'true'
    const r = await listReagentReceivings(params)
    receivings.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) } finally { loading.value = false }
}
async function loadItems() {
  if (allItems.value.length) return
  const all = await listAllReagentItems({ library: reagentStore.library })
  allItems.value = all
}
function onNewReceiving() {
  loadItems()
  editingId.value = null
  form.value = {
    receipt_no: 'RCV-' + new Date().toISOString().slice(0, 7) + '-' + String(Date.now()).slice(-3),
    receipt_date: new Date().toISOString().slice(0, 10),
    delivery_person: '',     receiver: '', remark: '',
  }
  items.value = []; searchResults.value = []; searchSel.value = ''
  dialogVisible.value = true
}
async function onEdit(row) {
  try {
    const r = await getReagentReceiving(row.id)
    editingId.value = row.id
    form.value = {
      receipt_no: r.receipt_no, receipt_date: r.receipt_date,
      delivery_person: r.delivery_person, receiver: r.receiver, remark: r.remark,
    }
    items.value = (r.items || []).map(it => ({
      item_id: it.item_id, batch_no: it.batch_no, expiry_date: it.expiry_date, quantity: it.quantity,
    }))
    await loadItems()
    dialogVisible.value = true
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) }
}
async function onSearchItem(query) {
  const q = (query || '').trim()
  if (!q) { searchResults.value = []; return }
  searching.value = true
  try {
    const r = await listReagentItems({ q, library: reagentStore.library, show_inactive: true, page_size: 20 })
    searchResults.value = r.items || []
  } catch (_) { searchResults.value = [] } finally { searching.value = false }
}
function onPickItem(id) {
  if (!id) return
  const hit = searchResults.value.find(o => o.id === id)
  if (!hit) return
  if (items.value.find(c => c.item_id === id)) { ElMessage.info('已在明细中'); searchSel.value = ''; return }
  items.value.push({ item_id: id, batch_no: '', expiry_date: '', quantity: 1 })
  searchSel.value = ''
}
async function onSubmit() {
  if (!form.value.receipt_no) { ElMessage.warning('请填收货单号'); return }
  if (!items.value.length) { ElMessage.warning('请至少添加一项试剂'); return }
  submitting.value = true
  const payload = {
    ...form.value, order_id: null,
    items: items.value.filter(c => c.item_id).map(c => ({
      item_id: c.item_id, batch_no: c.batch_no || '', expiry_date: c.expiry_date || null, quantity: c.quantity || 0, remark: '',
    })),
  }
  try {
    if (editingId.value) {
      await updateReagentReceiving(editingId.value, payload)
      ElMessage.success('已保存修改')
    } else {
      await createReagentReceiving(payload)
      ElMessage.success('收货单已保存（待确认接收后入库）')
    }
    dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('提交失败：' + errText(e)) } finally { submitting.value = false }
}
async function onConfirm(row) {
  try {
    await ElMessageBox.confirm(`确认接收「${row.receipt_no}」？确认后试剂将进入实时库存。`, '确认接收', { type: 'warning' })
  } catch (_) { return }
  try {
    await confirmReagentReceiving(row.id)
    ElMessage.success('已确认接收，库存已更新')
    refresh()
  } catch (e) { ElMessage.error('确认失败：' + errText(e)) }
}
async function onView(row) {
  try {
    const r = await getReagentReceiving(row.id)
    const lines = (r.items || []).map((it, i) => `${i + 1}. ${itemName(it.item_id)} 批号:${it.batch_no || '—'} 效期:${it.expiry_date || '—'} 数量:${it.quantity}`).join('\n')
    ElMessage.info(`收货单 ${r.receipt_no}（${r.is_confirmed ? '已确认' : '待确认'}）\n${lines || '无明细'}`)
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) }
}
async function onPrint(row) {
  try {
    const r = await getReagentReceiving(row.id)
    printData.value = r
    await loadItems()
    printVisible.value = true
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) }
}
function doPrint() { window.print() }

// 管理员删除收货单（已确认的会回退库存）
async function onDelete(row) {
  if (!auth.isAdmin) return
  try {
    await ElMessageBox.confirm(
      `确认删除收货单「${row.receipt_no}」？${row.is_confirmed ? '该单已确认，删除后将回退对应库存。' : ''}此操作不可恢复。`,
      '删除收货单', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (_) { return }
  try {
    await deleteReagentReceiving(row.id)
    ElMessage.success(`收货单 ${row.receipt_no} 已删除`)
    refresh()
  } catch (e) { ElMessage.error('删除失败：' + errText(e)) }
}

// 权限判定：试剂配送仅能改自己建的、且未确认的；管理员/试剂管理员可改任意未确认
function canEdit(row) {
  if (!canWrite.value) return false
  if (row.is_confirmed) return false
  if (auth.isAdmin) return true
  const roles = auth.myRoles
  if (roles.includes('reagent_manager')) return true
  // 试剂配送：仅本人
  return row.created_by === currentUser.value
}
function canConfirm() {
  if (auth.isAdmin) return true
  return auth.myRoles.includes('reagent_manager')
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
.sub-text { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.label { font-size: 13px; color: #475569; }
.hint { font-size: 11px; color: #94a3b8; }
.receipt { padding: 8px 4px; }
.receipt-title { text-align: center; font-size: 18px; margin: 0 0 12px; }
.receipt-head { width: 100%; border-collapse: collapse; font-size: 13px; }
.receipt-head td { padding: 6px 4px; }
.receipt-items { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
.receipt-items th, .receipt-items td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }
.receipt-items th { background: #f1f5f9; }
.receipt-foot { display: flex; justify-content: space-between; margin-top: 24px; font-size: 13px; }
</style>
<style>
@media print {
  body * { visibility: hidden; }
  #print-area, #print-area * { visibility: visible; }
  #print-area { position: absolute; left: 0; top: 0; width: 100%; padding: 0 12px; }
  .no-print-dialog .el-dialog__header,
  .no-print-dialog .el-dialog__footer { display: none !important; }
}
</style>
