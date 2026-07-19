<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">订购管理</h2>
      <p class="sub">月初（10号前）大批量订购或加订。可导出向设备科提交的订购表（含材料编码）。</p>
    </div>
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewOrder" v-if="canWrite">新建订购</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="orders" border stripe height="calc(100vh - 340px)">
      <el-table-column type="index" width="50" />
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
      <el-table-column label="操作" width="180" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onExport(row)">导出</el-button>
          <el-button size="small" link type="primary" @click="onEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建/编辑订购弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑订购' : '新建订购'" width="750px">
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
      <div style="margin-bottom:8px;display:flex;gap:8px">
        <el-input v-model="searchItem" placeholder="搜索试剂添加..." clearable style="width:280px" size="small" @keyup.enter="addOrderItem" />
        <el-button @click="addOrderItem" :icon="Plus" size="small">添加</el-button>
      </div>
      <el-table :data="orderItems" border size="small" max-height="400">
        <el-table-column label="试剂" min-width="180">
          <template #default="{ row, $index }">
            <el-select v-model="row.item_id" filterable placeholder="选试剂" style="width:100%">
              <el-option v-for="it in allItems" :key="it.id" :label="it.name + (it.spec ? ' '+it.spec : '')" :value="it.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="材料编码" width="110">
          <template #default="{ row }">{{ row._material_code }}</template>
        </el-table-column>
        <el-table-column label="订购数量" width="100">
          <template #default="{ row }"><el-input-number v-model="row.ordered_quantity" :min="0" size="small" style="width:90px" /></template>
        </el-table-column>
        <el-table-column width="50">
          <template #default="{ $index }"><el-button link type="danger" :icon="Delete" @click="orderItems.splice($index,1)" /></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import { listReagentOrders, createReagentOrder, updateReagentOrder, deleteReagentOrder, listReagentItems, exportOrderForm } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const orders = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), editingId = ref(null), submitting = ref(false)
const searchItem = ref(''), allItems = ref([])
const orderForm = ref({ order_no: '', order_date: new Date().toISOString().slice(0,10), order_type: '月初订购', remark: '' })
const orderItems = ref([])
const itemMap = ref({})

async function refresh() {
  loading.value = true
  try {
    const r = await listReagentOrders({ page: page.value, page_size: pageSize.value })
    orders.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}
async function loadItems() {
  if (allItems.value.length) return
  const r = await listReagentItems({ page: 1, page_size: 500 })
  allItems.value = r.items
  for (const it of r.items) itemMap.value[it.id] = it
}
function onNewOrder() {
  loadItems(); editingId.value = null
  orderForm.value = { order_no: 'ORD-'+new Date().toISOString().slice(0,7)+'-001', order_date: new Date().toISOString().slice(0,10), order_type: '月初订购', remark: '' }
  orderItems.value = []; dialogVisible.value = true
}
function addOrderItem() {
  const kw = searchItem.value.trim().toLowerCase()
  if (!kw) return
  const hit = allItems.value.find(it => it.name.toLowerCase().includes(kw))
  if (!hit) { ElMessage.warning('未找到'); return }
  if (orderItems.value.find(c => c.item_id === hit.id)) { ElMessage.info('已在'); return }
  orderItems.value.push({ item_id: hit.id, ordered_quantity: 0, unit_price: null, remark: '', _material_code: hit.material_code })
  searchItem.value = ''
}
function onEdit(row) {
  loadItems(); editingId.value = row.id
  orderForm.value = { order_no: row.order_no, order_date: row.order_date, order_type: row.order_type, remark: row.remark || '' }
  orderItems.value = (row.items || []).map(it => ({
    item_id: it.item_id, ordered_quantity: it.ordered_quantity, unit_price: it.unit_price, remark: it.remark || '',
    _material_code: itemMap.value[it.item_id]?.material_code || '',
  }))
  dialogVisible.value = true
}
async function onSubmit() {
  if (!orderForm.value.order_no) { ElMessage.warning('请填订单号'); return }
  submitting.value = true
  try {
    const data = { ...orderForm.value, status: '草稿', items: orderItems.value.filter(c => c.item_id).map(c => ({ item_id: c.item_id, ordered_quantity: c.ordered_quantity, unit_price: c.unit_price, remark: c.remark })) }
    if (editingId.value) { await updateReagentOrder(editingId.value, data) }
    else { await createReagentOrder(data) }
    ElMessage.success('已保存'); dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败') } finally { submitting.value = false }
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除订单「${row.order_no}」？`,'提示',{type:'warning'})
  await deleteReagentOrder(row.id); ElMessage.success('已删除'); refresh()
}
function onExport(row) {
  // 导出设备科订购表
  ElMessage.success('导出功能正在实现')
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
</style>
