<template>
  <div class="audit-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <el-button size="small" :icon="Refresh" @click="loadData">刷新</el-button>
        </div>
      </template>

      <!-- 筛选 -->
      <div class="filters">
        <el-select v-model="filters.action" placeholder="操作类型" clearable size="small" style="width: 140px" @change="loadData">
          <el-option v-for="a in actions" :key="a" :label="actionLabel(a)" :value="a" />
        </el-select>
        <el-select v-model="filters.table_name" placeholder="数据表" clearable size="small" style="width: 160px" @change="loadData">
          <el-option v-for="t in tables" :key="t" :label="t" :value="t" />
        </el-select>
        <el-input v-model="filters.user_id" placeholder="用户ID" clearable size="small" style="width: 100px" @change="loadData" />
        <el-date-picker v-model="dateRange" type="daterange" range-separator="—" start-placeholder="开始" end-placeholder="结束" size="small" style="width: 260px" value-format="YYYY-MM-DD" @change="onDateChange" />
      </div>

      <!-- 表格 -->
      <el-table :data="logs" v-loading="loading" stripe size="small" style="margin-top: 12px">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column prop="user_name" label="操作人" width="90" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="table_name" label="数据表" width="120" />
        <el-table-column prop="record_id" label="记录ID" width="70" />
        <el-table-column prop="ip" label="IP" width="110" />
        <el-table-column prop="detail" label="详情" show-overflow-tooltip />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="loadData"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { listAuditLogs, listActions, listTables } from '../../api/audit'

const logs = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const actions = ref([])
const tables = ref([])
const dateRange = ref([])
const filters = ref({ action: '', table_name: '', user_id: '', start_date: '', end_date: '' })

const ACTION_LABELS = {
  create: '新增', update: '修改', delete: '删除',
  login: '登录', login_failed: '登录失败', login_blocked: '登录被拒', login_locked: '账号锁定',
}

function actionLabel(a) {
  return ACTION_LABELS[a] || a
}

function actionTagType(a) {
  if (a === 'create') return 'success'
  if (a === 'update') return 'warning'
  if (a === 'delete') return 'danger'
  if (a === 'login') return ''
  if (a.startsWith('login_') || a === 'login_locked') return 'danger'
  return 'info'
}

function onDateChange(val) {
  filters.value.start_date = val ? val[0] : ''
  filters.value.end_date = val ? val[1] : ''
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.table_name) params.table_name = filters.value.table_name
    if (filters.value.user_id) params.user_id = filters.value.user_id
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await listAuditLogs(params)
    logs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try { actions.value = await listActions() } catch {}
  try { tables.value = await listTables() } catch {}
  await loadData()
})
</script>

<style scoped>
.audit-page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
</style>
