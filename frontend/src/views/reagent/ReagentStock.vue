<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">实时库存</h2>
      <p class="sub">当前库存余额（按试剂+批号+效期明细），低于预警值的标红提醒。</p>
    </div>
    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索试剂名称..." clearable style="width:250px" @keyup.enter="refresh" @clear="refresh">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filterType" placeholder="全部类型" clearable style="width:130px" @change="refresh">
        <el-option v-for="t in types" :key="t" :label="t" :value="t" />
      </el-select>
      <el-checkbox v-model="lowOnly" label="仅看预警" border @change="refresh" />
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe height="calc(100vh - 340px)">
      <el-table-column type="index" width="50" />
      <el-table-column label="试剂名称" min-width="180">
        <template #default="{ row }">
          <span :style="{ color: row._low_stock ? '#e74c3c' : 'inherit', fontWeight: row._low_stock ? 700 : 400 }">
            {{ row._item_name || '-' }}
            <el-tag v-if="row._low_stock" size="small" type="danger" style="margin-left:6px">预警</el-tag>
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="batch_no" label="批号" width="160" />
      <el-table-column prop="expiry_date" label="效期" width="110" />
      <el-table-column prop="quantity" label="数量" width="80" align="center" />
      <el-table-column prop="last_updated" label="最后更新" width="170">
        <template #default="{ row }">{{ row.last_updated ? new Date(row.last_updated).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50,100]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { listReagentStock } from '../../api/reagent'
import { listReagentItems } from '../../api/reagent'

const items = ref([]), total = ref(0), page = ref(1), pageSize = ref(50), loading = ref(false)
const q = ref(''), filterType = ref(''), lowOnly = ref(false)
const types = ['试剂','校准品','质控品','耗材']
const itemMap = ref({})

async function refresh() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (q.value.trim()) params.q = q.value.trim()
    if (filterType.value) params.type = filterType.value
    if (lowOnly.value) params.low_stock_only = true
    const r = await listReagentStock(params)
    // 映射 item_id → item name 和 min_stock
    if (Object.keys(itemMap.value).length === 0) {
      const ri = await listReagentItems({ page: 1, page_size: 500 })
      for (const it of ri.items) itemMap.value[it.id] = it
    }
    for (const s of r.items) {
      const it = itemMap.value[s.item_id]
      s._item_name = it?.name || `(id=${s.item_id})`
      s._low_stock = it && s.quantity < it.min_stock
    }
    items.value = r.items; total.value = r.total
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally { loading.value = false }
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
