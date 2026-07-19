<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">盘库管理</h2>
      <p class="sub">月末/月中盘库操作。新建盘库时录入试剂余量，自动更新实时库存。</p>
    </div>
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="onNewCheck" v-if="canWrite">新建盘库</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="checks" border stripe height="calc(100vh - 340px)">
      <el-table-column type="index" width="50" />
      <el-table-column prop="check_date" label="盘库日期" width="120" />
      <el-table-column prop="check_type" label="类型" width="100" />
      <el-table-column prop="operator" label="操作人" width="120" />
      <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onView(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新建盘库弹窗 -->
    <el-dialog v-model="dialogVisible" title="新建盘库" width="750px">
      <el-form :model="checkForm" label-width="80px" size="small">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="日期"><el-date-picker v-model="checkForm.check_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类型"><el-select v-model="checkForm.check_type" style="width:100%">
            <el-option label="月末盘库" value="月末盘库" /><el-option label="月中盘库" value="月中盘库" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="备注"><el-input v-model="checkForm.remark" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <div style="margin-bottom:8px;display:flex;gap:8px">
        <el-input v-model="searchItem" placeholder="搜索试剂添加..." clearable style="width:280px" @keyup.enter="addSearchItem" />
        <el-button @click="addSearchItem" :icon="Plus" size="small">添加</el-button>
        <el-button @click="addAllActive" size="small">添加全部在用</el-button>
      </div>
      <el-table :data="checkItems" border size="small" max-height="400">
        <el-table-column label="试剂" min-width="180">
          <template #default="{ row, $index }">
            <el-select v-model="row.item_id" filterable placeholder="选试剂" style="width:100%" @change="onItemSelect(row)">
              <el-option v-for="it in allItems" :key="it.id" :label="it.name" :value="it.id">
                <span>{{ it.name }}</span><span style="color:#94a3b8;margin-left:8px">{{ it.spec }}</span>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="批号" width="130">
          <template #default="{ row }"><el-input v-model="row.batch_no" size="small" /></template>
        </el-table-column>
        <el-table-column label="效期" width="120">
          <template #default="{ row }"><el-date-picker v-model="row.expiry_date" type="date" value-format="YYYY-MM-DD" size="small" style="width:100%" /></template>
        </el-table-column>
        <el-table-column label="余量" width="80">
          <template #default="{ row }"><el-input-number v-model="row.recorded_quantity" :min="0" size="small" style="width:80px" /></template>
        </el-table-column>
        <el-table-column width="50">
          <template #default="{ $index }"><el-button link type="danger" :icon="Delete" @click="checkItems.splice($index,1)" /></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交盘库</el-button>
      </template>
    </el-dialog>

    <!-- 查看盘库详情 -->
    <el-dialog v-model="viewVisible" title="盘库详情" width="600px">
      <el-table :data="viewItems" border size="small">
        <el-table-column prop="item_id" label="试剂ID" width="70" />
        <el-table-column prop="batch_no" label="批号" width="130" />
        <el-table-column prop="expiry_date" label="效期" width="110" />
        <el-table-column prop="recorded_quantity" label="余量" width="70" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import { listInventoryChecks, getInventoryCheck, createInventoryCheck, listReagentItems } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const checks = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const dialogVisible = ref(false), submitting = ref(false)
const searchItem = ref(''), allItems = ref([])
const checkForm = ref({ check_date: '', check_type: '月末盘库', remark: '' })
const checkItems = ref([])
const viewVisible = ref(false), viewItems = ref([])

async function refresh() {
  loading.value = true
  try {
    const r = await listInventoryChecks({ page: page.value, page_size: pageSize.value })
    checks.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}
async function loadAllItems() {
  if (allItems.value.length) return
  const r = await listReagentItems({ page: 1, page_size: 500 })
  allItems.value = r.items
}
function onNewCheck() {
  loadAllItems()
  checkForm.value = { check_date: new Date().toISOString().slice(0,10), check_type: '月末盘库', remark: '' }
  checkItems.value = []; dialogVisible.value = true
}
function addSearchItem() {
  const kw = searchItem.value.trim().toLowerCase()
  if (!kw) return
  const hit = allItems.value.find(it => it.name.toLowerCase().includes(kw) && it.is_active)
  if (!hit) { ElMessage.warning('未找到匹配的试剂'); return }
  if (checkItems.value.find(c => c.item_id === hit.id)) { ElMessage.info('已在列表中'); return }
  checkItems.value.push({ item_id: hit.id, batch_no: '', expiry_date: '', recorded_quantity: 0 })
  searchItem.value = ''
}
function addAllActive() {
  loadAllItems()
  const existing = new Set(checkItems.value.map(c => c.item_id))
  for (const it of allItems.value) {
    if (it.is_active && !existing.has(it.id)) {
      checkItems.value.push({ item_id: it.id, batch_no: '', expiry_date: '', recorded_quantity: 0 })
    }
  }
}
function onItemSelect(row) {
  // 可选：自动填充批号/效期
}
async function onSubmit() {
  if (!checkForm.value.check_date) { ElMessage.warning('请选日期'); return }
  submitting.value = true
  try {
    await createInventoryCheck({
      ...checkForm.value,
      items: checkItems.value.filter(c => c.item_id).map(c => ({
        item_id: c.item_id, batch_no: c.batch_no || '',
        expiry_date: c.expiry_date || null, recorded_quantity: c.recorded_quantity || 0,
      })),
    })
    ElMessage.success('盘库成功，库存已更新')
    dialogVisible.value = false; refresh()
  } catch (e) { ElMessage.error('盘库失败') } finally { submitting.value = false }
}
async function onView(row) {
  try {
    const r = await getInventoryCheck(row.id)
    viewItems.value = r.items || []; viewVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败') }
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
