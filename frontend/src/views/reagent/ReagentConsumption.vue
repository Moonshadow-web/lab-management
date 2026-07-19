<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">月消耗统计</h2>
      <p class="sub">月末盘库后计算各试剂月消耗量（= 上期结余 + 本期入库 - 期末结余），用于填写设备处物流出库记录。</p>
    </div>
    <div class="toolbar">
      <el-date-picker v-model="month" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="refresh" />
      <el-button type="primary" :loading="calculating" @click="onCalculate" v-if="canWrite">计算月消耗</el-button>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe height="calc(100vh - 340px)">
      <el-table-column type="index" width="50" />
      <el-table-column label="试剂" min-width="180">
        <template #default="{ row }">{{ row._item_name || `(id=${row.item_id})` }}</template>
      </el-table-column>
      <el-table-column prop="year_month" label="年月" width="90" />
      <el-table-column prop="opening_balance" label="期初库存" width="100" align="center" />
      <el-table-column prop="total_received" label="本月入库" width="100" align="center" />
      <el-table-column prop="closing_balance" label="期末库存" width="100" align="center" />
      <el-table-column prop="consumption" label="月消耗" width="90" align="center">
        <template #default="{ row }">
          <span style="font-weight:700;color:#0f766e">{{ row.consumption }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="calculated_at" label="计算时间" width="170">
        <template #default="{ row }">{{ row.calculated_at ? new Date(row.calculated_at).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50,100]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { listReagentConsumption, calculateConsumption, listReagentItems } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const items = ref([]), total = ref(0), page = ref(1), pageSize = ref(50), loading = ref(false)
const month = ref(new Date().toISOString().slice(0,7)), calculating = ref(false)
const itemMap = ref({})

async function refresh() {
  loading.value = true
  try {
    const params = { year_month: month.value || '', page: page.value, page_size: pageSize.value }
    const r = await listReagentConsumption(params)
    if (Object.keys(itemMap.value).length === 0) {
      const ri = await listReagentItems({ page: 1, page_size: 500 })
      for (const it of ri.items) itemMap.value[it.id] = it.name
    }
    for (const c of r.items) c._item_name = itemMap.value[c.item_id] || ''
    items.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}
async function onCalculate() {
  if (!month.value) { ElMessage.warning('请选择月份'); return }
  calculating.value = true
  try {
    const r = await calculateConsumption(month.value)
    ElMessage.success(`已计算 ${r.year_month}，新增 ${r.added} 条`)
    refresh()
  } catch (e) { ElMessage.error('计算失败') } finally { calculating.value = false }
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
