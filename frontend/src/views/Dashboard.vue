<template>
  <div class="dashboard">
    <el-row :gutter="16">
      <el-col :span="6">
        <AppCard title="检验项目">
          <div class="stat"><span class="num">{{ stats.testItems }}</span><span class="unit">项</span></div>
          <div class="stat-sub">生化免疫检验项目</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="仪器设备">
          <div class="stat"><span class="num">{{ stats.instruments }}</span><span class="unit">台</span></div>
          <div class="stat-sub">在用 / 停用台账</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="体系文件">
          <div class="stat"><span class="num">{{ stats.documents }}</span><span class="unit">份</span></div>
          <div class="stat-sub">SOP / 记录表格</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="待办提醒">
          <div class="stat"><span class="num" :class="{ warn: stats.notifications > 0 }">{{ stats.notifications }}</span><span class="unit">条</span></div>
          <div class="stat-sub">校准 / 质控提醒</div>
        </AppCard>
      </el-col>
    </el-row>

    <AppCard title="提醒事项" class="mt">
      <template #header-extra>
        <el-button v-if="notices.length" size="small" @click="onReadAll">全部已读</el-button>
      </template>
      <el-empty v-if="!notices.length" description="暂无提醒" />
      <el-table v-else :data="notices" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="message" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="due_date" label="到期日" width="130" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button v-if="!row.is_read" link type="primary" @click="onRead(row)">标记已读</el-button>
            <el-tag v-else type="success" size="small">已读</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AppCard from '../components/AppCard.vue'
import { listTestItems } from '../api/testItems'
import { listInstruments } from '../api/instruments'
import { listDocuments } from '../api/documents'
import { listNotifications, markRead, markAllRead } from '../api/notifications'

const stats = ref({ testItems: '-', instruments: '-', documents: '-', notifications: '-' })
const notices = ref([])

function levelType(level) {
  if (level === 'danger') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

async function loadStats() {
  try {
    const [ti, ins, docs, notis] = await Promise.all([
      listTestItems({ page: 1, page_size: 1 }),
      listInstruments({ page: 1, page_size: 1 }),
      listDocuments({ page: 1, page_size: 1 }),
      listNotifications({ page: 1, page_size: 1, unread_only: true }),
    ])
    stats.value = {
      testItems: ti.total,
      instruments: ins.total,
      documents: docs.total,
      notifications: notis.total,
    }
  } catch (e) {
    // 忽略
  }
}

async function loadNotices() {
  try {
    const res = await listNotifications({ page: 1, page_size: 50 })
    notices.value = res.items || []
  } catch (e) {
    notices.value = []
  }
}

async function onRead(row) {
  await markRead(row.id)
  row.is_read = true
  loadStats()
}
async function onReadAll() {
  await markAllRead()
  ElMessage.success('已全部标记已读')
  loadNotices()
  loadStats()
}

onMounted(() => {
  loadStats()
  loadNotices()
})
</script>

<style scoped>
.stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.stat .num {
  font-size: 34px;
  font-weight: 700;
  color: #1a365d;
}
.stat .num.warn {
  color: #e6a23c;
}
.stat .unit {
  color: #888;
}
.stat-sub {
  color: #999;
  font-size: 13px;
  margin-top: 4px;
}
.mt {
  margin-top: 16px;
}
</style>
