<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">到货接收</h2>
      <p class="sub">试剂送货到货录入，记录批号/效期/数量，自动增加库存。</p>
    </div>
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewReceiving" v-if="canWrite">新增收货</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="receivings" border stripe height="calc(100vh - 340px)">
      <el-table-column type="index" width="50" />
      <el-table-column prop="receipt_no" label="收货单号" width="180" />
      <el-table-column prop="receipt_date" label="日期" width="110" />
      <el-table-column label="细项数" width="70" align="center">
        <template #default="{ row }">{{ row.items?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="delivery_person" label="送货人" width="120" />
      <el-table-column prop="receiver" label="接收人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onView(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建收货弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增收货" width="750px">
      <el-form :model="form" label-width="80px" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="收货单号"><el-input v-model="form.receipt_no" placeholder="RCV-202607-001" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="日期"><el-date-picker v-model="form.receipt_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="送货人"><el-input v-model="form.delivery_person" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <div style="margin-bottom:8px;display:flex;gap:8px">
        <el-input v-model="searchItem" placeholder="搜索试剂添加..." clearable style="width:280px" size="small" @keyup.enter="addReceivingItem" />
        <el-button @click="addReceivingItem" :icon="Plus" size="small">添加</el-button>
      </div>
      <el-table :data="items" border size="small" max-height="400">
        <el-table-column label="试剂" min-width="180">
          <template #default="{ row }">
            <el-select v-model="row.item_id" filterable placeholder="选试剂" style="width:100%">
              <el-option v-for="it in allItems" :key="it.id" :label="it.name+(it.spec?' '+it.spec:'')" :value="it.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="批号" width="130"><template #default="{row}"><el-input v-model="row.batch_no" size="small" /></template></el-table-column>
        <el-table-column label="效期" width="120"><template #default="{row}"><el-date-picker v-model="row.expiry_date" type="date" value-format="YYYY-MM-DD" size="small" style="width:100%" /></template></el-table-column>
        <el-table-column label="数量" width="80"><template #default="{row}"><el-input-number v-model="row.quantity" :min="1" size="small" style="width:80px" /></template></el-table-column>
        <el-table-column width="50"><template #default="{row,$index}"><el-button link type="danger" :icon="Delete" @click="items.splice($index,1)" /></template></el-table-column>
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
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import { listReagentReceivings, createReagentReceiving, getReagentReceiving, listReagentItems } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const receivings = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), submitting = ref(false), searchItem = ref(''), allItems = ref([])
const form = ref({ receipt_no: '', receipt_date: '', delivery_person: '', remark: '' })
const items = ref([])

async function refresh() {
  loading.value = true
  try {
    const r = await listReagentReceivings({ page: page.value, page_size: pageSize.value })
    receivings.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}
async function loadItems() {
  if (allItems.value.length) return
  const r = await listReagentItems({ page: 1, page_size: 500 })
  allItems.value = r.items
}
function onNewReceiving() {
  loadItems()
  form.value = { receipt_no: 'RCV-'+new Date().toISOString().slice(0,7)+'-001', receipt_date: new Date().toISOString().slice(0,10), delivery_person: '', remark: '' }
  items.value = []; dialogVisible.value = true
}
function addReceivingItem() {
  const kw = searchItem.value.trim().toLowerCase()
  if (!kw) return
  const hit = allItems.value.find(it => it.name.toLowerCase().includes(kw))
  if (!hit) { ElMessage.warning('未找到'); return }
  if (items.value.find(c => c.item_id === hit.id)) { ElMessage.info('已在'); return }
  items.value.push({ item_id: hit.id, batch_no: '', expiry_date: '', quantity: 1 })
  searchItem.value = ''
}
async function onSubmit() {
  if (!form.value.receipt_no) { ElMessage.warning('请填收货单号'); return }
  submitting.value = true
  try {
    await createReagentReceiving({
      ...form.value, order_id: null,
      items: items.value.filter(c => c.item_id).map(c => ({
        item_id: c.item_id, batch_no: c.batch_no || '', expiry_date: c.expiry_date || null, quantity: c.quantity || 0, remark: '',
      })),
    })
    ElMessage.success('收货成功，库存已更新')
    dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('提交失败') } finally { submitting.value = false }
}
async function onView(row) {
  try {
    const r = await getReagentReceiving(row.id)
    ElMessage.info(`收货单 ${r.receipt_no}：${(r.items||[]).length} 项`)
  } catch (e) { ElMessage.error('加载失败') }
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
